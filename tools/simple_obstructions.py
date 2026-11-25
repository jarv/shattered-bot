"""Bounded observation of temporary ordinary-route obstructions, not bypasses."""
try:
    from .policy_geometry import neighbors, distance
    from .simple_navigation import paths, ordinary_work, mark
except ImportError:
    from policy_geometry import neighbors, distance
    from simple_navigation import paths, ordinary_work, mark


def choose(p, state, enemies, floor):
    if enemies or p.recent_threats or state.get("danger_cells") or p.unseen_damage_turns:
        return None
    hero = state["hero"]
    if hero["hp"] < .7 * hero["max_hp"] or any(any(k in b["name"].lower() for k in
            ("starv", "burn", "poison", "bleed", "ooze", "paral", "vertigo"))
            for b in hero.get("buffs", [])):
        return None
    pos, w, h = hero["cell"], state["map"]["width"], state["map"]["height"]
    vicinity = [p.tiles.get(c, {}) for c in [pos, *neighbors(pos, w, h)]]
    # Cold clouds do not inflict HP damage outside their observed footprint.
    # Adjacent cold is not itself a reason to walk into the cloud or give up;
    # current effects and all other adjacent effects still veto waiting.
    if p.tiles.get(pos, {}).get("effects") or any(
            any("unnaturally frigid" not in e.lower() for e in t.get("effects", []))
            or t.get("plant") or t.get("trap") and t.get("terrain") != 19 for t in vicinity):
        return None
    waits = floor.get("obstruction_waits", {})
    # Do not talk to the ghost: doing so starts the disabled quest. Its ordinary
    # wandering can clear a nearby exit; an accepted wait credits no movement.
    if waits.get("ghost", 0) < 8 and any(
            o["name"].lower() == "sad ghost" and distance(pos, o["cell"], w) <= 2
            and p.tiles.get(o["cell"], {}).get("terrain") in {8, 21, 22}
            for o in state.get("objects", [])):
        action = p.decision({"type": "wait"}, "simple: bounded wait for wandering ghost to clear downstairs")
        action.simple_obstruction = "ghost"
        return mark(action)
    cold = {c for c, t in p.tiles.items() if t.get("effects") and all(
        "unnaturally frigid" in e.lower() for e in t["effects"])
        and not t.get("plant") and not (t.get("trap") and t["terrain"] != 19)}
    if not cold:
        return None
    # Counterfactual feasibility only. Restore every tile/barrier immediately;
    # no route through the cloud is admitted for actual movement.
    original = {c: p.tiles[c] for c in cold}
    blocked = p.room_blocked
    try:
        for c in cold:
            p.tiles[c] = dict(p.tiles[c], effects=[])
        p.room_blocked = blocked - cold
        potential = paths(p, state)
        doors, frontiers = ordinary_work(p, state, potential)
        useful = doors or frontiers or any(p.tiles[c]["terrain"] in {8, 21, 22} for c in potential)
    finally:
        p.tiles.update(original)
        p.room_blocked = blocked
    if not useful:
        return None
    if not any(p.tiles[c].get("visible") for c in cold):
        if waits.get("cold-reobserve", 0) >= 64:
            return None
        try:
            from .policy_geometry import line_clear
            from .policy_decision import Intent
        except ImportError:
            from policy_geometry import line_clear
            from policy_decision import Intent
        previous = paths(p, state)
        scouted = floor.setdefault("cold_scouted", set())
        scouted.add(pos)
        banks = [c for c in previous if c not in scouted and c not in p.loot
                 and p.tiles[c].get("observed") and p.tiles[c]["terrain"] in {1,3,5,6,9,11,14,20,29}
                 and not any(p.tiles[c].get(k) for k in ("plant", "trap", "effects"))
                 and any(distance(c, target, w) <= 3 and line_clear(c, target, w, p.tiles) for target in cold)]
        if not banks:
            return None
        bank = min(banks, key=lambda c: (len(p.route(previous, c)), c))
        action = p.toward(state, bank, "simple: return on admitted ground to reobserve remembered cold obstruction",
                          previous, intent=Intent.REPOSITION)
        if action:
            action.simple_obstruction = "cold-reobserve"
            return mark(action)
        return None
    if waits.get("cold", 0) >= 16:
        return None
    action = p.decision({"type": "wait"}, "simple: bounded safe reobservation of cold-cloud route obstruction")
    action.simple_obstruction = "cold"
    return mark(action)
