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
    try:
        from .simple_key_access import accepted as accepted_key
    except ImportError:
        from simple_key_access import accepted as accepted_key
    accepted_key(p, before, decision, after, floor)
    cell = getattr(decision, "simple_search", None)
    if cell is not None:
        floor["searches"][cell] = floor["searches"].get(cell, 0) + 1
    if getattr(decision, "simple_navigation", False):
        floor["navigation_inputs"] += 1
    harvest = getattr(decision, "simple_harvest_target", None)
    if harvest is not None:
        floor["harvest_inputs"] = floor.get("harvest_inputs", 0) + 1
        if after.get("hero", {}).get("cell") == harvest:
            floor.setdefault("harvest_attempts", {})[harvest] = 1
    if getattr(decision, "simple_threat_reobserve", False):
        floor["threat_reobservations"] = floor.get("threat_reobservations", 0) + 1
    if getattr(decision, "simple_flight_staging", False):
        floor["flight_staging"] = floor.get("flight_staging", 0) + 1
    if getattr(decision, "simple_flight_input", False) and floor.get("flight_transit"):
        floor["flight_transit"]["inputs"] += 1
    obstruction = getattr(decision, "simple_obstruction", None)
    if obstruction:
        waits = floor.setdefault("obstruction_waits", {})
        waits[obstruction] = waits.get(obstruction, 0) + 1
    if getattr(decision, "ordinary_trap_action", None):
        try:
            from .ordinary_traps import accepted as accepted_trap
        except ImportError:
            from ordinary_traps import accepted as accepted_trap
        accepted_trap(p, before, decision, after)
    observe(p, after)


def remembered_threats(p, state):
    threats = list(p.recent_threats.values())
    try:
        from .public_evidence import binding_in_scope
    except ImportError:
        from public_evidence import binding_in_scope
    memory = p.dm100_threat
    if binding_in_scope(memory, state) and not any(
            e["cell"] == memory["cell"] and e["name"].lower() == "dm-100" for e in threats):
        threats.append(dict(memory, name="DM-100"))
    return threats


def paths(p, state, *, avoid_memories=True, avoid_retreats=True):
    # Iron doors are ordinary key-backed access, not puzzle objectives.
    # Shared paths stop at every lock,
    # so opening it requires a fresh observation before traversing beyond it.
    forbidden = {c for c, t in p.tiles.items()
                  if t["terrain"] in {7, 37} or
                 (t.get("observed") is False) or
                  (t.get("plant") or t.get("trap") and t["terrain"] != 19)}
    try:
        from .keyed_rooms import crystal_keys_ready
    except ImportError:
        from keyed_rooms import crystal_keys_ready
    if not crystal_keys_ready(p):
        forbidden.update(c for c, t in p.tiles.items() if t["terrain"] == 31)
    forbidden.update(o["cell"] for o in state.get("objects", []) if is_hostile(o))
    threats = remembered_threats(p, state) if avoid_memories else []
    if threats:
        try:
            from .challenge_combat import exposure
            from .policy_geometry import line_clear
        except ImportError:
            from challenge_combat import exposure
            from policy_geometry import line_clear
        forbidden.update(c for c in p.tiles if c != state["hero"]["cell"]
                          and exposure(p, state, threats, c, distance, line_clear)["exposure"])
        try:
            from .dm100_escape import sees
        except ImportError:
            from dm100_escape import sees
        forbidden.update(c for c in p.tiles if c != state["hero"]["cell"] and any(
            e["name"].lower() == "dm-100" and sees(p, state, e["cell"], c) for e in threats))
    edges = {(destination, origin) for origin, destination in
             (p.escape_commitment or {}).get("edges", [])} if avoid_retreats else set()
    return p.paths(state, forbidden, forbidden_edges=edges)


def reobserve_temporary_threats(p, state, enemies, floor):
    """Do not mislabel short-lived remembered exposure as floor exhaustion."""
    threats = remembered_threats(p, state)
    if enemies or not (threats or p.escape_commitment) or state.get("danger_cells") \
            or floor.get("threat_reobservations", 0) >= 16:
        return None
    if any(e.get("sleeping") for e in threats):
        return None  # Never wait for sleepers to approach.
    hero = state["hero"]
    tile = p.tiles.get(hero["cell"], {})
    if tile.get("effects") or tile.get("plant") \
            or tile.get("trap") and tile["terrain"] != 19 or p.unseen_damage_turns \
            or any(any(k in b["name"].lower() for k in (
                "starv", "burn", "poison", "bleed", "ooze", "vertigo", "paral"))
                   for b in hero.get("buffs", [])):
        return None
    try:
        from .challenge_combat import exposure
        from .policy_geometry import line_clear
    except ImportError:
        from challenge_combat import exposure
        from policy_geometry import line_clear
    if exposure(p, state, threats, hero["cell"],
                distance, line_clear)["exposure"]:
        return None
    try:
        from .dm100_escape import exposed_memory
    except ImportError:
        from dm100_escape import exposed_memory
    if exposed_memory(p, state):
        return None
    # Counterfactual feasibility only, never permission to move through threats.
    potential = paths(p, state, avoid_memories=False, avoid_retreats=False)
    doors, frontiers = ordinary_work(p, state, potential)
    if not (doors or frontiers or any(p.tiles[c]["terrain"] in {8, 21, 22} for c in potential)):
        return None
    if hero["hp"] < .7 * hero["max_hp"]:
        # At low health prefer a freshly admitted ordinary step under cover
        # when available; never cross the remembered attack lane.
        safe = paths(p, state)
        steps = [c for c in neighbors(hero["cell"], state["map"]["width"], state["map"]["height"])
                 if c in safe and p.tiles[c].get("visible") and p.tiles[c].get("observed")
                 and p.tiles[c]["terrain"] in {1, 3, 14, 19, 20}
                 and not p.tiles[c].get("effects") and not p.tiles[c].get("plant")
                 and not p.tiles[c].get("trap") and c not in p.loot]
        if steps:
            target = min(steps, key=lambda c: (p.visits[c], c))
            action = p.toward(state, target, "simple: bounded covered reposition while threat route remains restricted",
                              safe, intent=Intent.EXPLORE)
            if action:
                action.simple_threat_reobserve = True
                return mark(action)
        # A closed-door pocket can have no admitted ordinary step. Opening
        # that door would break cover. Keep observing from this verified
        # zero-exposure tile rather than declaring the floor exhausted.
        # Critical health still requires rescue, not this optional wait.
        if hero["hp"] < .35 * hero["max_hp"]:
            return None
    action = p.decision({"type": "wait"}, "simple: bounded reobservation of temporary remembered threats")
    action.simple_threat_reobserve = True
    return mark(action)


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
        elif suspicious_container(obj):
            reason = "Suspicious container requires shared ranged investigation, not ordinary key opening"
        elif cell not in previous or cell in skipped or cell in p.blocked:
            reason = "No currently admitted ordinary route (hazard, lock or inaccessible area)"
        elif name in {"tomb", "skeleton", "skeletal remains"}:
            reason = "Excluded special container"
        elif name == "crystal chest" and cell not in p.allowed_chests:
            reason = "No admitted matching-key crystal chest choice"
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


def ordinary_work(p, state, previous):
    pos = state["hero"]["cell"]
    report = p.exploration_report(state, previous)
    skipped = p.skipped_special_floor(state, previous)
    doors = [c for c in report["unopened_doors"] if c != pos]
    doors.extend(c for c in previous if c != pos and p.tiles[c]["terrain"] == 10
                 and c not in skipped and p.keys.get("iron", 0))
    frontiers = [c for c in previous if c != pos and c not in p.exhausted
                 and c not in skipped
                 and p.tiles[c]["terrain"] not in {7, 8, 10, 21, 22, 31, 37, 38}
                 and any(n not in p.tiles or p.tiles[n].get("observed") is False
                         for n in neighbors(c, state["map"]["width"], state["map"]["height"]))]
    return doors, frontiers


def keyed_access(p, state, previous):
    """Spend held ordinary floor keys before leaving, without a key expedition."""
    try:
        from .simple_key_access import follow_through, DOORS
    except ImportError:
        from simple_key_access import follow_through, DOORS
    follow = follow_through(p, state, previous, observe(p, state))
    if follow:
        return follow
    targets = [c for c in previous if c != state["hero"]["cell"]
               and p.tiles[c]["terrain"] in DOORS
               and p.keys.get(DOORS[p.tiles[c]["terrain"]], 0)]
    p.planner.report["simple_keys"] = {
        "held_floor_keys": dict(p.keys), "reachable_keyed_doors": targets,
        "qualification": "Use known admitted locks before descent; no unsafe or exhaustive key-spending search"}
    for cell in sorted(targets, key=lambda c: (len(p.route(previous, c)), c)):
        action = p.toward(state, cell, "simple: use held key before descent",
                          previous, intent=Intent.EXPLORE)
        if action:
            return mark(action)
    return None


def key_search(p, state, previous, floor, doors, frontiers):
    """Remaining usable keys justify bounded ordinary exploration, not puzzles."""
    if not any(p.keys.get(k, 0) for k in ("iron", "golden", "crystal", "skeleton")) \
            or floor.get("key_search_inputs", 0) >= 64 \
            or state["depth"] == 5 and ("goo" in p.defeated_bosses or p.keys.get("worn", 0)):
        return None
    for cell in sorted(set(doors + frontiers), key=lambda c: (len(p.route(previous, c)), c)):
        action = p.toward(state, cell, "simple: seek ordinary matching lock before leaving with keys",
                          previous, intent=Intent.EXPLORE)
        if action:
            action.simple_key_search = True
            return mark(action)
    return None


def wooden_barricade(p, state, enemies):
    # Retain shared bounded bookshelf burning and scoped unknown-fire testing
    # beside actual barricades. Existing recovery owns ignition/expiry.
    if remembered_threats(p, state):
        return None
    try:
        from .wooden_barrier import known_burn
    except ImportError:
        from wooden_barrier import known_burn
    known = known_burn(p, state, enemies)
    if known:
        return mark(known)
    try:
        from .puzzle_supplies import prepare_supplies
    except ImportError:
        from puzzle_supplies import prepare_supplies
    return mark(prepare_supplies(p, state, enemies, distance, neighbors, wood_only=True))


def harvest_supplies(p, state, enemies):
    try:
        from .garden_tactics import harvest_supplies as harvest
    except ImportError:
        from garden_tactics import harvest_supplies as harvest
    return harvest(p, state, enemies, observe(p, state))


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
    harvest = harvest_supplies(p, state, enemies)
    if harvest:
        return harvest
    access = keyed_access(p, state, previous)
    if access:
        return access
    burn = wooden_barricade(p, state, enemies)
    if burn:
        return burn
    exits = [c for c in previous if p.tiles[c]["terrain"] in {8, 21, 22}]
    doors, frontiers = ordinary_work(p, state, previous)
    search_keys = key_search(p, state, previous, floor, doors, frontiers)
    if search_keys:
        return search_keys
    goo_defeated = state["depth"] == 5 and state.get("branch", 0) == 0 \
        and ("goo" in p.defeated_bosses or p.keys.get("worn", 0) > 0)
    reason = "Goo defeated" if goo_defeated else (
        "level gained" if floor["level_gained"] else "ordinary doors/frontiers exhausted")
    requested = goo_defeated or floor["level_gained"] or not (doors or frontiers)
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
    temporary = reobserve_temporary_threats(p, state, enemies, floor)
    if temporary:
        return temporary
    try:
        from .simple_obstructions import choose as observe_obstruction
    except ImportError:
        from simple_obstructions import choose as observe_obstruction
    temporary = observe_obstruction(p, state, enemies, floor)
    if temporary:
        return temporary
    if not enemies and not any(t["terrain"] in {8, 21, 22} for t in p.tiles.values()):
        try:
            from .preparation_prerequisites import reconnaissance
        except ImportError:
            from preparation_prerequisites import reconnaissance
        information = reconnaissance(p, state)
        if information:
            information.reason = "simple: use known mapping resource before declaring stairs search exhausted"
            return mark(information)
    try:
        from .simple_flight import choose as flight_transit
    except ImportError:
        from simple_flight import choose as flight_transit
    transit = flight_transit(p, state, enemies, floor, previous)
    if transit:
        return mark(transit)
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
    harvest = harvest_supplies(p, state, enemies)
    if harvest:
        return harvest
    access = keyed_access(p, state, paths(p, state))
    if access:
        return access
    burn = wooden_barricade(p, state, enemies)
    if burn:
        return burn
    previous = paths(p, state)
    doors, frontiers = ordinary_work(p, state, previous)
    search_keys = key_search(p, state, previous, observe(p, state), doors, frontiers)
    if search_keys:
        return search_keys
    remaining = {kind: count for kind, count in p.keys.items()
                 if count and kind != "worn"}
    if remaining:
        p.defer_obligations(state, [{
            "kind": "unspent floor keys", "keys": remaining,
            "reason": "No admitted known matching ordinary lock; unsafe/inaccessible/puzzle access not pursued"}],
            "Leaving with unspent keys; no safe known matching ordinary access")
    try:
        from .descent_potions import begin
    except ImportError:
        from descent_potions import begin
    preparation = begin(p, state)
    if preparation:
        return preparation
    if p.physical_ledger.has_unresolved() or any(getattr(p, k, None) for k in (
            "potion_stash", "trap_payload_return", "puzzle_probe", "drop_plan", "room_journey", "wood_burn_plan")):
        p.stop_gameplay("Simple descent requires owned-item retrieval/transfer completion",
                        kind="mandatory-preparation-unresolved")
    return decision
