"""Verified short trap-field transit to known dry ground beside ordinary doors."""
from collections import deque
try:
    from .combat_items import unencumbered
    from .consumable_tactics import base_name
    from .policy_geometry import neighbors
    from .policy_decision import Intent
    from .room_tactics import safe_tile, remaining
except ImportError:
    from combat_items import unencumbered
    from consumable_tactics import base_name
    from policy_geometry import neighbors
    from policy_decision import Intent
    from room_tactics import safe_tile, remaining


def admitted(p, state, cell, occupied):
    tile = p.tiles.get(cell, {})
    return tile.get("observed") and tile.get("terrain") != 0 \
        and "summoning" not in tile.get("trap", "").lower() \
        and cell not in state.get("danger_cells", []) \
        and cell not in p.loot and cell not in p.unconfirmed_loot \
        and (cell not in p.room_blocked or tile.get("terrain") == 18) \
        and p.escape_step_allowed(state, cell) and safe_tile(p, cell, "flight", occupied)


def recover(p, state, enemies):
    floor = p.simple_floors.get((state.get("depth"), state.get("branch", 0)), {})
    plan = floor.get("flight_transit")
    if not plan or state.get("status") != "ready" or state.get("modal"):
        return None
    pos = state["hero"]["cell"]
    route = plan["route"]
    if pos not in route:
        p.stop_gameplay("Protected ordinary transit displaced off verified route", kind="immediate-safety-emergency")
    if (pos == route[-1] and not plan.get("returning")) or (pos == route[0] and plan.get("returning")):
        tile = p.tiles.get(pos, {})
        if tile.get("terrain") == 18 or tile.get("trap") or p.effects_block_movement(tile):
            p.stop_gameplay("Ordinary flight landing is no longer safe", kind="immediate-safety-emergency")
        floor["flight_transit"] = None
        p.planner.report["simple_flight"] = {"status": "Observed arrival on known safe ground",
                                           "landing": pos, "collection_credited": False}
        return None
    if plan["inputs"] >= 24:
        p.stop_gameplay("Ordinary flight transit exhausted accepted-input budget", kind="navigation-stalled")
    duration = remaining(state, "levitating")
    index = route.index(pos)
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if not unencumbered(state) or any(k in buffs for k in ("root", "paral", "vertigo", "slow", "crippl", "chill")):
        p.stop_gameplay("Ordinary flight movement budget invalidated", kind="immediate-safety-emergency")
    retreating = bool(plan.get("returning") or enemies or state.get("danger_cells"))
    if retreating and not plan.get("returning"):
        plan["returning"] = index <= len(route)-1-index
    destination = 0 if plan.get("returning") else len(route)-1
    if index == destination:
        floor["flight_transit"] = None
        return None
    if duration < abs(destination-index)+3:
        # Never restart a failed drink or infer protection from consuming it.
        p.stop_gameplay("Ordinary trap transit lacks witnessed flight duration", kind="immediate-safety-emergency")
    occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    target_index = index-1 if plan.get("returning") else index+1
    target = route[target_index]
    if not p.tiles.get(target, {}).get("visible") or not admitted(p, state, target, occupied):
        p.stop_gameplay("Ordinary flight route changed; no guessed hazardous step", kind="immediate-safety-emergency")
    action = p.cell(target, "simple: verified levitation step to known safe landing",
                    intent=Intent.RETREAT if retreating else Intent.REPOSITION)
    action.simple_flight_input = True
    return action


def choose(p, state, enemies, floor, previous):
    if floor.get("flight_transit"):
        return recover(p, state, enemies)
    if enemies or p.recent_threats or p.dm100_threat or state.get("danger_cells") or p.unseen_damage_turns \
            or floor.get("flight_attempted") or not unencumbered(state) \
            or state["hero"]["hp"] < .8*state["hero"]["max_hp"]:
        return None
    item = next((i for i in state["inventory"] if base_name(i) == "potion of levitation"
                 and "DRINK" in i.get("actions", []) and p.item_action_allowed(i, "DRINK")), None)
    if not item:
        return None
    if p.physical_ledger.has_unresolved() or any(getattr(p, k, None) for k in (
            "potion_stash", "puzzle_probe", "wood_burn_plan", "trap_payload_return", "room_journey")):
        return None
    occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    w, h = state["map"]["width"], state["map"]["height"]
    doors = [c for c, t in p.tiles.items() if t["terrain"] == 5 and c not in previous]
    landings = {n for c in doors for n in neighbors(c, w, h)
                if n not in previous and p.tiles.get(n, {}).get("terrain") in {1, 3, 9, 14, 20, 29}
                and not p.tiles[n].get("trap") and admitted(p, state, n, occupied)}
    choices = []
    for bank in previous:
        if not admitted(p, state, bank, occupied) or p.tiles[bank].get("trap"):
            continue
        queue, seen = deque([[bank]]), {bank}
        while queue:
            route = queue.popleft()
            if len(route) > 7:
                continue
            if route[-1] in landings and any(p.tiles[c]["terrain"] == 18 for c in route):
                choices.append((len(p.route(previous, bank)), len(route), route))
                break
            for n in neighbors(route[-1], w, h):
                if n not in seen and admitted(p, state, n, occupied):
                    seen.add(n)
                    queue.append(route+[n])
    if not choices:
        return None
    _, _, route = min(choices)
    pos = state["hero"]["cell"]
    if pos != route[0]:
        if floor.get("flight_staging", 0) >= 64:
            return None
        action = p.toward(state, route[0], "simple: stage known levitation for observed trap obstruction",
                          previous, intent=Intent.REPOSITION)
        if action:
            action.simple_flight_staging = True
        return action
    # Require fresh visibility for the whole short crossing before drinking.
    if not all(p.tiles[c].get("visible") for c in route):
        return None
    floor["flight_transit"] = {"route": route, "inputs": 0}
    floor["flight_attempted"] = True
    action = p.use(item, "DRINK", "simple: prepare known levitation; verify buff before trap transit")
    action.simple_flight_input = True
    return action
