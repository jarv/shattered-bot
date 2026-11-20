"""Room-driven potion hypotheses, public identification, and bounded water tests.

The floor-supply assumption is a search/guess prior, never an item identity or
permission to cross a hazard. All resulting protection must still be observed.
"""
from dataclasses import dataclass
from collections import deque

try:
    from .consumable_tactics import base_name, unknown_potion
    from .room_tactics import PROTECTION, remaining, plan_journey,sentry_geometry
    from .runestone_tactics import prepare_intuition
    from .special_rooms import fire_barrier
    from .potion_stash import protect_potions
    from .policy_decision import Intent
    from .policy_geometry import distance
except ImportError:
    from consumable_tactics import base_name, unknown_potion
    from room_tactics import PROTECTION, remaining, plan_journey,sentry_geometry
    from runestone_tactics import prepare_intuition
    from special_rooms import fire_barrier
    from potion_stash import protect_potions
    from policy_decision import Intent
    from policy_geometry import distance


@dataclass(frozen=True)
class Demand:
    kind: str
    potion: str
    cell: int


def demands(p, state, distance):
    width = state["map"]["width"]
    paths = p.paths(state)
    found = []
    for cell, actor in p.room_actors.items():
        name = actor["name"].lower()
        if name == "red sentry":
            found.append(Demand("sentry", "potion of haste", cell))
        elif "piranha" in name:
            found.append(Demand("pool", "potion of invisibility", cell))
    for cell, tile in p.tiles.items():
        effects = " ".join(tile.get("effects", [])).lower()
        if tile["terrain"]==0 and "distant well" in tile.get("name","").lower():
            found.append(Demand("fall","potion of levitation",cell))
        elif fire_barrier(tile):
            found.append(Demand("frost", "potion of frost", cell))
        elif tile["terrain"] in {13,27}:
            found.append(Demand("flame", "potion of liquid flame", cell))
        elif cell not in paths and tile["terrain"] in {0,18} and any(
                distance(cell, c, width) <= 3 for c in p.loot if c not in paths):
            found.append(Demand("flight", "potion of levitation", cell))
        elif "cloud of toxic gas" in effects and cell not in paths and any(
                distance(cell, c, width) <= 3 for c in p.loot if c not in paths):
            found.append(Demand("gas", "potion of purity", cell))
    # One hypothesis per visibly/rememberedly recognized puzzle kind; no room IDs.
    unique = {}
    pos = state["hero"]["cell"]
    for demand in sorted(found, key=lambda d: distance(pos,d.cell,width)):
        unique.setdefault(demand.kind, demand)
    return list(unique.values())


def frost_recovery_nearby(p,state,distance):
    """Fund extra recovery only near an observed puzzle, not across the floor.

    This does not relax the near-full-HP potion-test admission threshold.
    Ordinary bounded healing remains available while travelling/exploring.
    """
    if 'potion-supplies' in p.deferred_room_controllers:return False
    pos=state['hero']['cell'];width=state['map']['width']
    barriers=[c for c,t in p.tiles.items() if fire_barrier(t) and distance(pos,c,width)<=6]
    if not barriers:return False
    paths=p.paths(state)
    return any(any(len(p.route(paths,c))<=9 and 2<=distance(c,b,width)<=4
                   and p.tiles[c]['terrain'] in {1,3,9,11,14,19,20,29}
                   and not p.tiles[c].get('effects') for c in paths) for b in barriers)


def safe_test_bank(p, state, cell, distance, neighbors, allow_dry=False, pool_bank=False, flight_bank=False, sentry_bank=False):
    tile = p.tiles.get(cell, {})
    width, height = state["map"]["width"], state["map"]["height"]
    if cell in p.blocked or cell in p.room_blocked or cell in p.neutral_actor_cells \
            or tile.get("terrain") not in (({1,3,9,11,14,19,20,29}|({6} if flight_bank else set())) if allow_dry else {29}) \
            or not tile.get("visible") or tile.get("plant") or tile.get("trap") or tile.get("effects"):
        return False
    # Water is preferred; the user also allows nonflammable frost-barrier
    # staging with an intervening square. Exclude loot, NPCs and
    # flammable surroundings too, and retain two dry/gas-free escape directions.
    around = {cell, *neighbors(cell,width,height)}
    if pool_bank and (tile.get('terrain')==29 or p.recent_threats
                     or any(p.tiles.get(c,{}).get('terrain')==29 for c in around)):
        return False  # Unknown potion tests belong on dry ground, beyond every known water bank.
    allowed={1,3,4,6,9,11,12,14,19,20,29}|({0,5,18} if flight_bank else set())
    if any(c not in p.tiles or not p.tiles[c].get("visible") or p.tiles[c]["terrain"] not in allowed
           or p.tiles[c].get("plant") or p.tiles[c].get("effects") or c in p.loot for c in around):
        return False
    if any(distance(cell,o["cell"],width) <= 4 for o in state.get("objects", [])
            if not o.get("top_item") and o["cell"] not in p.loot
            and not (pool_bank and 'piranha' in o['name'].lower())
            and not (sentry_bank and o['name'].lower()=='red sentry')):
        return False
    return sum(p.walkable(n) and p.tiles[n]["terrain"] in {1,3,9,11,14,19,20,29}
                 for n in neighbors(cell,width,height)) >= 2


def stage_known_pool(p,state,demand,item,distance,neighbors):
    """Reserve known invisibility until a safe observed chest round trip exists."""
    if 'DRINK' not in item.get('actions',[]) or p.room_journey or remaining(state,PROTECTION['pool'][1])>0:return None
    paths=p.paths(state);choices=[]
    for bank in paths:
        if len(p.route(paths,bank))>10 or not safe_test_bank(p,state,bank,distance,neighbors,allow_dry=True,pool_bank=True):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='pool',plan_only=True)
        if journey:choices.append((len(p.route(paths,bank)),bank,journey))
    if not choices:return None
    _,bank,journey=min(choices,key=lambda c:(c[0],c[1]))
    p.planner.report['piranha_room']={'potion':'potion of invisibility','floor_supply':'Expected by the piranha-and-chest room rule',
        'bank':bank,'reward':journey.route[-1],'status':'Protected chest round trip planned; actual invisibility still required'}
    if bank!=state['hero']['cell']:
        return p.toward(state,bank,'room: stage known invisibility on dry ground outside piranha reach',paths,intent=Intent.REPOSITION)
    p.room_journey=journey
    p.room_attempts.add((state['depth'],'pool',journey.route[-1]))
    return p.use(item,'DRINK','room: activate known invisibility for planned piranha chest round trip; verify actual buff')


def refresh_barrier(p,state,demand,paths,distance):
    """Commit to one observation vantage; arrival without sight is a failed try."""
    pos=state['hero']['cell'];width=state['map']['width']
    plan=p.frost_view_plan
    if plan and plan['barrier']!=demand.cell:p.frost_view_plan=plan=None
    if plan:
        if pos==plan['view'] or plan['view'] not in paths or plan['steps']>=12:
            p.frost_view_attempts.add((demand.cell,plan['view']))
            p.frost_view_plan=plan=None
        else:
            plan['steps']+=1
            return p.toward(state,plan['view'],'room: finish committed fire-barrier observation vantage',paths,intent=Intent.EXPLORE)
    tried={view for barrier,view in p.frost_view_attempts if barrier==demand.cell}
    views=[c for c in paths if c!=pos and c not in tried
           and 2<=distance(c,demand.cell,width)<=4 and len(p.route(paths,c))<=13
           and distance(c,demand.cell,width)<distance(pos,demand.cell,width)
           and p.tiles[c]['terrain'] in {1,3,9,11,14,19,20,29}
           and not p.tiles[c].get('effects') and c not in p.loot
           and all(p.tiles[n]['terrain'] not in {7,8,10,21,22,31,37,38} and not p.tiles[n].get('plant')
                   for n in p.route(paths,c)[1:])
           and p.shot_clear(dict(state,hero=dict(state['hero'],cell=c)),demand.cell)]
    if len(tried)<3 and views:
        view=min(views,key=lambda c:(distance(c,demand.cell,width),len(p.route(paths,c))))
        p.frost_view_plan={'barrier':demand.cell,'view':view,'steps':1}
        return p.toward(state,view,'room: revisit observed fire barrier for safe frost staging',paths,intent=Intent.EXPLORE)
    p.defer_obligations(state,[{'kind':'unrefreshed fire barrier','cell':demand.cell}],
        'No bounded closer observation vantage; remembered fire remains hazardous, not cleared')
    return None


def revisit_flight_room(p,state,demand,distance):
    """Reach an observed approach before applying visible-only potion-test gates."""
    if demand.kind!='flight' or p.recent_threats or p.puzzle_revisit_steps['flight']>=48:return None
    hero=state['hero'];pos=hero['cell'];width=state['map']['width']
    try:
        from .policy_geometry import neighbors
    except ImportError:
        from policy_geometry import neighbors
    paths=p.paths(state);choices=[]
    for cell in paths:
        if cell in p.loot:continue
        route=p.route(paths,cell)
        if len(route)>41 or p.tiles[cell]['terrain'] not in {1,3,9,11,14,19,20,29}:continue
        if any(p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} or p.tiles[c].get('trap')
               or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c]) for c in route[1:]):continue
        # Choose an approach to the actual inaccessible reward, never the
        # closest arbitrary chasm/trap across a wall. Require a dry-run round
        # trip, then reobserve the bank before permitting any potion drink.
        staged=dict(state,hero=dict(hero,cell=cell))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='flight',plan_only=True)
        if not journey:continue
        around={cell,*neighbors(cell,width,state['map']['height'])}
        if any(c not in p.tiles or p.tiles[c]['terrain'] not in {0,1,3,4,5,6,9,11,12,14,18,19,20,29}
               or p.tiles[c].get('plant') or p.tiles[c].get('effects')
               or c in p.loot for c in around):continue
        if p.tiles[cell].get('trap') or sum(p.walkable(n) for n in neighbors(cell,width,state['map']['height']))<2:continue
        choices.append((cell!=p.puzzle_flight_bank,len(route),cell))
    if not choices:return None
    _,_,view=min(choices)
    p.puzzle_flight_bank=view
    if view==pos:return None
    p.puzzle_revisit_steps['flight']+=1
    p.planner.report['puzzle_revisit']={'kind':'flight','hazard':demand.cell,'approach':view,
        'status':'Return to observed approach, then reobserve and replan candidate test/round trip',
        'identity_inferred':False,'qualification':'No hazard entry or potion use admitted by this staging move'}
    return p.toward(state,view,'room: revisit levitation-room approach before deferring protected reward',paths,intent=Intent.REPOSITION)


def stage_known_flight(p,state,item,neighbors):
    if 'DRINK' not in item.get('actions',[]) or p.room_journey:return None
    paths=p.paths(state);choices=[]
    for bank in paths:
        if len(p.route(paths,bank))>41 or p.tiles[bank]['terrain'] not in {1,3,9,11,14,19,20,29}:continue
        route=p.route(paths,bank)
        if any(p.tiles[c].get('trap') or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
               or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} for c in route[1:]):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='flight',plan_only=True)
        if journey:choices.append((len(route),bank,journey))
    if not choices:return None
    _,bank,journey=min(choices,key=lambda c:(c[0],c[1]))
    if bank!=state['hero']['cell']:
        if p.puzzle_revisit_steps['known-flight']>=48:return None
        p.puzzle_revisit_steps['known-flight']+=1
        return p.toward(state,bank,'room: stage known levitation near verified reward round trip',paths,intent=Intent.REPOSITION)
    p.room_journey=journey;p.room_attempts.add((state['depth'],'flight',journey.route[-1]))
    return p.use(item,'DRINK','room: activate known levitation for planned reward round trip; verify actual buff')


def stage_sentry(p,state,neighbors,item=None):
    """Reach safe white flooring, not the carpet firing lane, before haste."""
    if p.recent_threats or p.puzzle_revisit_steps['sentry']>=48:return None
    region,delay=sentry_geometry(p,state)
    if not region or not delay:return None
    paths=p.paths(state);choices=[];pos=state['hero']['cell']
    for bank in region & paths.keys():
        tile=p.tiles[bank];route=p.route(paths,bank)
        if tile['terrain']==14 or len(route)>41 or tile.get('trap') or tile.get('plant') or tile.get('effects'):continue
        if item is None:
            # Unknown supplies must meet the same test-bank admission as
            # prepare_supplies. A protected reward route alone cannot justify
            # staging where the subsequent potion test will always decline.
            sentry=next(a for a in p.room_actors.values() if a['name'].lower()=='red sentry')
            if distance(bank,sentry['cell'],state['map']['width'])>5 or not safe_test_bank(
                    p,state,bank,distance,neighbors,allow_dry=True,sentry_bank=True):
                continue
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) for c in route[1:]):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='sentry',plan_only=True)
        if journey:choices.append((bank!=p.puzzle_sentry_bank,len(route),bank,journey))
    if not choices:return None
    _,_,bank,journey=min(choices,key=lambda c:c[:3]);p.puzzle_sentry_bank=bank
    if bank!=pos:
        p.puzzle_revisit_steps['sentry']+=1
        return p.toward(state,bank,'room: stage haste test on safe sentry entrance flooring before carpet',paths,intent=Intent.REPOSITION)
    if item:
        p.room_journey=journey
        return p.use(item,'DRINK','room: activate known haste for verified sentry round trip; check actual speed buff')
    return None


def prepare_supplies(p, state, enemies, distance, neighbors):
    if enemies or p.puzzle_probe or state.get("danger_cells") or "potion-supplies" in p.deferred_room_controllers:
        return None
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    pending=demands(p,state,distance)
    # A hungry hero cannot naturally recover to the near-full probe threshold.
    # Fund at most one nearby frost-room attempt from surplus known healing,
    # keeping one potion in reserve rather than lowering unknown-drink safety.
    frost_key=(state['depth'],'frost-probe-recovery')
    if getattr(p,'reserve_floor_puzzle_supplies',False) and 'hungry' in buffs and 'starving' not in buffs and not p.recent_threats \
            and .7*hero['max_hp']<=hero['hp']<.95*hero['max_hp'] and frost_key not in p.room_attempts \
            and not any(t in buffs for t in ('burn','poison','bleed','blind','vertigo','paral','root','magic immun')) \
            and any(d.kind=='frost' and distance(hero['cell'],d.cell,state['map']['width'])<=6 for d in pending) \
            and any(unknown_potion(i) and 'DRINK' in i.get('actions',[]) for i in state['inventory']):
        healing=[i for i in state['inventory'] if base_name(i)=='potion of healing' and 'DRINK' in i.get('actions',[])
                 and p.item_action_allowed(i,'DRINK')]
        if sum(i.get('quantity',1) for i in healing)>=2:
            paths=p.paths(state);width=state['map']['width']
            fires=[c for c,t in p.tiles.items() if t.get('visible') and fire_barrier(t)]
            banks=[c for c in paths if len(p.route(paths,c))<=12 and safe_test_bank(p,state,c,distance,neighbors,allow_dry=True)
                   and any((c%width==f%width or c//width==f//width) and distance(c,f,width)==2 for f in fires)]
            if banks:
                p.room_attempts.add(frost_key);p.puzzle_hungry_frost=True
                return p.use(healing[0],'DRINK','room: spend one surplus healing potion to fund near-full frost-barrier test; retain emergency reserve')
    meal_key=(state["depth"],"puzzle-meal")
    if "hungry" in buffs and "starving" not in buffs and hero["hp"]>=0.95*hero["max_hp"] \
            and not any(t in buffs for t in ("burning","poison","blind","vertigo","paral","root","magic immun")) \
            and (any(fire_barrier(t) for t in p.tiles.values()) or any(d.kind=='flight'
             and distance(hero['cell'],d.cell,state['map']['width'])<=6 for d in pending)
                 or any(d.kind=='sentry' and distance(hero['cell'],d.cell,state['map']['width'])<=8 for d in pending)) \
            and any((unknown_potion(i) or any(base_name(i)==d.potion for d in pending))
                    and "DRINK" in i.get("actions",[]) for i in state["inventory"]) \
            and meal_key not in p.room_attempts:
        food=p.food_items(state)
        if food:
            p.room_attempts.add(meal_key)
            return p.use(food[0],"EAT","room: eat one puzzle-backed meal before required potion staging/test")
    if getattr(p,'reserve_floor_puzzle_supplies',False) and 'hungry' in buffs and 'starving' not in buffs \
            and p.food_items(state) and hero['hp']>=.95*hero['max_hp'] \
            and not any(t in buffs for t in ('burn','poison','bleed','blind','vertigo','paral','root','levitat')):
        for demand in pending:
            staged=revisit_flight_room(p,state,demand,distance)
            if staged:return staged
    if hero["hp"] < 0.5*hero["max_hp"] or ('hungry' in buffs and not p.puzzle_hungry_frost) or any(t in buffs for t in (
            "starving", "burning", "poison", "blind", "vertigo", "paral", "root", "levitat", "magic immun")):
        return None
    inventory = state["inventory"]
    for demand in pending:
        if 'hungry' in buffs and demand.kind!='frost':continue
        known=next((i for i in inventory if base_name(i)==demand.potion),None)
        if known:
            if demand.kind=='pool' and getattr(p,'reserve_floor_puzzle_supplies',False):
                staged=stage_known_pool(p,state,demand,known,distance,neighbors)
                if staged:return staged
            if demand.kind=='flight' and getattr(p,'reserve_floor_puzzle_supplies',False):
                staged=stage_known_flight(p,state,known,neighbors)
                if staged:return staged
            if demand.kind=='sentry' and getattr(p,'reserve_floor_puzzle_supplies',False):
                staged=stage_sentry(p,state,neighbors,known)
                if staged:return staged
            continue
        if demand.kind in PROTECTION and remaining(state,PROTECTION[demand.kind][1]) > 0:
            continue
        candidates = [i for i in inventory if unknown_potion(i) and "DRINK" in i.get("actions", [])
                      and (state["depth"],base_name(i)) not in p.puzzle_drinks]
        if not candidates:
            # The potion is assumed available somewhere, not assumed already
            # carried or at a generated coordinate. Collect only observed loot.
            paths = p.paths(state)
            loot = [c for c,o in p.loot.items() if c in paths and not o.get("for_sale")
                    and (unknown_potion(o.get("top_item",o)) or base_name(o.get('top_item',o))==demand.potion)
                    and len(p.route(paths,c)) <= 12]
            if loot:
                return p.toward(state,min(loot,key=lambda c:len(p.route(paths,c))),
                                "room: seek observed floor potion for unresolved puzzle",paths,intent=Intent.LOOT)
            continue
        candidate = max(candidates,key=lambda i: (
            state["depth"] in p.consumable_sources.get(base_name(i),set()),i.get("quantity",1)))
        identify = next((i for i in inventory if base_name(i)=="scroll of identify" and "READ" in i.get("actions",[])),None)
        key = (state["depth"],demand.kind,base_name(candidate))
        if identify and key not in p.puzzle_identify_attempts:
            p.puzzle_identify_attempts.add(key)
            p.puzzle_identify_plan = {"target":candidate["name"].lower(),"steps":0,"bags":set()}
            return p.use(identify,"READ",f"room: identify potion for {demand.kind} puzzle before risking use")
        guess = prepare_intuition(p,state,guess=demand.potion,candidate=candidate) if key not in p.puzzle_guesses else None
        if guess:
            p.puzzle_guesses.add(key)
            return guess
        if hero["hp"]<0.95*hero["max_hp"]:
            continue  # Safe identification is not permission for a risky drink.
        if demand.kind=="frost":
            if sum(d==state["depth"] for d,_ in p.puzzle_drinks)>=2:
                continue
            width=state["map"]["width"]
            barriers=[c for c,t in p.tiles.items() if t.get("visible") and fire_barrier(t)]
            paths=p.paths(state)
            banks=[c for c in paths if len(p.route(paths,c))<=12
                   and safe_test_bank(p,state,c,distance,neighbors,allow_dry=True)
                   and any((c%width==b%width or c//width==b//width)
                           and distance(c,b,width)==2 for b in barriers)]
            if not banks:
                if not barriers:
                    # Healing/exploration may have taken us away from the
                    # observed puzzle. Refresh it before applying visible-only
                    # staging checks; remembered fire is not proof it cleared.
                    refresh=refresh_barrier(p,state,demand,paths,distance)
                    if refresh:return refresh
                continue
            bank=min(banks,key=lambda c:(p.tiles[c]["terrain"]!=29,len(p.route(paths,c))))
            if bank!=hero["cell"]:
                return p.toward(state,bank,"room: stage frost hypothesis with one square before visible fire barrier",paths,intent=Intent.EXPLORE)
            stash=protect_potions(p,state,candidate,distance,neighbors,safe_test_bank)
            if stash:
                return stash
            if p.potion_stash:
                p.potion_stash["phase"]="retrieve"
            p.puzzle_drinks.add((state["depth"],base_name(candidate)))
            p.puzzle_probe={"depth":state["depth"],"kind":"frost","turns":0}
            try:
                from .barrier_followup import begin
            except ImportError:
                from barrier_followup import begin
            begin(p,state,min(barriers,key=lambda c:distance(hero['cell'],c,width)),neighbors)
            p.potion_probe_permit=(candidate["id"],candidate["name"])
            try:
                return p.use(candidate,"DRINK","room: test unconfirmed frost beside barrier with one intervening square; verify fire removal")
            finally:
                p.potion_probe_permit=None
        if demand.kind=='flame' and getattr(p,'reserve_floor_puzzle_supplies',False):
            try:
                from .wooden_barrier import prepare as prepare_wood
            except ImportError:
                from wooden_barrier import prepare as prepare_wood
            action=prepare_wood(p,state,demand,candidate,safe_test_bank)
            if action:return action
        # Known flame is still preferred as a THROW. The unknown-drink fallback
        # above is explicitly staged beside wood with an immediate water exit.
        if demand.kind not in PROTECTION:
            continue
        if sum(d == state["depth"] for d,_ in p.puzzle_drinks) >= 2:
            continue
        if (state["depth"],base_name(candidate)) in p.puzzle_drinks:
            continue
        paths = p.paths(state)
        banks = [c for c in paths if len(p.route(paths,c)) <= 7
                  and (demand.kind=='flight' or distance(c,demand.cell,state["map"]["width"]) <= 5)
                  and (safe_test_bank(p,state,c,distance,neighbors,allow_dry=True,pool_bank=True)
                        if demand.kind=='pool' and getattr(p,'reserve_floor_puzzle_supplies',False)
                        else safe_test_bank(p,state,c,distance,neighbors,allow_dry=demand.kind in {'flight','sentry'}
                                            and getattr(p,'reserve_floor_puzzle_supplies',False),
                                            flight_bank=demand.kind=='flight' and getattr(p,'reserve_floor_puzzle_supplies',False),
                                            sentry_bank=demand.kind=='sentry' and getattr(p,'reserve_floor_puzzle_supplies',False)))]
        # A nearby hazard is not proof of a usable room. Keep the floor's
        # candidate until the reward, round trip and interaction budget are
        # actually admitted from the staging cell. Do not spend a successful
        # levitation/invisibility/haste/purity effect on subsequent exploration.
        journeys={}
        if getattr(p,'reserve_floor_puzzle_supplies',False):
            for bank in banks:
                staged=dict(state,hero=dict(hero,cell=bank))
                journey=plan_journey(p,staged,[],neighbors,probe_kind=demand.kind,plan_only=True)
                if journey:journeys[bank]=journey
            banks=[bank for bank in banks if bank in journeys]
        if not banks:
            if getattr(p,'reserve_floor_puzzle_supplies',False):
                p.planner.report['potion_reservation']={'reason':'Puzzle candidate retained: no verified protected reward round trip',
                    'puzzle':demand.kind,'identity_inferred':False}
                staged=revisit_flight_room(p,state,demand,distance)
                if staged:return staged
                if demand.kind=='sentry':
                    staged=stage_sentry(p,state,neighbors)
                    if staged:return staged
            continue
        bank = min(banks,key=lambda c:len(p.route(paths,c)))
        if bank != hero["cell"]:
            return p.toward(state,bank,"room: stage unconfirmed potion test on safe water",paths)
        if demand.kind=='flight' and bank in journeys:
            closed=next((c for c in journeys[bank].route[1:] if p.tiles[c]['terrain']==5),None)
            if closed is not None:
                if distance(bank,closed,state['map']['width'])==1 and p.tiles[closed].get('visible'):
                    return p.cell(closed,'room: open observed flight-room entrance before testing protection')
                continue  # Do not drink until all door opening fits outside the protection budget.
        stash=protect_potions(p,state,candidate,distance,neighbors,safe_test_bank)
        if stash:
            return stash
        if p.potion_stash:
            p.potion_stash["phase"]="retrieve"
        p.puzzle_drinks.add((state["depth"],base_name(candidate)))
        if journeys:
            journey=journeys[bank]
            p.room_journey=journey
        p.puzzle_probe = {"depth":state["depth"],"kind":demand.kind,"turns":0}
        p.potion_probe_permit = (candidate["id"],candidate["name"])
        try:
            return p.use(candidate,"DRINK",f"room: test unconfirmed {demand.potion} hypothesis on water; verify actual effect")
        finally:
            p.potion_probe_permit = None
    return None


def identify_menu(p,state):
    plan = p.puzzle_identify_plan
    plan["steps"] += 1
    buttons = state["ui"]["buttons"]
    if plan["steps"] <= 6:
        target = next((b for b in buttons if b["label"].lower()==plan["target"]),None)
        if target:
            p.puzzle_identify_plan = None
            return p.decision({"type":"button","id":target["id"]},"room: identify explicitly selected puzzle-potion candidate")
        bag = next((b for b in buttons if b["label"].lower() in {"backpack","potion bandolier"} and b["label"] not in plan["bags"]),None)
        if bag:
            plan["bags"].add(bag["label"])
            return p.decision({"type":"button","id":bag["id"]},"room: find candidate in observed potion bag")
    p.puzzle_identify_plan = None
    return p.decision({"type":"back"},"room: cancel unavailable potion identification")


def recover_probe(p,state,enemies,distance,neighbors):
    try:
        from .barrier_followup import observe
    except ImportError:
        from barrier_followup import observe
    observe(p)  # Capture verified clearing while visible, before cold recovery moves away.
    plan = p.puzzle_probe
    if not plan or state.get("status") != "ready" or state.get("modal"):
        return None
    if plan["depth"] != state["depth"]:
        p.puzzle_probe = None
        return None
    plan["turns"] += 1
    hero = state["hero"]
    pos,width,height = hero["cell"],state["map"]["width"],state["map"]["height"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs",[]))
    effects = p.tiles[pos].get("effects",[])
    impaired = any(t in buffs for t in ("burning","poison","paral","frozen","chill","blind","vertigo","root","drowsy","sleep"))
    if enemies or state.get("danger_cells"):
        p.puzzle_probe = None
        return None  # Ordinary emergency combat has priority over experiments.
    if hero["hp"] < 0.5*hero["max_hp"] or plan["turns"] > 24:
        p.stop_obligation("potion-probe","Potion test complication exceeded its observed health/time recovery budget")
    if effects and not any(t in buffs for t in ("paral","frozen","vertigo","root")):
        if all("unnaturally frigid" in e.lower() for e in effects):
            # Normal paths reject every cold-cloud tile, so they cannot find a
            # route out of a multi-tile frost cloud. Traverse only observed cold
            # air, never another hazard, instead of waiting through slowed turns.
            queue=deque([[pos]])
            seen={pos}
            while queue:
                route=queue.popleft()
                cell=route[-1]
                if cell!=pos and not p.tiles[cell].get("effects"):
                    return p.cell(route[1],"room: leave observed cold cloud before waiting for chill to clear",intent=Intent.RETREAT)
                if len(route)>=5:continue
                for n in neighbors(cell,width,height):
                    tile=p.tiles.get(n,{})
                    cold=tile.get("effects") and all("unnaturally frigid" in e.lower() for e in tile["effects"])
                    if n not in seen and tile.get("visible") and tile.get("terrain") in {1,3,9,11,14,19,20,29} \
                            and not tile.get("plant") and not tile.get("trap") and n not in p.loot \
                            and n not in p.neutral_actor_cells and n not in p.blocked \
                            and (cold or not tile.get("effects") and n not in p.room_blocked):
                        seen.add(n)
                        queue.append(route+[n])
        paths = p.paths(state)
        choices = [c for c in paths if c!=pos and len(p.route(paths,c)) <= 4
                   and p.tiles[c]["terrain"] in {1,3,9,11,14,19,20,29} and not p.tiles[c].get("plant")
                   and not p.tiles[c].get("effects") and c not in p.loot]
        if choices:
            target = min(choices,key=lambda c:(p.tiles[c]["terrain"]!=29,len(p.route(paths,c))))
            return p.toward(state,target,"room: leave observed potion-test cloud before another experiment",paths,intent=Intent.RETREAT)
    if not effects and not impaired:
        # Success or failure does not manufacture an identity. Room execution
        # separately checks the actual buff and rendered remaining duration.
        p.puzzle_probe = None
        return None
    if effects and not all("paralytic gas" in e.lower() or "unnaturally frigid" in e.lower() for e in effects):
        p.stop_obligation("potion-probe","Potion test left an unsafe cloud without a verified escape")
    return p.decision({"type":"wait"},"room: bounded recovery from actual observed potion-test effects")
