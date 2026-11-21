"""Strength discovery only after an admitted descent, never a potion identity guess."""
try:
    from .consumable_tactics import base_name, unknown_potion, discovery_score
    from .policy_geometry import distance, neighbors
    from .policy_decision import Intent
    from .puzzle_supplies import safe_test_bank
    from .potion_stash import can_protect_potions, protect_potions, advance_stash, potions
    from .room_supplies import requirements
    from .survival_policy import is_hostile
except ImportError:
    from consumable_tactics import base_name, unknown_potion, discovery_score
    from policy_geometry import distance, neighbors
    from policy_decision import Intent
    from puzzle_supplies import safe_test_bank
    from potion_stash import can_protect_potions, protect_potions, advance_stash, potions
    from room_supplies import requirements
    from survival_policy import is_hostile


PURPOSE = "pre-descent-strength"


def cancel(p, reason):
    p.planner.report["descent_potion_testing"] = {"status": "deferred", "reason": reason}
    if p.potion_stash and p.potion_stash.get("purpose") == PURPOSE:
        p.potion_stash["phase"] = "retrieve"
    p.descent_potion_plan = None


def begin(p, state):
    """Called only after descent has passed progression/quest/room hard gates."""
    if p.strength_identified or not any(unknown_potion(i) for i in state["inventory"]):
        return None
    if p.stop_on_incomplete_loot:
        try:
            from .loot_completion import pending_collections
        except ImportError:
            from loot_completion import pending_collections
        if pending_collections(p):
            return None  # The existing strict descent gate has not admitted departure.
    if not p.descent_potion_plan:
        p.descent_potion_plan = {"depth": state["depth"], "steps": 0, "candidate": None, "bank": None, "pending": False}
    return advance(p, state)


def advance(p, state):
    plan = p.descent_potion_plan
    if not plan or state.get("status") != "ready" or state.get("modal"):
        return None
    # This controller is admitted only by a descent decision. It does not need
    # the obsolete "every reachable tile visited" condition that vetoed run 37.
    if plan["depth"] != state["depth"] or p.strength_identified:
        cancel(p, "Strength identified or floor changed")
        return None
    if plan["pending"]:
        p.stop_gameplay("Pre-descent potion test lacks an accepted consumption receipt; never repeat it")
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    if p.puzzle_probe:
        return None  # Existing observed-effect recovery runs before this controller.
    if any(is_hostile(o) for o in state.get("objects", [])) or p.recent_threats \
            or state.get("danger_cells") or p.unseen_damage_turns:
        cancel(p, "Threats or unexplained damage interrupt potion discovery")
        return None
    if p.pharmacophobia or hero["hp"] < .85 * hero["max_hp"] or any(
            t in buffs for t in ("starving", "burn", "poison", "bleed", "ooze", "blind", "vertigo",
                                "paral", "root", "frozen", "chill", "levitat", "magic immun", "drowsy", "sleep")):
        cancel(p, "Health, impairment or challenge rules do not admit a safe unknown drink")
        return None
    if requirements(p, state) or p.room_journey or p.drop_plan or p.trap_payload_return:
        cancel(p, "Preserve supplies for an unfinished recognized potion room or retrieval")
        return None
    if p.potion_stash and p.potion_stash.get("purpose") != PURPOSE:
        cancel(p, "An existing potion stash must be retrieved first")
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
            if not p.potion_stash and not can_protect_potions(p, staged, item, distance, neighbors, safe_test_bank):
                continue
            choices.append((p.tiles[cell]["terrain"] != 29, len(route),
                            -discovery_score(item, p.consumable_sources), cell, item))
    if not choices:
        cancel(p, "No safe water/water-escape bank with verified potion-inventory protection")
        return None
    _, _, _, bank, candidate = min(choices, key=lambda c: c[:4])
    plan.update(candidate=base_name(candidate), bank=bank)
    if pos != bank:
        return p.toward(state, bank, "identify: stage pre-descent strength discovery on safe water",
                        paths, intent=Intent.REPOSITION)
    if not p.potion_stash:
        stash = protect_potions(p, state, candidate, distance, neighbors, safe_test_bank)
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
