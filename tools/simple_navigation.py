"""Ordinary observed pickups, frontiers, and latched floor-local descent.

No quest, puzzle objective, coverage sweep, remembered-enemy patrol, or
wall-search expedition. Shared combat and hazard admission still own safety.
"""
try:
    from .policy_decision import Intent
    from .policy_geometry import distance, neighbors
    from .survival_policy import is_hostile
    from .mimic_tactics import suspicious_container
    from .hidden_doors import corridor_ends, secret_search_allowed
    from .inventory_tactics import discarded
except ImportError:
    from policy_decision import Intent
    from policy_geometry import distance, neighbors
    from survival_policy import is_hostile
    from mimic_tactics import suspicious_container
    from hidden_doors import corridor_ends, secret_search_allowed
    from inventory_tactics import discarded


def observe(p, state):
    if state.get("scene") != "GameScene" or not state.get("hero"):
        return None
    scope = (state["depth"], state.get("branch", 0))
    level = state["hero"].get("level", 1)
    floor = p.simple_floors.setdefault(scope, {
        "entry_level": level, "level_gained": False, "searches": {},
        "navigation_inputs": 0, "deferred": {}, "missing_sites": set()})
    # A witnessed empty pickup site must not resurrect as soon as it leaves
    # sight. This is absence evidence, NOT a collection receipt. Reopen only
    # when a fresh visible heap/container is actually observed there.
    visible = {t["cell"] for t in state.get("map", {}).get("cells", [])
               if t.get("visible") and t.get("observed") is not False}
    present = {o["cell"] for o in state.get("objects", [])
               if o.get("top_item") or "chest" in o.get("name", "").lower()}
    floor["missing_sites"].update(set(p.unconfirmed_loot) & (visible - present))
    floor["missing_sites"].difference_update(visible & present)
    floor["level_gained"] |= level > floor["entry_level"]
    p.planner.report["simple_floor"] = {
        "entry_level": floor["entry_level"], "level_gained": floor["level_gained"],
        "navigation_inputs": floor["navigation_inputs"],
        "search_inputs": sum(floor["searches"].values())}
    return floor


def accepted(p, before, decision, after):
    floor = observe(p, before)
    if floor is None:
        return
    cell = getattr(decision, "simple_search", None)
    if cell is not None:
        floor["searches"][cell] = floor["searches"].get(cell, 0) + 1
    if getattr(decision, "simple_navigation", False):
        floor["navigation_inputs"] += 1
    observe(p, after)


def paths(p, state):
    # Exclude puzzle locks even when a key is held. Worn/skeleton gates are
    # main-progression gates and retain normal key-backed walkability.
    forbidden = {c for c, t in p.tiles.items()
                 if t["terrain"] in {7, 10, 31, 37} or
                 (t.get("observed") is False) or
                 (t.get("plant") or t.get("trap") and t["terrain"] != 19)}
    forbidden.update(o["cell"] for o in state.get("objects", []) if is_hostile(o))
    if p.recent_threats:
        try:
            from .challenge_combat import exposure
            from .policy_geometry import line_clear
        except ImportError:
            from challenge_combat import exposure
            from policy_geometry import line_clear
        threats = list(p.recent_threats.values())
        forbidden.update(c for c in p.tiles if c != state["hero"]["cell"]
                         and exposure(p, state, threats, c, distance, line_clear)["exposure"])
    return p.paths(state, forbidden)


def loot(p, state, previous=None):
    floor = observe(p, state)
    previous = paths(p, state) if previous is None else previous
    skipped = p.skipped_special_floor(state, previous)
    eligible, excluded = {}, {}
    for cell, obj in {**p.unconfirmed_loot, **p.loot}.items():
        if obj.get("for_sale"):
            continue
        name = obj.get("name", "").lower()
        reason = None
        if discarded(p, cell, obj):
            reason = "Previously declined/discarded item; no repeated inventory loop"
        elif cell in floor["missing_sites"]:
            reason = "Previously observed loot is absent on reobservation; collection unconfirmed"
        elif cell not in previous or cell in skipped or cell in p.blocked:
            reason = "No currently admitted ordinary route (hazard, lock or inaccessible area)"
        elif name in {"crystal chest", "tomb", "skeleton", "skeletal remains"}:
            reason = "Excluded special container"
        elif suspicious_container(obj):
            reason = "Suspicious container requires a separate encounter"
        elif "locked chest" in name and not p.keys.get("golden", 0):
            reason = "Missing chest key; no key-search expedition"
        elif cell in p.combat_deferred_loot:
            reason = "Pickup remains combat-deferred"
        elif p.room_loot_deferred.get(cell) is not None:
            # A freshly changed inventory makes a refused full-pack pickup
            # eligible again; never repeat it forever with the same pack.
            try:
                from .room_loot import inventory_context
            except ImportError:
                from room_loot import inventory_context
            if p.room_loot_deferred[cell] == inventory_context(state):
                reason = "Pickup refused with unchanged inventory"
        if reason:
            excluded[cell] = {"cell": cell, "name": obj.get("name", "loot"), "reason": reason}
        else:
            eligible[cell] = obj
    return eligible, excluded


def defer(p, state, excluded):
    floor = observe(p, state)
    for cell, item in excluded.items():
        if floor["deferred"].get(cell) != item["reason"]:
            p.defer_obligations(state, [{"kind": "simple-bot excluded pickup", **item}],
                                item["reason"])
            floor["deferred"][cell] = item["reason"]
    p.planner.report["simple_excluded_pickups"] = list(excluded.values())


def mark(decision):
    if decision:
        decision.simple_navigation = True
    return decision


def dead_end_search(p, state, floor, exits):
    if floor["level_gained"] and exits or not secret_search_allowed(state, p):
        return None
    pos = state["hero"]["cell"]
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if floor["searches"].get(pos, 0) >= 2 or sum(floor["searches"].values()) >= 16 \
            or state["hero"]["hp"] < .7 * state["hero"]["max_hp"] \
            or any(t in buffs for t in ("hungry", "starving", "burn", "poison", "blind", "root")):
        return None
    ends = corridor_ends(p.tiles, state["map"]["width"], state["map"]["height"])
    if not any(distance(pos, wall, state["map"]["width"]) == 1
               and p.tiles[wall].get("visible") for wall in ends):
        return None
    decision = p.decision({"type": "search"}, "simple: incidental dead-end search")
    decision.simple_search = pos
    return mark(decision)


def choose(p, state, enemies):
    floor = observe(p, state)
    if any(not e.get("sleeping") for e in enemies) or state.get("danger_cells"):
        p.stop_no_safe_action("Simple navigation cannot bypass an unresolved combat threat")
    if floor["navigation_inputs"] >= 2048:
        p.stop_gameplay("Simple ordinary navigation exhausted its accepted-input budget",
                        kind="navigation-stalled")
    previous = paths(p, state)
    pos = state["hero"]["cell"]
    # A frontier is a vantage for new observations, not a tile-coverage target.
    p.exhausted.add(pos)
    targets, excluded = loot(p, state, previous)
    defer(p, state, excluded)
    for cell in sorted(targets, key=lambda c: ("key" not in targets[c]["name"].lower(),
                                              len(p.route(previous, c)), c)):
        action = p.toward(state, cell, "simple: collect observed ordinary loot",
                          previous, intent=Intent.LOOT)
        if action:
            return mark(action)
        p.stop_gameplay("Observed ordinary loot lacks a dispatchable pickup action",
                        kind="mandatory-preparation-unresolved")
    exits = [c for c in previous if p.tiles[c]["terrain"] in {8, 22}]
    report = p.exploration_report(state, previous)
    doors = [c for c in report["unopened_doors"] if c != pos]
    frontiers = [c for c in previous if c != pos and c not in p.exhausted
                 and c not in p.skipped_special_floor(state, previous)
                 and p.tiles[c]["terrain"] not in {7, 8, 10, 21, 22, 31, 37, 38}
                 and any(n not in p.tiles or p.tiles[n].get("observed") is False
                         for n in neighbors(c, state["map"]["width"], state["map"]["height"]))]
    reason = "level gained" if floor["level_gained"] else "ordinary doors/frontiers exhausted"
    requested = floor["level_gained"] or not (doors or frontiers)
    p.planner.report["simple_descent"] = {
        "requested": requested, "reason": reason, "doors": doors, "frontiers": frontiers,
        "stairs": exits, "full_floor_clear_claimed": False}
    locked = any("locked" in b["name"].lower() for b in state["hero"].get("buffs", []))
    if requested and exits and not locked:
        target = min(exits, key=lambda c: len(p.route(previous, c)))
        return mark(p.toward(state, target, "simple: descend after " + reason,
                             previous, intent=Intent.DESCEND))
    search = dead_end_search(p, state, floor, exits) if not enemies else None
    if search:
        return search
    # After leveling, this is only a search for unknown/unreachable downstairs.
    for target in sorted(set(doors + frontiers), key=lambda c: len(p.route(previous, c))):
        action = p.toward(state, target, "simple: ordinary door/frontier" if not requested
                          else "simple: find reachable downstairs", previous, intent=Intent.EXPLORE)
        if action:
            return mark(action)
    p.stop_gameplay("Simple exploration exhausted without usable downstairs"
                    + (" (floor remains boss-locked)" if locked else ""),
                    kind="navigation-stalled")


def before_descent(p, state, decision):
    enemies = [o for o in state.get("objects", []) if is_hostile(o)]
    if any(not e.get("sleeping") for e in enemies) or state.get("danger_cells") or any(
            "locked" in b["name"].lower() for b in state["hero"].get("buffs", [])):
        p.stop_no_safe_action("Simple descent interrupted by threat, warning or locked floor")
    targets, excluded = loot(p, state)
    defer(p, state, excluded)
    if targets:
        return choose(p, state, enemies)
    try:
        from .descent_potions import begin
    except ImportError:
        from descent_potions import begin
    preparation = begin(p, state)
    if preparation:
        return preparation
    if p.physical_ledger.has_unresolved() or any(getattr(p, k, None) for k in (
            "potion_stash", "trap_payload_return", "puzzle_probe", "drop_plan", "room_journey")):
        p.stop_gameplay("Simple descent requires owned-item retrieval/transfer completion",
                        kind="mandatory-preparation-unresolved")
    return decision
