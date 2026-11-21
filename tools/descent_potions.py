"""Strength discovery only after an admitted descent, never a potion identity guess."""
try:
    from .consumable_tactics import base_name, unknown_potion, discovery_score
    from .policy_geometry import distance, neighbors
    from .policy_decision import Intent, PlannerStuck
    from .puzzle_supplies import safe_test_bank
    from .potion_stash import can_protect_potions, protect_potions, advance_stash, potions
    from .room_supplies import requirements
    from .survival_policy import is_hostile
except ImportError:
    from consumable_tactics import base_name, unknown_potion, discovery_score
    from policy_geometry import distance, neighbors
    from policy_decision import Intent, PlannerStuck
    from puzzle_supplies import safe_test_bank
    from potion_stash import can_protect_potions, protect_potions, advance_stash, potions
    from room_supplies import requirements
    from survival_policy import is_hostile


PURPOSE = "pre-descent-strength"


def potion_inventory(state):
    return tuple(sorted((base_name(i), i.get("quantity", 1),
                         tuple(sorted(i.get("actions", [])))) for i in potions(state)))


def remember_bank(p, state):
    """Remember actual drink/stash feasibility, not hypothetical visibility."""
    if not hasattr(p, "puzzle_probe"):
        return  # The shared runner also observes policies without Mage discovery.
    if p.potion_stash or p.puzzle_probe or p.recent_threats or p.unseen_damage_turns \
            or state.get("danger_cells") or any(is_hostile(o) for o in state.get("objects", [])):
        return
    cell = state["hero"]["cell"]
    if not safe_test_bank(p, state, cell, distance, neighbors, allow_dry=True):
        return
    width, height = state["map"]["width"], state["map"]["height"]
    if p.tiles[cell]["terrain"] != 29 and not any(
            p.tiles.get(n, {}).get("terrain") == 29 and p.walkable(n)
            and not any(p.tiles[n].get(k) for k in ("effects", "trap", "plant"))
            for n in neighbors(cell, width, height)):
        return
    if any(unknown_potion(i) and "DRINK" in i.get("actions", [])
           and can_protect_potions(p, state, i, distance, neighbors, safe_test_bank,
                                  isolated_stack=True) for i in state["inventory"]):
        p.descent_potion_bank_receipt = (state["depth"], state.get("branch", 0),
                                         cell, potion_inventory(state))


def revisit_bank(p, state, paths):
    """Reobserve a previously admitted bank; never authorize a drink from memory."""
    receipt = getattr(p, "descent_potion_bank_receipt", None)
    if not receipt or p.potion_stash or p.descent_potion_plan.get("return_steps", 0) >= 12:
        return None
    depth, branch, bank, inventory = receipt
    if (depth, branch, inventory) != (state["depth"], state.get("branch", 0), potion_inventory(state)) \
            or bank == state["hero"]["cell"] or bank not in paths:
        return None
    route = p.route(paths, bank)
    if len(route) > 13:
        return None
    forbidden = p.navigation_barriers(state, Intent.REPOSITION)
    # A closed door is admitted only as ordinary transit, not as a test bank.
    if any(c in forbidden or not p.tiles[c].get("observed")
           or p.tiles[c]["terrain"] not in {1, 3, 5, 6, 9, 11, 14, 19, 20, 29}
           or any(p.tiles[c].get(k) for k in ("effects", "plant", "trap"))
           or c in p.loot for c in route[1:]):
        return None
    step = route[1]
    if not p.tiles[step].get("visible") or not p.escape_step_allowed(state, step):
        return None
    try:
        from .hunger_budget import admits, travel_cost
    except ImportError:
        from hunger_budget import admits, travel_cost
    if not admits(p, state, 2 * travel_cost(state, p, route) + 14):
        return None
    decision = p.toward(state, bank, "identify: reobserve previously verified pre-descent bank",
                        paths, intent=Intent.REPOSITION)
    if decision:
        decision.descent_bank_return = True
    return decision


def cancel(p, reason):
    p.planner.report["descent_potion_testing"] = {"status": "deferred", "reason": reason}
    if p.potion_stash and p.potion_stash.get("purpose") == PURPOSE:
        p.potion_stash["phase"] = "retrieve"
    p.descent_potion_plan = None


def pause(p, reason):
    """Keep the discovery obligation; safety arbitration may run before resuming."""
    p.planner.report["descent_potion_testing"] = {"status": "paused", "reason": reason}


def wait_effect(p, state):
    plan = p.descent_potion_plan
    tile = p.tiles.get(state["hero"]["cell"], {})
    if plan.get("waits", 0) >= 64:
        raise PlannerStuck("Pre-descent potion discovery: temporary effect did not clear within recovery budget")
    if tile.get("terrain") not in {1, 3, 9, 11, 14, 19, 20, 29} or tile.get("effects") \
            or tile.get("plant") or tile.get("trap") or state["hero"]["cell"] in p.room_blocked:
        return None
    decision = p.decision({"type": "wait"}, "identify: pause mandatory discovery until temporary potion effect clears",
                          intent=Intent.RECOVER)
    decision.descent_potion_wait = True
    return decision


def begin(p, state):
    """Called only after descent has passed progression/quest/room hard gates."""
    owned_strength = next((i for i in state["inventory"] if base_name(i) == "potion of strength"), None)
    stash = p.potion_stash and p.potion_stash.get("purpose") == PURPOSE
    if p.strength_identified and not owned_strength and not stash:
        return None
    if not any(unknown_potion(i) for i in state["inventory"]) and not owned_strength and not stash:
        return None
    if p.stop_on_incomplete_loot:
        try:
            from .loot_completion import pending_collections
        except ImportError:
            from loot_completion import pending_collections
        if pending_collections(p):
            return None  # The existing strict descent gate has not admitted departure.
    if not p.descent_potion_plan:
        p.descent_potion_plan = {"depth": state["depth"], "steps": 0, "waits": 0,
                                "candidate": None, "bank": None, "pending": False}
    action = advance(p, state)
    if action:
        return action
    stash = p.potion_stash and p.potion_stash.get("purpose") == PURPOSE
    if stash or owned_strength or not p.strength_identified and any(unknown_potion(i) for i in state["inventory"]):
        reason = p.planner.report.get("descent_potion_testing", {}).get("reason", "discovery/retrieval incomplete")
        raise PlannerStuck("Cannot descend before potion discovery: " + reason)
    return None


def advance(p, state):
    plan = p.descent_potion_plan
    if not plan or state.get("status") != "ready" or state.get("modal"):
        return None
    # This controller is admitted only by a descent decision. It does not need
    # the obsolete "every reachable tile visited" condition that vetoed run 37.
    if plan["depth"] != state["depth"]:
        raise PlannerStuck("Mandatory potion discovery crossed floors before completion")
    if p.strength_identified and not p.potion_stash \
            and not any(base_name(i) == "potion of strength" for i in state["inventory"]):
        cancel(p, "Strength identified and all known strength doses consumed")
        return None
    if plan["pending"]:
        p.stop_gameplay("Pre-descent potion test lacks an accepted consumption receipt; never repeat it")
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    if p.puzzle_probe:
        return None  # Existing observed-effect recovery runs before this controller.
    if any(is_hostile(o) for o in state.get("objects", [])) or p.recent_threats \
            or state.get("danger_cells") or p.unseen_damage_turns:
        pause(p, "Threats or unexplained damage interrupt potion discovery")
        return None
    if hero["hp"] < .85 * hero["max_hp"] or any(
            t in buffs for t in ("starving", "burn", "poison", "bleed", "ooze", "vertigo",
                                "paral", "root", "frozen", "chill", "drowsy", "sleep")):
        pause(p, "Health or impairment does not admit a safe unknown drink")
        return None
    if any(t in buffs for t in ("blind", "levitat", "magic immun")):
        pause(p, "Temporary potion effect; resume discovery after it expires")
        return wait_effect(p, state)
    identify = next((i for i in state["inventory"] if base_name(i) == "scroll of identify"
                     and "READ" in i.get("actions", []) and p.item_action_allowed(i, "READ")), None)
    if identify and not p.strength_identified and not p.potion_stash:
        try:
            from .consumable_tactics import identify_retry_allowed
        except ImportError:
            from consumable_tactics import identify_retry_allowed
        if identify_retry_allowed(p, state):
            p.menu_plan = "discover-scroll"
            p.consumable_menu_bags = set()
            return p.use(identify, "READ", "identify: mandatory pre-descent strength discovery")
    if p.pharmacophobia:
        pause(p, "Pharmacophobia forbids discovery drinking; a safe identification resource is required")
        return None
    # Known reserved supplies can remain safely in the stash. Do not let a
    # deferred room blanket-veto unrelated colors when its supplies are held.
    needed = {}
    for demand in requirements(p, state):
        needed[demand.potion] = needed.get(demand.potion, 0) + 1
    own_stash = p.potion_stash and p.potion_stash.get("purpose") == PURPOSE
    if (not own_stash and any(
            sum(i.get("quantity", 1) for i in state["inventory"] if base_name(i) == name) < count
            for name, count in needed.items())) or p.room_journey or p.drop_plan or p.trap_payload_return:
        pause(p, "Preserve missing supplies for an unfinished recognized potion room or retrieval")
        return None
    if p.potion_stash and p.potion_stash.get("purpose") != PURPOSE:
        pause(p, "An existing potion stash must be retrieved first")
        return None
    plan["steps"] += 1
    if plan["steps"] > 128:
        p.stop_gameplay("Pre-descent strength discovery exceeded its bounded preparation budget")
    if p.potion_stash:
        action = advance_stash(p, state, [], distance)
        if action:
            return action
        if p.potion_stash and p.potion_stash["phase"] != "ready":
            return None
    strength = next((i for i in state["inventory"] if base_name(i) == "potion of strength"
                     and "DRINK" in i.get("actions", []) and p.item_action_allowed(i, "DRINK")), None)
    if strength:
        return p.use(strength, "DRINK", "prepare: consume known strength before descending")
    if p.strength_identified:
        cancel(p, "Strength identified and stash retrieved")
        return None
    candidates = sorted((i for i in state["inventory"] if unknown_potion(i)
                         and "DRINK" in i.get("actions", [])
                         and p.item_action_allowed(i, "DRINK")
                         and base_name(i) not in p.descent_potion_tests),
                        key=lambda i: discovery_score(i, p.consumable_sources), reverse=True)
    if not candidates:
        cancel(p, "No unidentified untested potion remains")
        return None
    paths = p.paths(state)
    pos, width, height = hero["cell"], state["map"]["width"], state["map"]["height"]
    choices = []
    for item in candidates:
        if plan["candidate"] and base_name(item) != plan["candidate"]:
            continue
        for cell in paths:
            route = p.route(paths, cell)
            if len(route) > 13 or not safe_test_bank(p, state, cell, distance, neighbors, allow_dry=True):
                continue
            # Prefer standing in water. A dry fallback must still have an
            # adjacent observed water escape; do not test fire on flammable land.
            if p.tiles[cell]["terrain"] != 29 and not any(
                    p.tiles.get(n, {}).get("terrain") == 29 and p.walkable(n)
                    and not p.tiles[n].get("effects") and not p.tiles[n].get("trap")
                    and not p.tiles[n].get("plant") for n in neighbors(cell, width, height)):
                continue
            if any(p.tiles[c].get("effects") or p.tiles[c].get("plant") or p.tiles[c].get("trap")
                   or p.tiles[c]["terrain"] not in {1, 3, 9, 11, 14, 19, 20, 29} for c in route[1:]):
                continue
            staged = dict(state, hero=dict(hero, cell=cell))
            if not p.potion_stash and not can_protect_potions(
                    p, staged, item, distance, neighbors, safe_test_bank, isolated_stack=True):
                continue
            choices.append((p.tiles[cell]["terrain"] != 29, len(route),
                            -discovery_score(item, p.consumable_sources), cell, item))
    if not choices:
        returning = revisit_bank(p, state, paths)
        if returning:
            return returning
        pause(p, "No safe water/water-escape bank with verified potion-inventory protection")
        return None
    _, _, _, bank, candidate = min(choices, key=lambda c: c[:4])
    plan.update(candidate=base_name(candidate), bank=bank)
    if pos != bank:
        return p.toward(state, bank, "identify: stage pre-descent strength discovery on safe water",
                        paths, intent=Intent.REPOSITION)
    if not p.potion_stash:
        stash = protect_potions(p, state, candidate, distance, neighbors, safe_test_bank, isolated_stack=True)
        if p.potion_stash:
            p.potion_stash["purpose"] = PURPOSE
        if stash:
            return stash
    if p.potion_stash:
        p.potion_stash["phase"] = "retrieve"
    plan["pending"] = True
    p.puzzle_probe = {"depth": state["depth"], "kind": PURPOSE, "turns": 0}
    decision = p.use(candidate, "DRINK", "identify: test unknown potion before descending until strength is identified")
    decision.potion_purpose = PURPOSE
    return decision


def observe(p, before, decision, after):
    """Only accepted inventory/effect observations confirm a drink or strength."""
    if before.get("depth") == after.get("depth") and before.get("branch", 0) == after.get("branch", 0) \
            and before.get("status") == "ready" and not before.get("modal") \
            and p.last_state and p.last_state.get("hero", {}).get("cell") == before.get("hero", {}).get("cell"):
        remember_bank(p, before)
        if getattr(decision, "descent_bank_return", False) and p.descent_potion_plan:
            plan = p.descent_potion_plan
            plan["return_steps"] = plan.get("return_steps", 0) + 1
    if getattr(decision, "descent_potion_wait", False):
        if p.descent_potion_plan and decision.action == {"type": "wait"} \
                and before.get("depth") == after.get("depth") == p.descent_potion_plan["depth"] \
                and before.get("branch", 0) == after.get("branch", 0):
            p.descent_potion_plan["waits"] = p.descent_potion_plan.get("waits", 0) + 1
            return {"purpose": PURPOSE, "recovery_waits": p.descent_potion_plan["waits"],
                    "strength_identified": p.strength_identified, "collection_credited": False}
        return None
    item = next((i for i in before.get("inventory", []) if i.get("id") == decision.action.get("id")), None)
    if decision.action.get("action") != "DRINK" or not item or not unknown_potion(item):
        return None
    if "inventory" not in after or not after.get("hero") or before.get("depth") != after.get("depth"):
        return None
    if sum(i.get("quantity", 1) for i in potions(before)) <= sum(i.get("quantity", 1) for i in potions(after)):
        return None
    testing = getattr(decision, "potion_purpose", None) == PURPOSE
    if testing:
        p.descent_potion_tests.add(base_name(item))
        if p.descent_potion_plan:
            p.descent_potion_plan.update(pending=False, candidate=None, bank=None)
    # Ordinary strength's actual +1 is observed, not inferred from color, floor
    # placement or a proposed action. Exotic adrenaline is not an identity receipt.
    old_strength = before.get("hero", {}).get("strength")
    new_strength = after.get("hero", {}).get("strength")
    gain = new_strength - old_strength if all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in (old_strength, new_strength)) else None
    buffs = " ".join(b["name"].lower() for b in after.get("hero", {}).get("buffs", []))
    if (gain == 1 and "adrenaline" not in buffs) or any(
            base_name(i) == "potion of strength" for i in after.get("inventory", [])):
        p.strength_identified = True
    if not testing and not p.strength_identified:
        return None
    return {"tested": base_name(item), "strength_identified": p.strength_identified,
            "purpose": PURPOSE if testing else "observed unknown drink", "collection_credited": False}
