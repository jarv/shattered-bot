"""Shop purchase priorities/confirmation; validated selling: inventory_tactics.py."""
import re
from collections import deque

try:
    from .policy_decision import Intent
    from .objective_planning import Status, Result, publish, mark, exhausted
except ImportError:
    from policy_decision import Intent
    from objective_planning import Status, Result, publish, mark, exhausted

BAGS = ("scroll holder", "potion bandolier", "velvet pouch", "magical holster")


def priority(name, inventory, pharmacophobia=False,into_darkness=False):
    name = name.lower()
    if name.startswith("scroll of remove curse") and any(i.get("equipped") and i.get("known_cursed") for i in inventory):
        return (-1, 0)
    bag = next((bag for bag in BAGS if bag in name), None)
    if bag:
        return None if any(bag in i["name"].lower() for i in inventory) else (0, BAGS.index(bag))
    if name.startswith("scroll of "):
        return (1, 0)
    if name.startswith("potion of healing"):
        return None if pharmacophobia else (2, 0)
    if into_darkness and name == "torch" and not any("torch" in i["name"].lower() for i in inventory):
        return (2, 0)
    if "ration" in name or name == "bag of magic sand":
        if "sand" in name and not any("timekeeper's hourglass" in i["name"].lower() for i in inventory):
            return None
        return (3, 0)
    return None


def choose_shop(p, state, previous):
    gold = state["hero"].get("gold", 0)
    starving_without_food = any("starving" in b["name"].lower()
                                for b in state["hero"].get("buffs", [])) and not p.food_items(state)
    candidates = []
    for cell, stock in p.loot.items():
        if not stock.get("for_sale") or cell not in previous or cell in p.blocked:
            continue
        price = stock.get("price")
        name = stock.get("top_item", {}).get("name", stock["name"])
        rank = priority(name, state["inventory"], getattr(p, "pharmacophobia", False),getattr(p,'into_darkness',False))
        # An observed ration is immediate relief, not optional stock, when
        # starving without safe carried food. Keep curse removal first and
        # retain the same route, affordability and purchase-confirmation gates.
        if starving_without_food and name.lower() in {"small food ration", "ration of food"}:
            rank = (-0.5, 0)
        if rank is not None and isinstance(price, int) and 0 <= price <= gold:
            candidates.append((rank, price, len(p.route(previous, cell)), cell, name))
    if not candidates:
        return None
    _, price, _, cell, name = min(candidates)
    route = p.route(previous, cell)
    if len(route) <= 2:
        p.shop_plan = {"name": name, "price": price, "cell": cell, "depth": state["depth"]}
    return p.toward(state, cell, "shop: buy priority supplies", previous, intent=Intent.SHOP)


def confirm_purchase(p, state):
    plan, p.shop_plan = p.shop_plan, None
    if not plan:
        return None
    for button in state["ui"]["buttons"]:
        match = re.fullmatch(r"buy for (\d+)g", button["label"].strip().lower())
        if match and int(match[1]) == plan["price"] and state["hero"].get("gold", 0) >= plan["price"] \
                and priority(plan["name"], state["inventory"], getattr(p, "pharmacophobia", False),getattr(p,'into_darkness',False)) is not None:
            # UI item title must match our intended purchase, not an unrelated
            # trade window opened during a navigation interruption.
            title = plan["name"].replace("_", "").lower()
            texts = [t.replace("_", "").lower() for t in state["ui"].get("texts", [])]
            if any(title in text for text in texts):
                p.purchases.append(dict(plan))
                return p.decision({"type": "button", "id": button["id"]}, f"shop: purchase {plan['name']} for {plan['price']}g")
    return p.decision({"type": "back"}, "shop: cancel unavailable or changed purchase")


class ShopVisitBlocked(RuntimeError):
    pass


def visit_entrance_shop(p, state, previous, neighbors):
    """Commit to an admitted search target until arrival or invalidation."""
    depth, pos = state["depth"], state["hero"]["cell"]
    if depth in p.shop_visited_floors:
        p.shop_search_target = None
        return None
    plan = p.shop_search_target
    if plan and plan["target"] in p.exhausted and p.tiles.get(plan["target"], {}).get("terrain") not in {5, 6}:
        p.shop_search_target = plan = None
    stock = [o for o in state.get("objects", []) if o.get("for_sale") or o["name"].lower() == "shopkeeper"]
    if plan and not stock:
        target = plan["target"]
        key = "shop-target:"+str(target)
        if exhausted(p, key, 80, 6):
            p.shop_search_failed.add(target)
            p.shop_search_target = None
            publish(p, "entrance-shop", Result(Status.BLOCKED, "target made no progress or exhausted travel",
                                               prerequisites=[dict(target=target)]))
        elif target != pos and target in previous and p.entrance_visit_steps < 80:
            route = p.route(previous, target)
            if _shop_route(p, state, route):
                action = p.toward(state, target, plan["reason"], previous, intent=Intent.SHOP)
                if action:
                    return _track_shop(p, state, action)
            p.shop_search_target = None
        else:
            p.shop_search_target = None
    try:
        action = _visit_entrance_shop(p, state, previous, neighbors)
    except ShopVisitBlocked as error:
        if getattr(getattr(p, "profile", None), "name", None) == "simple-bot" \
                and p.entrance_cell not in previous and not stock:
            # An observed teleport can separate the hero from the entrance.
            # Discover an ordinary connection rather than invent a path or
            # certify a store visit. Retry this same shop routine next input.
            p.shop_search_target = None
            reason = "Entrance shop temporarily disconnected; continue ordinary exploration and retry observed access"
            publish(p, "entrance-shop", Result(Status.BLOCKED, reason,
                    prerequisites=[dict(entrance=p.entrance_cell, visited=False)]))
            p.defer_obligations(state, [{"kind": "unreached entrance shop", "cell": p.entrance_cell}],
                                reason)
            return None
        publish(p, "entrance-shop", Result(Status.EXHAUSTED, str(error),
                prerequisites=[dict(failed_targets=sorted(p.shop_search_failed),
                                    accepted_search_inputs=p.entrance_visit_steps)]))
        raise
    if action:
        return _track_shop(p, state, action)
    if depth in p.shop_visited_floors:
        publish(p, "entrance-shop", Result(Status.COMPLETE, "observed proximity to shop stock or keeper"))
        p.shop_search_target = None
    return None


def _shop_route(p, state, route):
    forbidden = p.navigation_barriers(state, Intent.SHOP)
    return len(route) > 1 and all(c not in forbidden and c not in state.get("danger_cells", [])
        and not p.tiles[c].get("trap") and not p.tiles[c].get("plant")
        and not p.effects_block_movement(p.tiles[c]) for c in route[1:]) \
        and p.tiles[route[1]].get("visible") and p.escape_step_allowed(state, route[1])


def _track_shop(p, state, action):
    route = list(action.navigation_route) or [state["hero"]["cell"], action.action.get("cell")]
    target = route[-1]
    p.shop_search_target = dict(target=target, reason=action.reason)
    publish(p, "entrance-shop", Result(Status.READY, "continue admitted search target",
                                       prerequisites=[dict(target=target, route=route)]))
    return mark(p, state, action, "shop-target:"+str(target), target, route)


def _visit_entrance_shop(p, state, previous, neighbors):
    depth = state["depth"]
    stock = [o for o in state.get("objects", []) if o.get("for_sale")]
    keepers = [o for o in state.get("objects", []) if o["name"].lower() == "shopkeeper"]
    if depth in p.shop_visited_floors or (depth not in {6, 11, 16} and not stock and not keepers) \
            or state.get("branch", 0) != 0:
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    def dist(a, b):
        return max(abs(a % width-b % width), abs(a // width-b // width))
    if any(dist(pos, o["cell"]) <= 2 for o in stock + keepers):
        p.shop_visited_floors.add(depth)
        return None
    if p.entrance_visit_steps >= 80:
        raise ShopVisitBlocked("Entrance shop visit exhausted its safe search budget; refusing to silently skip the store")
    if stock or keepers:
        targets = [c for c in previous if c != pos and p.tiles[c]["terrain"] not in {5, 7, 8, 21, 22, 37}
                   and not p.loot.get(c, {}).get("for_sale")
                   and any(dist(c, o["cell"]) <= 2 for o in stock + keepers)]
        if targets:
            target = min(targets, key=lambda c: len(p.route(previous, c)))
            return p.toward(state, target, "shop: visit entrance store before exploring", previous, intent=Intent.SHOP)
    # Search observed entrance-side chambers. A small stair annex can have a
    # door before the main entrance chamber; already checked thresholds must
    # not prevent revealing that chamber. The overall movement budget bounds
    # this search, without generated room IDs or hidden shop positions.
    body, queue = {p.entrance_cell}, deque([p.entrance_cell])
    layers = {p.entrance_cell: 0}
    interior = {1, 2, 3, 9, 11, 14, 15, 19, 20, 29, 30, 32}
    while queue:
        cell = queue.popleft()
        for c in neighbors(cell, width, height):
            if c % width != cell % width and c // width != cell // width:
                continue
            terrain = p.tiles.get(c, {}).get("terrain")
            if terrain in interior or (terrain in {5, 6} and c in p.entrance_doors_checked):
                cost = int(terrain in {5, 6})
                layer = layers[cell] + cost
                if c in layers and layers[c] <= layer:
                    continue
                body.add(c)
                layers[c] = layer
                if cost:
                    queue.append(c)
                else:
                    queue.appendleft(c)
    # Reveal the observed entrance-side component without letting either a
    # door branch or a distant connected frontier monopolize the visit budget.
    # Use only the existing admitted paths, never unknown cells or a route
    # through an unchecked door to reach a supposedly local frontier.
    frontiers = [c for c in body if c != pos and c in previous and c not in p.exhausted and c not in p.shop_search_failed
                 and all(n in body for n in p.route(previous, c))
                 and any(n not in p.tiles for n in neighbors(c, width, height))]
    doors = {c for cell in body for c in neighbors(cell, width, height)
              if p.tiles.get(c, {}).get("terrain") in {5, 6} and c not in p.entrance_doors_checked
              and c not in p.shop_search_failed}
    # Checking an annex exit must not let its entire downstream component
    # monopolize the entrance visit. Finish admitted work at the shallowest
    # observed door layer first; within that layer, reveal frontiers as before.
    # This changes target ordering only, not paths, hazards or visit receipts.
    door_layers = {c: min(layers[n] for n in neighbors(c, width, height) if n in body)
                   for c in doors if c in previous}
    work_layers = [layers[c] for c in frontiers] + list(door_layers.values())
    if work_layers:
        layer = min(work_layers)
        frontiers = [c for c in frontiers if layers[c] == layer]
        doors = {c for c in door_layers if door_layers[c] == layer}
    # At the same door layer, also bound outward scouting by the nearest
    # observed entrance-side door. Greedily following the nearest frontier
    # can walk an entire large connected component while doors beside the
    # entrance starve. This is target ordering only, not movement admission.
    # Frontiers inside/equal to that entrance radius retain their priority.
    if frontiers and doors:
        if min(len(p.route(previous, c)) for c in doors) < min(
                len(p.route(previous, c)) for c in frontiers):
            frontiers = []
        else:
            radius = min(dist(p.entrance_cell, c) for c in frontiers)
            entrance_doors = {c for c in doors if dist(p.entrance_cell, c) < radius}
            if entrance_doors:
                doors = entrance_doors
                frontiers = []
    if frontiers:
        return p.toward(state, min(frontiers, key=lambda c: len(p.route(previous, c))),
                         "shop: reveal entrance chamber doors", previous, intent=Intent.SHOP)
    for door in sorted(doors, key=lambda c: len(p.route(previous, c)) if c in previous else 9999):
        if door not in previous:
            continue
        if pos == door:
            beyond = [c for c in neighbors(door, width, height) if c not in body and c in previous
                      and p.walkable(c) and p.tiles[c]["terrain"] in interior
                      and not p.loot.get(c, {}).get("for_sale")]
            p.entrance_doors_checked.add(door)
            if beyond:
                return p.cell(min(beyond, key=lambda c: p.visits[c]), "shop: inspect entrance-door branch")
            continue
        return p.toward(state, door, "shop: check entrance door before descent", previous, intent=Intent.SHOP)
    raise ShopVisitBlocked("Expected shop at this floor's entrance, but no safe unexamined entrance branch remains")
