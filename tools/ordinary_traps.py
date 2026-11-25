"""Bounded, publicly reobserved remote clearing of ordinary trap obstructions.

FlockTrap's radius-two sheep spawn can activate other traps. Unknown geometry,
observed secondary mechanisms, effects, plants and actors veto activation.
This excludes observed risks; it never claims hidden traps cannot exist.
"""
from collections import deque

try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance, neighbors, line_clear
    from .policy_decision import Intent
    from .payload_workflow import throw, REUSABLE, PayloadPhase
    from .simple_navigation import paths, observe, ordinary_work
    from .hunger_budget import admits
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance, neighbors, line_clear
    from policy_decision import Intent
    from payload_workflow import throw, REUSABLE, PayloadPhase
    from simple_navigation import paths, observe, ordinary_work
    from hunger_budget import admits


# Public Terrain.java SOLID flags, not generated map/room identities.
SOLID = {4, 5, 10, 12, 13, 16, 21, 23, 25, 26, 27, 28, 31, 33, 34, 35, 36, 38, 39}
SUPPORTED = {"flock trap", "burning trap"}


def burning_footprint(p, state, target, *, fresh=True):
    """BurningTrap seeds radius-one fire; decline any observed spread fuel."""
    area = {target, *neighbors(target, state["map"]["width"], state["map"]["height"])}
    nonflammable = {0, 1, 3, 4, 9, 11, 12, 14, 18, 19, 20, 24, 25, 26, 28, 29, 31, 33, 34, 35, 36, 38, 39}
    for c in area:
        t = p.tiles.get(c, {})
        if not t.get("observed") or fresh and not t.get("visible") \
                or t.get("terrain") not in nonflammable or t.get("effects") or t.get("plant"):
            return None
        # Fire does not press adjacent mechanisms. Still exclude every other
        # live trap type; this is not general permission to chain a trap field.
        if t.get("trap") and t["terrain"] != 19 and t["trap"].lower() != "burning trap":
            return None
        if c in p.loot or c in p.unconfirmed_loot:
            return None
    if any(o["cell"] in area for o in state.get("objects", [])):
        return None
    return area


def burning_route_targets(p, state, previous):
    """Counterfactual progress feasibility, never an actual movement route."""
    burning = {c for c, t in p.tiles.items()
               if t["terrain"] == 18 and t.get("trap", "").lower() == "burning trap"}
    if not burning:
        return set()
    old = {c: p.tiles[c] for c in burning}
    blocked = p.room_blocked
    try:
        for c in burning:
            p.tiles[c] = dict(p.tiles[c], terrain=19, trap="")
        p.room_blocked = blocked-burning
        possible = paths(p, state)
        doors, frontiers = ordinary_work(p, state, possible)
        goals = [c for c in doors+frontiers if c not in previous]
        goals.extend(c for c in possible if c not in previous and p.tiles[c]["terrain"] in {8,21,22})
        if not goals:
            return set()
        goal = min(goals, key=lambda c: (len(p.route(possible, c)), c))
        route = p.route(possible, goal)
        first = next((c for c in route if c in burning), None)
        return {first} if first is not None else set()
    finally:
        p.tiles.update(old)
        p.room_blocked = blocked


def footprint(p, state, target):
    """Freshly observed radius-two non-solid connectivity, or None if unknown."""
    w, h = state["map"]["width"], state["map"]["height"]
    distances = {target: 0}
    queue = deque([target])
    while queue:
        cell = queue.popleft()
        if distances[cell] == 2:
            continue
        for n in neighbors(cell, w, h):
            tile = p.tiles.get(n)
            if tile is None or not tile.get("observed") or not tile.get("visible"):
                return None
            if tile["terrain"] not in SOLID and n not in distances:
                distances[n] = distances[cell] + 1
                queue.append(n)
    for cell in distances:
        tile = p.tiles.get(cell, {})
        if not tile.get("visible") or not tile.get("observed") \
                or tile["terrain"] == 0 or tile.get("effects") or tile.get("plant") \
                or (cell != target and tile.get("trap") and tile["terrain"] != 19):
            return None
    if any(o["cell"] in distances and not o.get("top_item") for o in state.get("objects", [])):
        return None
    return set(distances)


def accepted(p, before, decision, after):
    kind = getattr(decision, "ordinary_trap_action", None)
    if not kind:
        return
    plan = observe(p, before).get("ordinary_trap")
    if plan:
        plan["steps" if kind == "approach" else "waits"] += 1


def choose(p, state, enemies):
    floor = observe(p, state)
    if enemies or p.recent_threats or state.get("danger_cells") or p.unseen_damage_turns:
        return None
    if state.get("status") != "ready" or state.get("modal"):
        return None
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    if hero["hp"] < .7 * hero["max_hp"] or any(
            b in buffs for b in ("starving", "burn", "poison", "bleed", "ooze", "vertigo", "root", "paral")):
        return None
    plan = floor.get("ordinary_trap")
    if plan and plan.get("owner"):
        account = p.physical_ledger.entries.get(plan["owner"])
        if account and account.unresolved and not p.trap_payload_return:
            p.stop_gameplay("Ordinary trap payload remains unverified/unretrieved",
                            kind="mandatory-preparation-unresolved")
        if not p.trap_payload_return:
            floor["ordinary_trap"] = None
            return None  # Existing retrieval receipts, not a guessed return.
        if p.trap_payload_return.phase in {PayloadPhase.PROPOSED, PayloadPhase.AIMING}:
            return None
        sheep = [o for o in state.get("objects", []) if o["name"].lower() == "sheep"]
        if sheep and p.tiles.get(plan["target"], {}).get("terrain") == 19:
            if plan["waits"] >= 12:
                p.stop_gameplay("Flock trap sheep did not clear within bounded observation budget",
                                kind="navigation-stalled")
            action = p.decision({"type": "wait"}, "trap: bounded wait for observed flock sheep before payload retrieval")
            action.ordinary_trap_action = "wait"
            return action
        if plan.get("kind") == "burning trap" and any(
                p.tiles.get(c, {}).get("effects") for c in plan.get("area", [])):
            if plan["waits"] >= 16:
                p.stop_gameplay("Remote burning-trap effects did not clear within bounded observation budget",
                                kind="navigation-stalled")
            here = p.tiles.get(hero["cell"], {})
            if here.get("effects") or here.get("trap") or here.get("plant"):
                return None
            action = p.decision({"type": "wait"}, "trap: observe remote fire expiry before owned waterskin retrieval")
            action.ordinary_trap_action = "wait"
            return action
        return None  # Shared recover_trap_payload owns the collection route.
    if p.trap_payload_return or p.potion_stash or p.puzzle_probe:
        return None
    previous = paths(p, state)
    doors, frontiers = ordinary_work(p, state, previous)
    if any(p.tiles[c]["terrain"] in {8, 22} for c in previous) or doors or frontiers:
        floor["ordinary_trap"] = None
        return None  # Ordinary routes/known stairs first, never a trap expedition.
    if not plan:
        choices = []
        burning_targets = burning_route_targets(p, state, previous)
        if sum(d == state["depth"] for d, _ in p.trap_attempts) >= 16:
            return None
        for target, tile in list(p.tiles.items()):
            kind = tile.get("trap", "").lower()
            if tile.get("terrain") != 18 or kind not in SUPPORTED \
                    or not tile.get("observed") or (state["depth"], target) in p.trap_attempts:
                continue
            if kind == "burning trap" and (target not in burning_targets
                    or not burning_footprint(p, state, target, fresh=False)):
                continue
            # Feasibility only: fresh disarm must later be observed before entry.
            old = p.tiles[target]
            old_blocked = p.room_blocked
            try:
                p.tiles[target] = dict(old, terrain=19, trap=None)
                p.room_blocked = old_blocked - {target}
                gain = len(set(paths(p, state)) - set(previous))
            finally:
                p.tiles[target] = old
                p.room_blocked = old_blocked
            if gain > 1 or kind == "burning trap" and gain >= 1:
                choices.append(target)
        if not choices:
            return None
        target = min(choices, key=lambda c: distance(hero["cell"], c, state["map"]["width"]))
        plan = floor["ordinary_trap"] = {
            "target": target, "kind": p.tiles[target].get("trap", "").lower(),
            "steps": 0, "waits": 0, "scouted": set(), "owner": None}
    target = plan["target"]
    if plan["steps"] >= 32:
        p.stop_gameplay("Ordinary trap reobservation exhausted bounded approach budget",
                        kind="navigation-stalled")
    tile = p.tiles.get(target, {})
    if tile.get("terrain") != 18 or tile.get("trap", "").lower() not in SUPPORTED:
        floor["ordinary_trap"] = None
        return None
    burning = tile.get("trap", "").lower() == "burning trap"
    area = (burning_footprint(p, state, target) if burning else footprint(p, state, target)) \
        if tile.get("visible") else None
    item = next((i for i in state["inventory"] if base_name(i) in REUSABLE
                 and "THROW" in i.get("actions", []) and not i.get("equipped")), None)
    remote_safe = not burning or distance(hero["cell"], target, state["map"]["width"]) >= 3 \
        and not any(p.tiles.get(hero["cell"], {}).get(k) for k in ("trap", "plant", "effects"))
    if area and item and remote_safe and p.shot_clear(state, target) and admits(p, state, 30):
        action = throw(p, state, item, target,
                       "trap: activate observed blocking "+plan["kind"]+" remotely; retain payload custody")
        if action:
            plan["owner"] = p.trap_payload_return.owner
            plan["area"] = sorted(area)
            p.trap_attempts.add((state["depth"], target))
            p.planner.report["ordinary_trap"] = {
                "target": target, "observed_footprint": sorted(area),
                "qualification": "Type-specific observed footprint/actor/plant/effect checks; hidden mechanisms not ruled out. "
                                 "No disarm or payload recovery credited before accepted observations."}
        return action
    plan["scouted"].add(hero["cell"])
    candidates = [c for c in previous if c not in plan["scouted"]
                  and c not in p.loot and p.tiles[c]["terrain"] not in {7, 8, 21, 22, 37, 38}
                  and distance(c, target, state["map"]["width"]) <= 4
                  and (not burning or distance(c, target, state["map"]["width"]) >= 3)
                  and line_clear(c, target, state["map"]["width"], p.tiles)]
    if not item or not candidates:
        p.planner.report["ordinary_trap"] = {
            "target": target, "status": "no safe fresh footprint/approach or reusable payload",
            "disarm_credited": False}
        return None
    vantage = min(candidates, key=lambda c: (len(p.route(previous, c)), c))
    if not admits(p, state, len(p.route(previous, vantage)) + 30):
        return None
    action = p.toward(state, vantage, "trap: reobserve ordinary blocking mechanism from known ground",
                      previous, intent=Intent.REPOSITION)
    if action:
        action.ordinary_trap_action = "approach"
    return action
