"""Food preparation, beneficial wells, and enchantments from public observations."""

try:
    from .policy_decision import Intent
    from .combat_items import known_cursed, stats, physical_score
except ImportError:
    from policy_decision import Intent
    from combat_items import known_cursed, stats, physical_score


def healing_water(tile):
    return any("power of health radiates" in e.lower() for e in tile.get("effects", []))


def recheck_hazards(p, state, previous, distance):
    p.hazard_recheck_pending=None
    if p.hazard_recheck_steps >= 60:
        return None
    pos, width = state["hero"]["cell"], state["map"]["width"]
    reserved=set()
    if getattr(p,'reserve_floor_puzzle_supplies',False):
        try:
            from .puzzle_supplies import demands
            from .policy_geometry import neighbors
        except ImportError:
            from puzzle_supplies import demands
            from policy_geometry import neighbors
        # Recognize the potion-gated gas/reward geometry, not a generated room.
        # Ordinary isolated trap gas can still use the bounded expiry recheck.
        queue=[d.cell for d in demands(p,state,distance) if d.kind=='gas']
        while queue:
            cell=queue.pop()
            if cell in reserved:continue
            if not any('cloud of toxic gas' in effect.lower() for effect in p.tiles.get(cell,{}).get('effects',[])):continue
            reserved.add(cell)
            queue.extend(n for n in neighbors(cell,width,state['map']['height']) if n not in reserved)
        if reserved:
            p.planner.report['potion_reservation']={'puzzle':'gas','potion':'potion of purity',
                'reason':'Potion-gated gas reward: conserve/seek observed floor supplies, not expiry waiting',
                'identity_inferred':False}
    stale = [c for c, t in p.tiles.items() if t.get("effects") and not t.get("visible") and c not in reserved]
    choices = []
    for cell in stale:
        for vantage in previous:
            if vantage == pos or p.tiles[vantage]["terrain"] in {5,6,7,8,22,37}:
                continue
            route=p.route(previous,vantage)
            if len(route)<2:continue
            # A closed doorway currently free of gas is not a safe observation
            # bank: opening/entering it can expose the gas on the other side.
            if any(p.tiles[n]['terrain']==5 and distance(n,cell,width)<=2 for n in route[1:]):
                p.planner.report['hazard_recheck']={'status':'closed doorway observation deferred','hazard':cell,'vantage':vantage}
                continue
            if any(n in p.room_blocked or p.effects_block_movement(p.tiles[n]) or p.tiles[n].get('plant')
                   or p.tiles[n].get('trap') and p.tiles[n]['terrain']!=19 for n in route[1:]):continue
            if p.hazard_recheck_edges[(cell,pos,route[1])]>=2:
                p.planner.report['hazard_recheck']={'status':'repeated observation edge deferred','hazard':cell,
                    'from':pos,'to':route[1],'accepted_edge_limit':2}
                continue
            if distance(vantage, cell, width) <= 2 \
                    and p.shot_clear(dict(state, hero=dict(state["hero"], cell=vantage)), cell):
                choices.append((len(route),distance(vantage,cell,width),vantage,cell,route[1]))
    if choices:
        _,_,vantage,hazard,step=min(choices)
        p.hazard_recheck_steps += 1
        p.hazard_recheck_pending={'depth':state['depth'],'branch':state.get('branch',0),
            'hazard':hazard,'from':pos,'to':step,'vantage':vantage}
        p.planner.report['hazard_recheck']={'status':'bounded safe-ground observation route',**p.hazard_recheck_pending}
        return p.toward(state,vantage,"explore: recheck remembered hazard from safe ground",previous,intent=Intent.EXPLORE)
    visible_gas = [c for c, t in p.tiles.items() if t.get("visible") and t.get("effects")
                   and c not in reserved
                   and all("gas" in e.lower() for e in t["effects"])
                   and distance(pos, c, width) <= 3]
    if visible_gas and not p.tiles[pos].get("effects") and p.hazard_recheck_waits < 16:
        p.hazard_recheck_steps += 1
        p.hazard_recheck_waits += 1
        return p.decision({"type": "wait"}, "obstacle: observe gas dissipating from safe ground")
    return None


def observe_hazard_recheck(p,before,decision,after):
    """Bound actual re-entries, never proposals, rejected inputs or guessed IDs."""
    plan=p.hazard_recheck_pending
    p.hazard_recheck_pending=None
    if not plan or decision.intent!=Intent.EXPLORE or decision.action.get('type')!='cell':return
    if (before.get('depth'),before.get('branch',0),before['hero']['cell'],decision.action.get('cell')) != \
            (plan['depth'],plan['branch'],plan['from'],plan['to']):return
    if after.get('depth')!=plan['depth'] or after.get('branch',0)!=plan['branch'] \
            or after['hero']['cell']!=plan['to'] or plan['to']==plan['from']:return
    key=(plan['hazard'],plan['from'],plan['to'])
    p.hazard_recheck_edges[key]+=1
    return dict(plan,accepted_edge_traversals=p.hazard_recheck_edges[key],
                evidence='Confirmed hero movement for a remembered public hazard; no inferred clearance')


def clear_blocking_plant(p, state, previous, distance):
    # These plants affect a character on their cell, not the thrower. Fire,
    # freezing, and teleportation plants need separate area/escape planning.
    harmless_to_thrower = {"sorrowmoss", "blindweed", "stormvine"}
    food = p.food_items(state)
    item = next((i for i in food if "THROW" in i.get("actions", [])), None)
    if not item:
        item = next((i for i in state["inventory"] if i["name"].lower() == "magical catalyst"
                     and "THROW" in i.get("actions", [])), None)
    if not item:
        return None
    width = state["map"]["width"]
    for cell, tile in p.tiles.items():
        if tile.get("plant", "").lower() not in harmless_to_thrower or cell in p.room_blocked \
                or cell in p.loot or tile.get("effects"):
            continue
        after = p.paths(state, ignored_plants={cell})
        if len(after) <= len(previous) + 1:
            continue
        choices = [c for c in previous if p.tiles[c]["terrain"] not in {7, 8, 22, 37}
                   and 1 <= distance(c, cell, width) <= 3
                   and p.shot_clear(dict(state, hero=dict(state["hero"], cell=c)), cell)]
        if not choices:
            continue
        vantage = min(choices, key=lambda c: len(p.route(previous, c)))
        if vantage != state["hero"]["cell"]:
            return p.toward(state, vantage, "obstacle: approach blocking plant safely", previous)
        return p.use(item, "THROW", "obstacle: trigger blocking plant with retrievable item", target=cell)
    return None


def choose_well(p, state, enemies, distance, neighbors):
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .well_cleansing import choose
        except ImportError:
            from well_cleansing import choose
        action=choose(p,state,enemies)
        if action:return action
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    cursed = any(i.get("equipped") and known_cursed(i) for i in state["inventory"])
    urgent = cursed or hero["hp"] < 0.55 * hero["max_hp"] or "starving" in buffs
    if getattr(p, "pharmacophobia", False) and "hungry" in buffs and not p.food_items(state) \
            and hero["hp"] < 0.85*hero["max_hp"]:
        urgent = True
    if not urgent:
        return None
    active = [e for e in enemies if not e.get("sleeping")]
    previous = p.paths(state, {e["cell"] for e in enemies})
    width, height = state["map"]["width"], state["map"]["height"]
    candidates = []
    for cell, tile in p.tiles.items():
        if not healing_water(tile) or cell in p.neutral_actor_cells:
            continue
        for bank in neighbors(cell, width, height):
            if bank not in previous:
                continue
            route = p.route(previous, bank)[1:] + [cell]
            if len(route) > (4 if active else 16):
                continue
            if any(c in state.get("danger_cells", []) or p.tiles[c].get("plant")
                   or (p.tiles[c].get("effects") and not healing_water(p.tiles[c]))
                   or any(distance(c, e["cell"], width) <= 1 for e in active) for c in route):
                continue
            candidates.append(route)
    if candidates:
        route = min(candidates, key=len)
        if len(route) == 1 and not active and not cursed and hero["hp"] >= 0.55*hero["max_hp"] \
                and p.tiles[route[0]].get("visible"):
            # Only equip while already beside a verified cleansing well. No
            # speculative travel while curse-bound, no overweight items, no
            # artifact side effects, and no setup before urgent low-HP healing.
            strength = hero.get("strength", 0)
            upgrades = []
            for item in state["inventory"]:
                value = stats(item)
                if not value or value[0] not in {"armor", "melee"} or value[2] > strength \
                        or item.get("equipped") or "EQUIP" not in item.get("actions", []):
                    continue
                current = next((i for i in state["inventory"] if i.get("equipped") and stats(i) and stats(i)[0] == value[0]), None)
                baseline = physical_score(current, strength) if current else 0
                score = physical_score(dict(item, known_cursed=False), strength)  # Evaluate after the observed well cleanses it.
                # Do not replace the Mage's staff to test a marginal weapon.
                if value[0] == "melee" and current and "IMBUE" in current.get("actions", []):
                    continue
                if score >= max(baseline*1.25, baseline+1):
                    upgrades.append((score-baseline, item))
            if upgrades:
                item = max(upgrades, key=lambda pair: pair[0])[1]
                return p.use(item,"EQUIP","well: equip useful strength-safe upgrade beside verified curse-cleansing water")
        return p.cell(route[0], "well: heal, feed, and cleanse equipped curses")
    return None


def choose_meat(p, state, enemies, distance, neighbors):
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .hungry_cooking import choose
        except ImportError:
            from hungry_cooking import choose
        return choose(p,state,enemies)
    return prepare_meat(p,state,enemies,distance,neighbors)


def prepare_meat(p, state, enemies, distance, neighbors):
    if enemies or state.get("danger_cells"):
        return None
    meat = next((i for i in state["inventory"] if "mystery meat" in i["name"].lower()
                 and "THROW" in i.get("actions", [])), None)
    if not meat:
        p.meat_plan = None
        return None
    pos, width = state["hero"]["cell"], state["map"]["width"]
    previous = p.paths(state)
    if p.meat_plan:
        plan = p.meat_plan
        cell, kind = plan["cell"], plan["kind"]
        p.meat_plan = None
        if kind in p.tiles.get(cell, {}).get("plant", "").lower() and p.shot_clear(state, cell):
            reason = "food: freeze raw meat with prepared icecap" if kind == "icecap" else "food: grill raw meat with prepared firebloom"
            return p.use(meat, "THROW", reason, target=cell)
    try:
        from .environment_tactics import cold_trigger_safe
    except ImportError:
        from environment_tactics import cold_trigger_safe
    cold_traps=[c for c in p.tiles if (state['depth'],c) not in p.trap_attempts
                and any(n in previous for n in neighbors(c,width,state['map']['height']))
                and cold_trigger_safe(p,state,c,distance,neighbors)]
    if cold_traps:
        cell=min(cold_traps,key=lambda c:distance(pos,c,width))
        p.trap_attempts.add((state['depth'],cell))
        return p.use(meat,'THROW','food: freeze raw meat with a revealed chilling trap from outside its radius',target=cell)
    for cell, tile in sorted(p.tiles.items(),key=lambda pair:not any(
            'unnaturally frigid' in e.lower() for e in pair[1].get('effects',[]))):
        effects = " ".join(tile.get("effects", [])).lower()
        if 1 < distance(pos, cell, width) <= 3 and p.shot_clear(state, cell) \
                and tile.get("terrain") in {1, 2, 3, 9, 11, 14, 19, 20} \
                and ("a fire is raging here" in effects or "unnaturally frigid" in effects) \
                and not tile.get("trap") and cell not in p.loot:
            return p.use(meat, "THROW", "food: cook raw meat in observed fire or cold", target=cell)
    if getattr(p, "barren_land", False):
        return None  # Existing fire/cold still cooks meat; thrown seeds cannot sprout.
    for kind in ("icecap", "firebloom"):
        seed = next((i for i in state["inventory"] if f"seed of {kind}" in i["name"].lower()
                      and "THROW" in i.get("actions", []) and p.item_action_allowed(i,"THROW")), None)
        if not seed:
            continue
        for cell in previous:
            tile = p.tiles[cell]
            if kind == "firebloom" and (tile["terrain"] in {2, 3, 15, 30}
                    or any(n not in p.tiles or p.tiles[n]["terrain"] in {2, 3, 5, 13, 15, 30}
                           or n in p.loot for n in neighbors(cell, width, state["map"]["height"]))):
                continue  # No uncontrolled spread, burned loot, or blind fire setup.
            if distance(pos, cell, width) == 2 and len(p.route(previous, cell)) <= 4 \
                    and tile["terrain"] in {1, 2, 3, 11, 14, 20} and not tile.get("plant") \
                    and not tile.get("trap") and not tile.get("effects") and cell not in p.loot \
                    and p.shot_clear(state, cell):
                if getattr(p,'unit_strategies_enabled',False):
                    area={cell,*neighbors(cell,width,state['map']['height'])}
                    if not tile.get('visible') or any(c not in p.tiles or not p.tiles[c].get('visible')
                            or c in p.loot or p.tiles[c].get('plant') or p.tiles[c].get('trap')
                            or p.tiles[c].get('effects') for c in area):continue
                    if any(o['cell'] in area for o in state.get('objects',[]) if not o.get('top_item')):continue
                p.meat_plan = {"cell": cell, "kind": kind}
                reason = "food: prepare icecap for safe meat freezing" if kind == "icecap" else "food: prepare isolated firebloom for meat grilling"
                return p.use(seed, "THROW", reason, target=cell)
    return None


def choose_enchantment(p, state):
    for item in state["inventory"]:
        value = stats(item)
        if not item.get("equipped") or not value or known_cursed(item) \
                or not (item.get("curse_known") or item.get("identified")):
            continue
        description = item.get("description", "").lower()
        if "inscribed with" in description or "enchanted with" in description:
            continue
        source = None
        if value[0] == "armor" and (value[2] >= 12 or getattr(p, "faith_is_my_armor", False)):
            source = next((i for i in state["inventory"] if "arcane stylus" in i["name"].lower()
                           and "INSCRIBE" in i.get("actions", [])), None)
        if not source and value[0] == "melee":
            source = next((i for i in state["inventory"] if "stone of enchantment" in i["name"].lower()
                           and "USE" in i.get("actions", [])), None)
            if not source:
                source = next((i for i in state["inventory"] if "scroll of enchantment" in i["name"].lower()
                               and "READ" in i.get("actions", [])), None)
        if source:
            p.enchant_target = item["name"]
            p.menu_plan = "enchant-select"
            p.enchant_choice = "scroll of enchantment" in source["name"].lower()
            return p.use(source, "READ" if p.enchant_choice else "INSCRIBE" if value[0] == "armor" else "USE",
                         "prepare: enchant useful equipped gear")
    return None


def enchantment_menu(p, state):
    if p.menu_plan == "enchant-choice":
        ranking = ("vampiric", "grim", "blocking", "chilling", "kinetic", "shocking", "lucky",
                   "elastic", "blooming", "projecting", "corrupting", "unstable", "blazing")
        for name in ranking:
            button = next((b for b in state["ui"]["buttons"] if name in b["label"].lower()), None)
            if button:
                p.menu_plan = None
                return p.decision({"type": "button", "id": button["id"]}, "enchant: choose visible beneficial enchantment")
    button = next((b for b in state["ui"]["buttons"] if b["label"].lower() == (p.enchant_target or "").lower()), None)
    if button:
        p.menu_plan = "enchant-choice" if getattr(p, "enchant_choice", False) else None
        p.enchant_target = None
        return p.decision({"type": "button", "id": button["id"]}, "enchant: select equipped target")
    p.menu_plan = None
    p.enchant_target = None
    return p.decision({"type": "back"}, "enchant: cancel unavailable target")
