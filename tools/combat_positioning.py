"""Shared observable positioning: rinse damage-over-time and close on zappers."""

try:
    from .policy_decision import Intent
    from .challenge_combat import reach
except ImportError:
    from policy_decision import Intent
    from challenge_combat import reach

ZAPPERS = {"dm-100", "gnoll shaman", "dwarf warlock"}
NON_MELEE = {"necromancer", "spectral necromancer"}
NO_DESTINATION = {5, 7, 8, 10, 21, 22, 31, 37, 38}


class CombatPositioningBlocked(RuntimeError):
    pass


class SkeletonSpacingBlocked(CombatPositioningBlocked):
    pass


def invisible_withdrawal(p, state, enemies, distance, line_clear):
    hero, width = state["hero"], state["map"]["width"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    threats = [e for e in enemies if not e.get("sleeping")]
    if any(s in buffs for s in ("invisib","cloaked")) and hero["hp"]<0.5*hero["max_hp"]:
        seen={e["cell"] for e in threats}
        threats.extend(e for e in getattr(p,"recent_threats",{}).values() if e["cell"] not in seen)
    if not any(s in buffs for s in ("invisib", "cloaked")) or hero["hp"] >= 0.5 * hero["max_hp"] or not threats:
        p.invisible_withdraw_steps = 0
        return None
    previous = p.paths(state, {e["cell"] for e in enemies})
    choices = []
    for cell in previous:
        route = p.route(previous, cell)
        if len(route) < 2 or len(route) > 7 or any(
                p.tiles[c]["terrain"] in NO_DESTINATION or p.tiles[c].get("plant")
                or c in p.loot or c in state.get("danger_cells", []) for c in route[1:]):
            continue
        separation = min(distance(cell, e["cell"], width) for e in threats)
        if separation < 4:
            continue
        covered = all(not line_clear(cell, e["cell"], width, p.tiles) for e in threats)
        step=route[1]
        step_separation=min(distance(step,e["cell"],width) for e in threats)
        immediate_cover=all(not line_clear(step,e["cell"],width,p.tiles) for e in threats)
        if step_separation<min(distance(hero["cell"],e["cell"],width) for e in threats) and not immediate_cover:
            continue
        choices.append((not immediate_cover,-step_separation,p.visits[step],not covered,len(route),-separation,cell))
    if choices and p.invisible_withdraw_steps < 12:
        p.invisible_withdraw_steps += 1
        return p.toward(state, min(choices)[-1], "combat: retreat under invisibility before reengaging", previous, intent=Intent.RETREAT)
    raise CombatPositioningBlocked("Low-HP invisibility: no bounded safe withdrawal; refusing to break invisibility with an attack")


def skeleton_spacing(p, state, enemies, distance, neighbors):
    hero, width = state["hero"], state["map"]["width"]
    # Do not grow this early-game danger band with the hero's maximum HP:
    # doing so falsely blocks survivable fights after each level-up.
    if hero["hp"] > 16:
        p.skeleton_retreats = 0
        return None
    targets = [e for e in enemies if e["name"].lower() in {"skeleton", "necromancer's skeleton", "dwarven skeleton"}
               and not e.get("sleeping") and distance(hero["cell"], e["cell"], width) == 1 and e.get("health_bar")
               and e["health_bar"][1] > 0 and e["health_bar"][0] / e["health_bar"][1] <= 0.5]
    if not targets:
        p.skeleton_retreats = 0
        return None
    fear = next((i for i in state["inventory"] if "stone of fear" in i["name"].lower()
                 and "THROW" in i.get("actions", [])), None)
    if fear and p.shot_clear(state, targets[0]["cell"]):
        return p.use(fear, "THROW", "survival: fear skeleton before fatal adjacent explosion", target=targets[0]["cell"])
    sleep = next((i for i in state["inventory"] if "stone of deep sleep" in i["name"].lower()
                  and "THROW" in i.get("actions", [])), None)
    if sleep and p.shot_clear(state, targets[0]["cell"]):
        return p.use(sleep, "THROW", "survival: sleep skeleton before fatal adjacent explosion", target=targets[0]["cell"])
    blink = next((i for i in state["inventory"] if "stone of blink" in i["name"].lower()
                  and "THROW" in i.get("actions", [])), None)
    if blink:
        previous = p.paths(state, {e["cell"] for e in enemies})
        cells = [c for c in previous if p.tiles[c]["terrain"] not in NO_DESTINATION
                 and not p.tiles[c].get("plant") and c not in state.get("danger_cells", [])
                 and not p.loot.get(c, {}).get("for_sale") and p.shot_clear(state, c)
                 and all(distance(c, e["cell"], width) >= 4 for e in enemies if not e.get("sleeping"))
                 and distance(hero["cell"], c, width) <= 6]
        if cells:
            cell = min(cells, key=lambda c: distance(hero["cell"], c, width))
            return p.use(blink, "THROW", "survival: blink clear of skeleton death blast", target=cell)
    escape = p.retreat(state, enemies)
    if escape and p.skeleton_retreats < 6:
        p.skeleton_retreats += 1
        escape.reason = "survival: gain spacing before skeleton death blast"
        return escape
    raise SkeletonSpacingBlocked("Wounded adjacent skeleton risks a fatal death blast; no usable spacing escape")


def rinse_ooze(p, state, enemies, distance, neighbors):
    pos, width = state["hero"]["cell"], state["map"]["width"]
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    burning = "burning" in buffs
    if not burning:
        p.burning_water_plan=None
    if burning and ('levitat' in buffs or 'flying' in buffs):
        frost=emergency_splash(p,state)
        if frost:return frost
        p.stop_no_safe_action('Burning while airborne: water cannot rinse; no known frost splash')
    if not ("ooze" in buffs or burning) or "levitat" in buffs or "flying" in buffs or p.tiles[pos]["terrain"] == 29:
        return None
    danger = set(state.get("danger_cells", []))
    awake = [e for e in enemies if not e.get("sleeping") and e["name"].lower() not in NON_MELEE]
    exposure = lambda c: sum(distance(c, e["cell"], width) <= reach(e) for e in awake)
    budget = exposure(pos) if burning else min(1, exposure(pos))
    previous = p.paths(state, {e["cell"] for e in enemies})
    goo = next((e for e in enemies if e["name"].lower() == "goo"), None)
    candidates = []
    critical_burning=burning and getattr(p,"pharmacophobia",False) \
        and state["hero"]["hp"]<=max(2,0.15*state["hero"]["max_hp"])
    rejected_burning_route=False
    for cell in previous:
        if p.tiles[cell]["terrain"] != 29 or p.loot.get(cell, {}).get("for_sale"):
            continue
        route = p.route(previous, cell)
        if len(route) > (25 if burning else 5):
            continue
        if critical_burning and len(route)>2:
            rejected_burning_route=True
            continue  # A distant water endpoint cannot extinguish this turn.
        forbidden=NO_DESTINATION-({5} if burning and not critical_burning else set())
        if any(c in danger or exposure(c) > budget or p.tiles[c].get("plant")
               or p.tiles[c]["terrain"] in forbidden or p.loot.get(c, {}).get("for_sale") for c in route[1:]):
            continue
        if goo and any(p.boss_strategies["goo"].landing_escape_distance(p, state, enemies, goo, c, distance, neighbors) > 2
                       for c in route[1:]):
            continue
        candidates.append(cell)
    if candidates:
        cell = min(candidates, key=lambda c: (exposure(p.route(previous,c)[1]),
                   max(exposure(n) for n in p.route(previous,c)[1:]),len(p.route(previous,c)),exposure(c)))
        plan=getattr(p,'burning_water_plan',None)
        if burning and plan and plan['cell'] in candidates:
            cell=plan['cell']
        if burning and len(p.route(previous,cell))>2:
            frost=emergency_splash(p,state)
            if frost:return frost
        if burning:
            if not plan:plan=p.burning_water_plan={'cell':cell,'steps':0}
            plan['cell']=cell
            if plan['steps']>=24:
                p.stop_no_safe_action('Burning: bounded water journey exhausted; no verified immediate rescue')
            plan['steps']+=1
        reason = "boss: goo rinse ooze safely" if any(e["name"].lower() == "goo" for e in enemies) \
             else "survival: wash ooze in nearby water"
        if burning:
            reason = "survival: extinguish burning in nearby water"
        return p.toward(state, cell, reason, previous, intent=Intent.RETREAT)
    if burning:
        frost=emergency_splash(p,state)
        if frost:return frost
    if rejected_burning_route:
        p.stop_no_safe_action("Critical burning: water requires another dry turn; no verified immediate extinguishing route")
    if burning:
        p.stop_no_safe_action('Burning: no verified water route or known frost splash; refusing loot/recharge fallthrough')
    return None


def emergency_splash(p,state):
    """Known identities only; preserve the existing frost rescue priority."""
    try:
        from .consumable_tactics import base_name
    except ImportError:
        from consumable_tactics import base_name
    frost=next((i for i in state['inventory'] if base_name(i)=='potion of frost'
                and 'THROW' in i.get('actions',[])),None)
    if frost:
        p.planner.report['emergency_extinguishing']={'method':'known frost self-splash',
            'caveat':'Cold and carried-potion risks accepted for active burning; no survival guarantee'}
        try:
            from .room_supplies import use as use_room_supply
        except ImportError:
            from room_supplies import use as use_room_supply
        return use_room_supply(p,frost,'THROW','survival: emergency known frost self-splash to extinguish burning',
                               kind='emergency',target=state['hero']['cell'])
    # Purity shatters with the normal splash, removing Burning and clearing
    # fire. Drinking only grants blob immunity; it is not this rescue.
    # Do not certify shattering into a well/pit, or press an active plate.
    tile=p.tiles.get(state['hero']['cell'],{})
    if tile.get('terrain') not in {1,2,3,5,6,9,14,15,19,20,29,30}:
        return None
    purity=next((i for i in state['inventory'] if base_name(i)=='potion of purity'
                 and i.get('identified') and 'THROW' in i.get('actions',[])),None)
    if purity:
        p.planner.report['emergency_extinguishing']={'method':'known purity self-splash',
            'caveat':'Rescue selection only; observe the splash and status removal before further progress'}
        try:
            from .room_supplies import use as use_room_supply
        except ImportError:
            from room_supplies import use as use_room_supply
        return use_room_supply(p,purity,'THROW','survival: emergency known purity self-splash to extinguish burning',
                               kind='emergency',target=state['hero']['cell'])


def close_zapper(p, state, enemies, distance):
    pos, width = state["hero"]["cell"], state["map"]["width"]
    targets = [e for e in enemies if not e.get("sleeping") and e["name"].lower() in ZAPPERS]
    if not targets:
        return None
    target = min(targets, key=lambda e: distance(pos, e["cell"], width))
    others = [e for e in enemies if not e.get("sleeping") and e is not target and e["name"].lower() not in NON_MELEE]
    if distance(pos, target["cell"], width) <= 1:
        attack = p.best_attack(state, target)
        if attack:
            attack.reason = "ranged: engage zapper at close range"
        return attack
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if state["hero"]["hp"] < 0.35 * state["hero"]["max_hp"] and "haste" not in buffs:
        attack = p.best_attack(state, target)
        if attack:
            attack.reason = "ranged: cast instead of slow gap closing at critical health"
            return attack
    if any(distance(pos, e["cell"], width) <= 1 for e in others):
        return None  # Resolve existing melee pressure rather than tunnel-vision.
    previous = p.paths(state, {e["cell"] for e in enemies})
    danger = set(state.get("danger_cells", []))
    candidates = []
    for cell in previous:
        if distance(cell, target["cell"], width) != 1 or p.tiles[cell]["terrain"] in NO_DESTINATION:
            continue
        route = p.route(previous, cell)
        if len(route) > 9 or any(c in danger or p.tiles[c].get("plant") or p.loot.get(c, {}).get("for_sale")
                                or p.tiles[c]["terrain"] in NO_DESTINATION
                                or any(distance(c, e["cell"], width) <= 1 for e in others) for c in route[1:]):
            continue
        candidates.append(cell)
    if candidates:
        cell = min(candidates, key=lambda c: len(p.route(previous, c)))
        return p.toward(state, cell, "ranged: close distance to stop ranged zaps", previous, intent=Intent.REPOSITION)
    attack = p.best_attack(state, target)
    if attack:
        attack.reason = "ranged: fire when safe gap closing is blocked"
    return attack
