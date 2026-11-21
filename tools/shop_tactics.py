"""Shop purchase priorities/confirmation; validated selling: inventory_tactics.py."""
import re
from collections import deque

try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent

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
    candidates = []
    for cell, stock in p.loot.items():
        if not stock.get("for_sale") or cell not in previous or cell in p.blocked:
            continue
        price = stock.get("price")
        name = stock.get("top_item", {}).get("name", stock["name"])
        rank = priority(name, state["inventory"], getattr(p, "pharmacophobia", False),getattr(p,'into_darkness',False))
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
    p.entrance_visit_steps += 1
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
    frontiers = [c for c in body if c != pos and c in previous and c not in p.exhausted
                 and all(n in body for n in p.route(previous, c))
                 and any(n not in p.tiles for n in neighbors(c, width, height))]
    doors = {c for cell in body for c in neighbors(cell, width, height)
             if p.tiles.get(c, {}).get("terrain") in {5, 6} and c not in p.entrance_doors_checked}
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
    # At the same door layer, check a strictly nearer admitted door rather
    # than repeatedly crossing a large open component to scout its perimeter.
    # Local/equidistant frontiers still win; paths and visit receipts are
    # unchanged, and deeper branches still wait for shallower work.
    if frontiers and doors:
        if min(len(p.route(previous, c)) for c in doors) < min(
                len(p.route(previous, c)) for c in frontiers):
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
