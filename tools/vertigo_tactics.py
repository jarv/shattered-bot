"""Bounded vertigo recovery: all random landing directions must be admissible."""
from collections import deque
import re

try:
    from .policy_decision import Intent, PlannerStuck
    from .policy_geometry import distance, neighbors
    from .consumable_tactics import base_name
    from .survival_policy import is_hostile
except ImportError:
    from policy_decision import Intent, PlannerStuck
    from policy_geometry import distance, neighbors
    from consumable_tactics import base_name
    from survival_policy import is_hostile


MAX_MOVES = 12
MAX_WAITS = 12
GROUND = {1, 2, 3, 6, 9, 11, 14, 15, 19, 20, 29, 30}


def confusion(tile):
    effects = tile.get("effects", [])
    return bool(effects) and all("cloud of confusion gas" in e.lower() for e in effects)


def remaining(state):
    for buff in state["hero"].get("buffs", []):
        if "vertigo" in buff["name"].lower():
            match = re.search(r"(?:remaining|left)\s*:\s*(\d+(?:\.\d+)?)", buff.get("description", ""), re.I)
            return float(match[1]) if match else None
    return 0


def threats(p, state):
    visible = [o for o in state.get("objects", []) if is_hostile(o)]
    cells = {o["cell"] for o in visible}
    return visible + [o for c, o in getattr(p, "recent_threats", {}).items() if c not in cells]


def safe_tile(p, state, cell, *, random_landing=False):
    tile = p.tiles.get(cell, {})
    # An exit is passable when landed on, but requesting it may interact
    # with stairs. Admit it only in the random-outcome check, never as a goal.
    ground = tile.get("terrain") in GROUND or random_landing and tile.get("terrain") == 8
    if not tile.get("visible") or not ground or tile.get("plant") \
            or (tile.get("trap") and tile.get("terrain") != 19) \
            or (tile.get("effects") and not confusion(tile)) \
            or cell in p.blocked or cell in state.get("danger_cells", []) \
            or not p.escape_step_allowed(state, cell):
        return False
    if cell in p.room_blocked and not confusion(tile):
        return False
    width = state["map"]["width"]
    if any(distance(cell, o["cell"], width) <= 4 for o in p.room_actors.values()):
        return False
    if any(o.get("cell") == cell and not o.get("top_item") for o in state.get("objects", [])):
        return False
    for foe in threats(p, state):
        if foe.get("sleeping"):
            if distance(cell, foe["cell"], width) <= 3:
                return False
        elif distance(cell, foe["cell"], width) <= 3:
            return False  # Do not random-walk into an approaching melee opponent.
        elif getattr(p, "unit_strategies_enabled", False):
            profile = p.unit_strategies.profile(foe)
            if {"ranged-attacks", "ranged-pull"} & set(profile.capabilities) \
                    and p.enemy_can_see(state, foe, cell):
                return False
    return True


def landings(p, state, cell):
    """Walls cause no movement; passable/avoidable hazards are NOT walls."""
    width, height = state["map"]["width"], state["map"]["height"]
    if not 0 < cell % width < width-1 or not 0 < cell // width < height-1:
        return None
    result = []
    for adjacent in neighbors(cell, width, height):
        tile = p.tiles.get(adjacent, {})
        if not tile.get("visible"):
            return None
        # Region decorations (e.g. sewer storage barrels) are solid, with
        # neither PASSABLE nor AVOID, so Char.move bumps rather than lands.
        if tile.get("terrain") in {4, 12, 33}:
            continue
        if not safe_tile(p, state, adjacent, random_landing=True):
            return None
        result.append(adjacent)
    return result


def exit_route(p, state, random):
    pos = state["hero"]["cell"]
    queue = deque([[pos]])
    seen = {pos}
    while queue:
        route = queue.popleft()
        cell = route[-1]
        if cell != pos and not p.tiles[cell].get("effects"):
            return route
        if len(route) >= MAX_MOVES + 1 or len(seen) > 128:
            continue
        choices = landings(p, state, cell) if random else [
            c for c in neighbors(cell, state["map"]["width"], state["map"]["height"]) if safe_tile(p, state, c)]
        for adjacent in choices or ():
            if p.tiles[adjacent].get("terrain") == 8:
                continue  # Possible random landing, not a requested stair input.
            if adjacent not in seen:
                seen.add(adjacent)
                queue.append(route + [adjacent])
    return None


def mark(p, state, decision, kind):
    decision.vertigo_kind = kind
    p.vertigo_pending = {"kind": kind, "action": dict(decision.action), "depth": state["depth"],
                         "branch": state.get("branch", 0), "cell": state["hero"]["cell"],
                         "remaining": remaining(state)}
    return decision


def rescue(p, state, gas, vertigo, *, reserved=False):
    hero = state["hero"]
    inventory = state["inventory"]
    if gas:
        purity = next((i for i in inventory if base_name(i) == "potion of purity"
                       and "DRINK" in i.get("actions", [])
                       and (reserved or p.item_action_allowed(i, "DRINK"))), None)
        if purity:
            try:
                from .room_supplies import use
                from .room_tactics import remaining as duration
            except ImportError:
                from room_supplies import use
                from room_tactics import remaining as duration
            if duration(state, "purification barrier") <= 0:
                return use(p, purity, "DRINK", "vertigo: stop confusion-gas exposure with known purity; verify actual immunity",
                           kind="emergency")
    heal = next((i for i in inventory if base_name(i) == "potion of healing"
                 and "DRINK" in i.get("actions", []) and p.item_action_allowed(i, "DRINK")), None)
    if heal and (hero["hp"] < .35 * hero["max_hp"] or vertigo and not gas and threats(p, state)):
        return p.use(heal, "DRINK", "vertigo: known healing/cure before further impaired actions")
    if gas or threats(p, state) or state.get("danger_cells") or hero["hp"] < .35 * hero["max_hp"]:
        return p.emergency_transport(state, threats(p, state))
    return None


def choose(p, state):
    p.vertigo_pending = None
    if state.get("status") != "ready" or state.get("modal"):
        return None
    pos = state["hero"]["cell"]
    tile = p.tiles.get(pos, {})
    vertigo = any("vertigo" in b["name"].lower() for b in state["hero"].get("buffs", []))
    gas = confusion(tile)
    if not vertigo and not gas:
        p.vertigo_plan = None
        p.temporary_confusion_waits = 0
        return None
    if not p.vertigo_plan:
        p.vertigo_plan = {"moves": 0, "waits": 0, "stale": 0}
    plan = p.vertigo_plan
    p.planner.report["vertigo_response"] = dict(plan, in_confusion_gas=gas,
        remaining=remaining(state), qualification="Only actual observations confirm movement, gas escape or recovery")
    exposure = any("cloud of confusion gas" in e.lower() for e in tile.get("effects", []))
    action = rescue(p, state, exposure, vertigo)
    if action:
        return action
    mixed = bool(tile.get("effects")) and not gas
    calm_environment = not state.get("danger_cells") and not mixed \
        and not getattr(p, "unseen_damage_turns", 0) and state["hero"]["hp"] > .35 * state["hero"]["max_hp"]
    foes = threats(p, state)
    calm = not foes and calm_environment
    try:
        from .room_tactics import remaining as duration
    except ImportError:
        from room_tactics import remaining as duration
    protected = duration(state, "purification barrier") > 0
    # Waiting is useful only after leaving the source or verifying immunity.
    if vertigo and calm and (not gas or protected) and plan["stale"] < 2 \
            and plan["waits"] < MAX_WAITS and tile.get("terrain") in GROUND and not tile.get("plant") \
            and (not tile.get("trap") or tile.get("terrain") == 19) \
            and not any("starving" in b["name"].lower() for b in state["hero"].get("buffs", [])) \
            and (gas or pos not in p.room_blocked):
        return mark(p, state, p.decision({"type": "wait"}, "vertigo: bounded wait outside renewing exposure", intent=Intent.RECOVER), "wait")
    impaired = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    # A distant sleeper is not an active pursuit veto. Keep stationary waits
    # unchanged; safe_tile still rejects every landing near any sleeper, and
    # landings checks all random directions before permitting a single input.
    escape_calm = calm_environment and not any(not foe.get("sleeping") for foe in foes)
    if escape_calm and (gas or plan["stale"] >= 2 or plan["waits"] >= MAX_WAITS) \
            and not any(b in impaired for b in ("root", "paral", "frozen")) and plan["moves"] < MAX_MOVES:
        route = exit_route(p, state, random=vertigo)
        if route:
            p.planner.report["vertigo_response"].update(
                possible_landings=landings(p, state, pos) if vertigo else [route[1]],
                intended_route=route, random_direction=vertigo,
                qualification="Requested direction is not a promise of landing; one input, then reobserve actual cell")
            return mark(p, state, p.cell(route[1], "vertigo: bounded single-step escape; all possible random landings checked",
                                        intent=Intent.RETREAT), "move")
    # Useful stationary attacks may remove a threat; never force a random step
    # into it or treat an unknown potion as an escape resource.
    if not mixed and not state.get("danger_cells"):
        for enemy in state.get("objects", []):
            if is_hostile(enemy) and not enemy.get("sleeping") and (
                    distance(pos, enemy["cell"], state["map"]["width"]) <= 1 or p.shot_clear(state, enemy["cell"])):
                action = p.best_attack(state, enemy)
                if action:
                    return action
    # Preserve puzzle supplies when a free escape exists; emergency use remains
    # explicit and is accounted for only by the shared consumption receipts.
    action = rescue(p, state, exposure, vertigo, reserved=True)
    if action:
        return action
    teleport = next((i for i in state["inventory"] if base_name(i) == "scroll of teleportation"
                     and "READ" in i.get("actions", []) and p.item_action_allowed(i, "READ")), None)
    if teleport:
        return p.use(teleport, "READ", "vertigo: known emergency teleport after no admissible bounded local escape")
    raise PlannerStuck("Vertigo/confusion exposure: no admissible recovery or all-direction-safe escape within budget",
                       kind="immediate-safety-emergency")


def observe(p, before, decision, after):
    pending = p.vertigo_pending
    p.vertigo_pending = None
    if not pending or getattr(decision, "vertigo_kind", None) != pending["kind"] \
            or decision.action != pending["action"] or before.get("depth") != pending["depth"] \
            or after.get("depth") != pending["depth"] or before.get("branch", 0) != after.get("branch", 0) \
            or before["hero"]["cell"] != pending["cell"] or not p.vertigo_plan:
        return None
    plan = p.vertigo_plan
    if pending["kind"] == "move":
        plan["moves"] += 1  # Includes wall bumps and unexpected, but accepted, landings.
        if after["hero"]["cell"] != before["hero"]["cell"]:
            plan["stale"] = 0
    else:
        plan["waits"] += 1
        old, new = pending["remaining"], remaining(after)
        plan["stale"] = plan["stale"] + 1 if old is not None and new is not None and new >= old else 0
    return {"kind": pending["kind"], "actual_cell": after["hero"]["cell"],
            "moved_as_requested": after["hero"]["cell"] == decision.action.get("cell"),
            "moves": plan["moves"], "waits": plan["waits"], "stale": plan["stale"]}
