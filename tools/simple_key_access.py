"""Key spending includes witnessed room entry, not just removing the lock."""
try:
    from .policy_geometry import neighbors
    from .policy_decision import Intent
except ImportError:
    from policy_geometry import neighbors
    from policy_decision import Intent


DOORS = {10: "iron", 31: "crystal", 38: "skeleton"}


def count(state, kind):
    return sum(k.get("quantity", 0) for k in state.get("keys", [])
               if k.get("depth") == state["depth"] and
               f"{kind} key" in k.get("name", "").lower())


def accepted(p, before, decision, after, floor):
    if before.get("depth") != after.get("depth") or before.get("branch", 0) != after.get("branch", 0):
        return
    for plan in floor.get("key_entries", []):
        if not plan.get("done") and getattr(decision, "simple_key_entry", None) == plan["door"]:
            plan["steps"] += 1
        if after["hero"]["cell"] == plan["door"]:
            plan["entered_threshold"] = True
    if getattr(decision, "simple_key_search", False):
        floor["key_search_inputs"] = floor.get("key_search_inputs", 0) + 1
    target = decision.action.get("cell") if decision.action.get("type") == "cell" else None
    old = next((t for t in before.get("map", {}).get("cells", []) if t["cell"] == target), {})
    new = next((t for t in after.get("map", {}).get("cells", []) if t["cell"] == target), {})
    kind = DOORS.get(old.get("terrain"))
    if not kind or not new.get("visible") or new.get("terrain") not in {5, 6} \
            or count(after, kind) != count(before, kind) - 1:
        return
    # p.tiles still describes the accepted input's BEFORE observation here.
    baseline = set(p.paths(before))
    baseline.discard(target)
    floor.setdefault("key_entries", []).append({
        "door": target, "kind": kind, "baseline": baseline, "steps": 0,
        "entered_threshold": after["hero"]["cell"] == target,
        "inside": False, "seen_vantages": set(), "done": False})


def follow_through(p, state, previous, floor):
    """Finish safe entry/reobservation before a newly unlocked door is forgotten."""
    for plan in floor.get("key_entries", []):
        if plan["done"]:
            continue
        door, pos = plan["door"], state["hero"]["cell"]
        plan["seen_vantages"].add(pos)
        # Flood only newly accessible room floor. Existing outside routes,
        # other thresholds and hazards delimit this small entry objective.
        w, h = state["map"]["width"], state["map"]["height"]
        region, queue = set(), [door]
        while queue and len(region) < 256:
            cell = queue.pop()
            if cell in region:
                continue
            region.add(cell)
            for n in neighbors(cell, w, h):
                if n not in region and n not in plan["baseline"] and n in previous \
                        and p.tiles[n]["terrain"] in {1, 2, 3, 9, 11, 14, 15, 19, 20, 29, 30}:
                    queue.append(n)
        inside = region - {door}
        if pos in inside:
            plan["inside"] = True
        frontiers = [c for c in inside if c not in plan["seen_vantages"] and any(
            n not in p.tiles or p.tiles[n].get("observed") is False for n in neighbors(c, w, h))]
        target = None
        if not plan["entered_threshold"]:
            target = door if door in previous else None
        elif not plan["inside"]:
            target = min(inside, key=lambda c: (len(p.route(previous, c)), c)) if inside else None
        elif frontiers:
            target = min(frontiers, key=lambda c: (len(p.route(previous, c)), c))
        if target is not None and plan["steps"] < 64:
            action = p.toward(state, target, "simple: enter and inspect room after using key",
                              previous, intent=Intent.EXPLORE)
            if action:
                action.simple_navigation = True
                action.simple_key_entry = door
                return action
        if plan["inside"] and not frontiers:
            plan["done"] = True
            plan["result"] = "Room entered and ordinary observation frontiers exhausted; no full-clear claim"
        else:
            plan["done"] = True
            plan["result"] = "Entry deferred: no currently admitted interior route or entry budget exhausted"
            p.defer_obligations(state, [{"kind": "unlocked room entry", "cell": door}],
                                plan["result"])
    p.planner.report["simple_key_entries"] = [
        {k: plan[k] for k in ("door", "kind", "steps", "entered_threshold", "inside", "done", "result")
         if k in plan} for plan in floor.get("key_entries", [])]
    return None
