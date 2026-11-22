"""Room-driven potion hypotheses, public identification, and bounded water tests.

The floor-supply assumption is a search/guess prior, never an item identity or
permission to cross a hazard. All resulting protection must still be observed.
"""
from dataclasses import dataclass
from collections import deque

try:
    from .consumable_tactics import base_name, unknown_potion
    from .room_tactics import GROUND, PROTECTION, remaining, plan_journey,sentry_geometry
    from .runestone_tactics import prepare_intuition
    from .special_rooms import fire_barrier
    from .potion_stash import protect_potions, can_protect_potions, bandolier_protected
    from .policy_decision import Intent
    from .policy_geometry import distance
    from .room_supplies import use as use_room_supply
except ImportError:
    from consumable_tactics import base_name, unknown_potion
    from room_tactics import GROUND, PROTECTION, remaining, plan_journey,sentry_geometry
    from runestone_tactics import prepare_intuition
    from special_rooms import fire_barrier
    from potion_stash import protect_potions, can_protect_potions, bandolier_protected
    from policy_decision import Intent
    from policy_geometry import distance
    from room_supplies import use as use_room_supply


@dataclass(frozen=True)
class Demand:
    kind: str
    potion: str
    cell: int


MAX_ROOM_POTION_TESTS=12  # Distinct unknown types, at most once each per floor.


def nearby_flight_reward(p, cell, reward, width, height, distance):
    """Reject proximity through an observed separator, not missing geometry.

    This is local room recognition only, never movement admission. Unknown
    cells remain possible connections so incomplete sight cannot clear a
    supply obligation. Walls and non-flight locks cannot link a nearby reward
    to the hazard merely because they are close in coordinate space.
    """
    if distance(cell, reward, width) > 3:
        return False
    try:
        from .policy_geometry import neighbors
        from .room_tactics import GROUND
    except ImportError:
        from policy_geometry import neighbors
        from room_tactics import GROUND
    queue, seen = deque([cell]), {cell}
    while queue:
        current = queue.popleft()
        if current == reward:
            return True
        for n in neighbors(current, width, height):
            if n in seen or distance(cell, n, width) > 3:
                continue
            tile = p.tiles.get(n, {})
            if tile.get("observed") and tile.get("terrain") not in GROUND | {0, 5, 18}:
                continue
            seen.add(n)
            queue.append(n)
    return False


def demands(p, state, distance, *, include_deferred=False):
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
                nearby_flight_reward(p, cell, c, width, state["map"]["height"], distance)
                for c in p.loot if c not in paths):
            found.append(Demand("flight", "potion of levitation", cell))
        elif "cloud of toxic gas" in effects and cell not in paths and any(
                distance(cell, c, width) <= 3 for c in p.loot if c not in paths):
            found.append(Demand("gas", "potion of purity", cell))
    for cell,room in p.piranha_rooms.items():
        if not room['collected']:
            found.append(Demand('pool','potion of invisibility',cell))
    # One hypothesis per visibly/rememberedly recognized puzzle kind; no room IDs.
    unique = {}
    pos = state["hero"]["cell"]
    for demand in sorted(found, key=lambda d: distance(pos,d.cell,width)):
        unique.setdefault(demand.kind, demand)
    result=list(unique.values())
    if not include_deferred:
        try:
            from .room_supplies import exhausted
        except ImportError:
            from room_supplies import exhausted
        result=[d for d in result if not exhausted(p,state,d.kind)]
    return result


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
    allowed={1,3,4,6,9,11,12,14,19,20,29}|({0,5,18} if flight_bank else {5} if pool_bank else set())
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


def known_pool_bank(p,state,bank,neighbors, *, arrival=False):
    """Known invisibility needs safe activation/retreat, not unknown-frost geometry."""
    width,height=state['map']['width'],state['map']['height']
    tile=p.tiles.get(bank,{})
    if not p.walkable(bank) or bank in p.loot or tile.get('terrain') not in {1,3,5,6,9,11,14,19,20,29} \
            or arrival and not tile.get('visible'):
        return False
    around={bank,*neighbors(bank,width,height)}
    if any(c not in p.tiles or not p.tiles[c].get('observed',False)
           or p.tiles[c].get('trap') or p.tiles[c].get('plant')
           or p.effects_block_movement(p.tiles[c]) for c in around):
        return False
    # One ordinary exterior retreat suffices for a known non-damaging potion.
    # Habitat and its shore remain excluded by walkable; never count fish water.
    return any(p.walkable(n) and n not in p.loot
               and p.tiles[n]['terrain'] in {1,3,6,9,11,14,19,20,29}
               and any(c!=bank and p.walkable(c) and c not in p.loot
                       and not p.tiles[c].get('plant') and not p.effects_block_movement(p.tiles[c])
                       for c in neighbors(n,width,height))
               for n in neighbors(bank,width,height))


def stage_known_pool(p,state,demand,item,distance,neighbors):
    """Reserve known invisibility until a safe observed chest round trip exists."""
    if 'DRINK' not in item.get('actions',[]) or p.room_journey or remaining(state,PROTECTION['pool'][1])>0:return None
    paths=p.paths(state);choices=[]
    try:
        from .piranha_tactics import staging_bank
    except ImportError:
        from piranha_tactics import staging_bank
    for bank in paths:
        route=p.route(paths,bank)
        if len(route)>41 or p.puzzle_revisit_steps['pool']>=48:continue
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) for c in route[1:]):continue
        verified=safe_test_bank(p,state,bank,distance,neighbors,allow_dry=True,pool_bank=True)
        # Unknown-drink banks exclude all water because frost and other effects
        # are not known. Identified invisibility needs no such experiment.
        # Ordinary approach water is usable only outside the remembered habitat,
        # with observed, hazard-free surroundings and a visible arrival recheck.
        width,height=state['map']['width'],state['map']['height']
        around={bank,*neighbors(bank,width,height)}
        known_water=item.get('identified') and p.tiles[bank]['terrain']==29 \
            and p.walkable(bank) and bank not in p.loot \
            and (bank!=state['hero']['cell'] or p.tiles[bank].get('visible')) \
            and all(c in p.tiles and p.tiles[c].get('observed') is not False
                    and not p.tiles[c].get('trap') and not p.tiles[c].get('plant')
                    and not p.effects_block_movement(p.tiles[c]) for c in around) \
            and sum(p.walkable(n) for n in neighbors(bank,width,height))>=2
        # A closed entrance can be the only origin whose protected round trip
        # fits the budget. Scout/open it with ordinary movement, then reobserve;
        # never charge its opening to an already-running potion. Unlike an
        # unknown drink, identified invisibility needs no frost-test bank.
        known_door=item.get('identified') and p.tiles[bank]['terrain'] in {5,6} \
            and bank not in p.room_blocked and bank not in p.blocked and bank not in p.loot \
            and bank not in p.neutral_actor_cells \
            and (bank!=state['hero']['cell'] or p.tiles[bank].get('visible')) \
            and all(c in p.tiles and p.tiles[c].get('observed') is not False
                    and p.tiles[c]['terrain'] in {1,3,4,5,6,9,11,12,14,19,20}
                    and not p.tiles[c].get('trap') and not p.tiles[c].get('plant')
                    and not p.effects_block_movement(p.tiles[c]) for c in around) \
            and not any(o['cell']==bank and not o.get('top_item') for o in state.get('objects',[])) \
            and sum(p.walkable(n) for n in neighbors(bank,width,height))>=2
        known_activation=item.get('identified') and p.tiles[bank].get('visible') and known_pool_bank(
            p,state,bank,neighbors,arrival=bank==state['hero']['cell'])
        if not verified and not known_water and not known_door and not known_activation:continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='pool',plan_only=True)
        if journey and known_activation and not (verified or known_water or known_door) \
                and not entrance_actionable(p,staged,journey):continue
        # Do not choose water from which the entrance helper cannot act.
        if journey and known_water:
            door=next((c for c in journey.route[1:] if p.tiles[c]['terrain']==5),None)
            if door is not None and distance(bank,door,width)!=1:continue
        if journey:choices.append((0 if verified or known_water or known_door else 1,
                                   len(p.route(paths,bank)),bank,journey))
    if not choices:return None
    _,_,bank,journey=min(choices,key=lambda c:(c[0],c[1],c[2]))
    p.planner.report['piranha_room']={'potion':'potion of invisibility','floor_supply':'Expected by the piranha-and-chest room rule',
        'bank':bank,'reward':journey.route[-1],'status':'Protected chest round trip planned; actual invisibility still required'}
    if bank!=state['hero']['cell']:
        p.puzzle_revisit_steps['pool']+=1
        return p.toward(state,bank,'room: stage known invisibility outside piranha reach',paths,intent=Intent.REPOSITION)
    if p.tiles[bank]['terrain']==5:return None  # Opening is not an arrival receipt.
    ready,opening=open_journey_entrance(p,state,journey)
    if not ready:return opening
    p.room_journey=journey
    p.room_attempts.add((state['depth'],'pool',journey.route[-1]))
    return use_room_supply(p,item,'DRINK','room: activate known invisibility for planned piranha chest round trip; verify actual buff',kind='pool')


def revisit_pool(p,state,demand,neighbors):
    if p.puzzle_revisit_steps['pool']>=48:return None
    key=(state['depth'],state.get('branch',0),demand.cell)
    if any(receipt[:3]==key for receipt in p.pool_approach_receipts):return None
    try:
        from .piranha_tactics import staging_bank
    except ImportError:
        from piranha_tactics import staging_bank
    paths=p.paths(state);choices=[]
    for bank in paths:
        route=p.route(paths,bank)
        if len(route)>41 or not staging_bank(p,state,bank):continue
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) for c in route[1:]):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        if plan_journey(p,staged,[],neighbors,probe_kind='pool',plan_only=True):
            choices.append((len(route),bank))
    if not choices:return None
    _,bank=min(choices)
    if bank==state['hero']['cell']:return None
    p.puzzle_revisit_steps['pool']+=1
    decision=p.toward(state,bank,'room: revisit observed piranha-room dry approach before testing floor supply',
                      paths,intent=Intent.REPOSITION)
    if decision:p.pool_approach_pending=(*key,bank)
    return decision


def stage_known_gas(p,state,item,neighbors):
    if 'DRINK' not in item.get('actions',[]) or p.room_journey:return None
    paths=p.paths(state);choices=[]
    for bank in paths:
        route=p.route(paths,bank)
        if len(route)>41 or p.tiles[bank]['terrain'] not in {1,3,9,11,14,19,20,29}:continue
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) for c in route):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='gas',plan_only=True)
        # A budgeted trip is not executable if its closed entrance cannot be
        # scouted from this bank. Apply the arrival prerequisite before travel,
        # rather than repeatedly staging here and yielding back to exploration.
        if journey and entrance_actionable(p,staged,journey):
            choices.append((len(route),bank,journey))
    if not choices:return None
    _,bank,journey=min(choices,key=lambda c:(c[0],c[1]))
    if bank!=state['hero']['cell']:
        if p.puzzle_revisit_steps['gas']>=48:return None
        p.puzzle_revisit_steps['gas']+=1
        return p.toward(state,bank,'room: stage known purity outside gas before protected retrieval',paths,intent=Intent.REPOSITION)
    ready,opening=open_journey_entrance(p,state,journey)
    if not ready:return opening
    p.room_journey=journey;p.room_attempts.add((state['depth'],'gas',journey.route[-1]))
    return use_room_supply(p,item,'DRINK','room: activate known purity for verified gas-room round trip; verify actual buff',kind='gas')


def refresh_barrier(p,state,demand,paths,distance):
    """Commit to one observation vantage; arrival without sight is a failed try."""
    pos=state['hero']['cell'];width=state['map']['width']
    plan=p.frost_view_plan
    if plan and plan['barrier']!=demand.cell:p.frost_view_plan=plan=None
    if plan:
        remote=plan.get('remote',False)
        route=p.route(paths,plan['view']) if plan['view'] in paths else []
        unsafe=remote and (p.recent_threats or any(
            p.tiles[n]['terrain'] in {7,8,10,18,21,22,31,37,38}
            or p.tiles[n].get('trap') or p.tiles[n].get('plant')
            or p.effects_block_movement(p.tiles[n]) for n in route[1:]))
        if pos==plan['view'] or not route or unsafe or plan['steps']>=plan.get('budget',12) \
                or remote and p.puzzle_revisit_steps['frost']>=48:
            p.frost_view_attempts.add((demand.cell,plan['view']))
            p.frost_view_plan=plan=None
        else:
            plan['steps']+=1
            if remote:p.puzzle_revisit_steps['frost']+=1
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
    # A remembered barrier can be beyond the local refresh envelope after
    # ordinary floor work. Admit bounded *observation travel* over a fully
    # known safe route, not a drink bank or permission to enter the fire.
    # Keep its own finite travel account and revalidate on each selection.
    if len(tried)<3 and not p.recent_threats and p.puzzle_revisit_steps['frost']<48:
        remote_views=[c for c in paths if c!=pos and c not in tried
            and 2<=distance(c,demand.cell,width)<=4
            and distance(c,demand.cell,width)<distance(pos,demand.cell,width)
            and 13<len(p.route(paths,c))<=41
            and len(p.route(paths,c))-1<=48-p.puzzle_revisit_steps['frost']
            and p.tiles[c]['terrain'] in {1,3,9,11,14,19,20,29}
            and c not in p.loot
            and all(p.tiles[n]['terrain'] not in {7,8,10,18,21,22,31,37,38}
                    and not p.tiles[n].get('trap') and not p.tiles[n].get('plant')
                    and not p.effects_block_movement(p.tiles[n])
                    for n in p.route(paths,c)[1:])
            and p.shot_clear(dict(state,hero=dict(state['hero'],cell=c)),demand.cell)]
        if remote_views:
            view=min(remote_views,key=lambda c:(len(p.route(paths,c)),distance(c,demand.cell,width),c))
            p.frost_view_plan={'barrier':demand.cell,'view':view,'steps':1,
                              'remote':True,'budget':len(p.route(paths,view))-1}
            p.puzzle_revisit_steps['frost']+=1
            return p.toward(state,view,'room: approach remembered fire over observed safe ground before rechecking frost staging',
                            paths,intent=Intent.EXPLORE)
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
        if not journey or not entrance_actionable(p,staged,journey):continue
        around={cell,*neighbors(cell,width,state['map']['height'])}
        if any(c not in p.tiles or p.tiles[c]['terrain'] not in {0,1,3,4,5,6,9,11,12,14,18,19,20,29}
               or p.tiles[c].get('plant') or p.tiles[c].get('effects')
               or c in p.loot for c in around):continue
        if p.tiles[cell].get('trap') or sum(p.walkable(n) for n in neighbors(cell,width,state['map']['height']))<2:continue
        choices.append((cell!=p.puzzle_flight_bank,len(route),cell))
    if not choices:return None
    _,_,view=min(choices)
    p.puzzle_flight_bank=view
    if view==pos:
        # Scout an actionable entrance before the visible-only drink-bank check,
        # not after it. A hypothetical reward route alone is not a test bank.
        # This is only the existing adjacent observed-door input; the next
        # observation must still pass every test/protection/round-trip gate.
        journey=plan_journey(p,state,[],neighbors,probe_kind='flight',plan_only=True)
        if journey:
            _,opening=open_journey_entrance(p,state,journey)
            return opening
        return None
    p.puzzle_revisit_steps['flight']+=1
    p.planner.report['puzzle_revisit']={'kind':'flight','hazard':demand.cell,'approach':view,
        'status':'Return to observed approach, then reobserve and replan candidate test/round trip',
        'identity_inferred':False,'qualification':'No hazard entry or potion use admitted by this staging move'}
    return p.toward(state,view,'room: revisit levitation-room approach before deferring protected reward',paths,intent=Intent.REPOSITION)


def known_flight_choices(p,state,neighbors):
    """Dry-run only, including the existing equipment and round-trip gates."""
    paths=p.paths(state);choices=[]
    for bank in paths:
        if len(p.route(paths,bank))>41 or p.tiles[bank]['terrain'] not in {1,3,9,11,14,19,20,29}:continue
        route=p.route(paths,bank)
        if any(p.tiles[c].get('trap') or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
               or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} for c in route[1:]):continue
        staged=dict(state,hero=dict(state['hero'],cell=bank))
        journey=plan_journey(p,staged,[],neighbors,probe_kind='flight',plan_only=True)
        if journey:choices.append((len(route),bank,journey))
    return choices


def prepare_flight_armor(p,state,neighbors):
    """Replace uncertain movement gear only for an otherwise verified trip."""
    try:
        from .combat_items import stats, unencumbered
    except ImportError:
        from combat_items import stats, unencumbered
    hero=state['hero']
    tile=p.tiles.get(hero['cell'],{})
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if unencumbered(state) or p.recent_threats or p.unseen_damage_turns \
            or state.get('danger_cells') or hero['hp']<.95*hero['max_hp'] \
            or not tile.get('visible') or hero['cell'] in p.room_blocked \
            or tile.get('terrain') not in GROUND \
            or any(tile.get(k) for k in ('trap','plant','effects')) \
            or any(b in buffs for b in ('hungr','starv','burn','poison','bleed','blind',
                                        'vertigo','paral','root','slow','crippl','chill','levitat')):
        return None
    worn=[i for i in state['inventory'] if i.get('equipped') and
          (stats(i) and stats(i)[0]=='armor' or
           any(n in i['name'].lower() for n in ('armor','robe')))]
    if not worn or any(not i.get('curse_known') or i.get('known_cursed')
                       or 'UNEQUIP' not in i.get('actions',[]) for i in worn):
        return None
    for spare in state['inventory']:
        value=stats(spare)
        if spare.get('equipped') or not spare.get('identified') \
                or spare.get('known_cursed') or not spare.get('curse_known') \
                or 'EQUIP' not in spare.get('actions',[]) \
                or not value or value[0]!='armor' or value[2]>hero['strength']:
            continue
        # A local inventory alternative is not an observation or an equip
        # receipt. Re-run all real gates on the next public observation.
        inventory=[dict(i,equipped=(i is spare)) if i in worn or i is spare
                   else dict(i) for i in state['inventory']]
        staged=dict(state,inventory=inventory)
        if unencumbered(staged) and known_flight_choices(p,staged,neighbors):
            return p.use(spare,'EQUIP','room: equip known strength-safe armor before planning levitation round trip')
    return None


def stage_known_flight(p,state,item,neighbors):
    if 'DRINK' not in item.get('actions',[]) or p.room_journey:return None
    choices=known_flight_choices(p,state,neighbors)
    if not choices:
        return prepare_flight_armor(p,state,neighbors)
    paths=p.paths(state)
    _,bank,journey=min(choices,key=lambda c:(c[0],c[1]))
    if bank!=state['hero']['cell']:
        if p.puzzle_revisit_steps['known-flight']>=48:return None
        p.puzzle_revisit_steps['known-flight']+=1
        return p.toward(state,bank,'room: stage known levitation near verified reward round trip',paths,intent=Intent.REPOSITION)
    ready,opening=open_journey_entrance(p,state,journey)
    if not ready:return opening
    p.room_journey=journey;p.room_attempts.add((state['depth'],'flight',journey.route[-1]))
    return use_room_supply(p,item,'DRINK','room: activate known levitation for planned reward round trip; verify actual buff',kind='flight')


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
        ready,opening=open_journey_entrance(p,state,journey)
        if not ready:return opening
        p.room_journey=journey
        return use_room_supply(p,item,'DRINK','room: activate known haste for verified sentry round trip; check actual speed buff',kind='sentry')
    return None


def observe_pool_entrance(p,before,state):
    """Observe entrance scouts; only actual visible open-door arrivals count."""
    # Ordinary exploration can perform the very same entrance scout. Its
    # visible open-door arrival remains evidence after the door recloses;
    # requiring a controller-specific pending token loses that observation.
    # This is geometry only, shared by both room kinds, not a supply/loot receipt.
    decision=p.last_decision
    door=state.get('hero',{}).get('cell')
    if before and decision and decision.action=={'type':'cell','cell':door} \
            and (before.get('depth'),before.get('branch',0)) == (state.get('depth'),state.get('branch',0)) \
            and isinstance(before.get('hero',{}).get('cell'),int) and isinstance(door,int) \
            and distance(before['hero']['cell'],door,state.get('map',{}).get('width',1))==1:
        old=next((t for t in before.get('map',{}).get('cells',[]) if t['cell']==door),{})
        tile=next((t for t in state.get('map',{}).get('cells',[]) if t['cell']==door),{})
        if old.get('visible') and old.get('terrain') in {5,6} \
                and tile.get('visible') and tile.get('terrain')==6 \
                and not any(t.get('trap') or t.get('plant') or t.get('effects') for t in (old,tile)):
            receipt=(state['depth'],state.get('branch',0),door)
            for kind in ('pool','flight'):
                getattr(p,kind+'_entrance_receipts').add(receipt)
        # Gas can spread onto an opened doorway, forcing immediate retreat.
        # That is still an observed entrance scout, not evidence that another
        # unprotected entry is needed after the ordinary door recloses.
        # This receipt never admits a hazard: bank/route planning still checks
        # fresh tiles, and execution still requires the actual protective buff.
        if hasattr(p,'gas_entrance_receipts') \
                and old.get('visible') and old.get('terrain') in {5,6} \
                and tile.get('visible') and tile.get('terrain')==6 \
                and not old.get('effects') \
                and not any(t.get('trap') or t.get('plant') for t in (old,tile)) \
                and all('cloud of toxic gas' in e.lower() for e in tile.get('effects',[])):
            p.gas_entrance_receipts.add((state['depth'],state.get('branch',0),door))
    # A dry approach scout is an observation task, not a protection or loot
    # receipt. Once actually reached, leaving it for other floor work must not
    # restart that same detour. Supply/test admission still runs on every input.
    pending=p.pool_approach_pending
    if pending is not None:
        p.pool_approach_pending=None
        depth,branch,_,bank=pending
        decision=p.last_decision
        tile=next((t for t in state.get('map',{}).get('cells',[]) if t['cell']==bank),{})
        if before and decision and decision.action=={'type':'cell','cell':bank} \
                and decision.intent==Intent.REPOSITION \
                and (before.get('depth'),before.get('branch',0))==(depth,branch) \
                and (state.get('depth'),state.get('branch',0))==(depth,branch) \
                and before.get('hero',{}).get('cell')!=bank \
                and state.get('hero',{}).get('cell')==bank and tile.get('visible'):
            p.pool_approach_receipts.add(pending)
    for kind in ('pool','flight'):
        pending=getattr(p,kind+'_entrance_pending')
        if pending is None:continue
        setattr(p,kind+'_entrance_pending',None)
        depth,branch,door=pending
        decision=p.last_decision
        if not before or not decision or decision.action != {'type':'cell','cell':door}:continue
        if (before.get('depth'),before.get('branch',0)) != (depth,branch) \
                or (state.get('depth'),state.get('branch',0)) != (depth,branch):continue
        tile=next((t for t in state.get('map',{}).get('cells',[]) if t['cell']==door),{})
        if state.get('hero',{}).get('cell')==door and tile.get('visible') \
                and tile.get('terrain')==6:
            getattr(p,kind+'_entrance_receipts').add(pending)


def unscouted_entrance(p,state,journey):
    """Read-only door prerequisite shared by bank selection and arrival."""
    # Ordinary doors close again when stepped off. A receipted entrance scout is
    # not undone by that normal reclosure. The newly planned round trip still
    # budgets entering the door, and Journey.advance rechecks every step.
    return next((c for c in journey.route[1:] if p.tiles[c]['terrain']==5
               and not (journey.kind in {'pool','flight','gas'}
                        and (state['depth'],state.get('branch',0),c)
                            in getattr(p,journey.kind+'_entrance_receipts')
                        and not p.tiles[c].get('trap') and not p.tiles[c].get('plant')
                        and not p.effects_block_movement(p.tiles[c]))),None)


def entrance_actionable(p,state,journey):
    door=unscouted_entrance(p,state,journey)
    return door is None or (distance(state['hero']['cell'],door,state['map']['width'])==1
                            and p.tiles[door].get('visible'))


def open_journey_entrance(p,state,journey):
    """A dry-run closed door is scouting only; open it before any potion is spent."""
    door=unscouted_entrance(p,state,journey)
    if door is None:return True,None
    if distance(state['hero']['cell'],door,state['map']['width'])==1 and p.tiles[door].get('visible'):
        if journey.kind in {'pool','flight'}:
            setattr(p,journey.kind+'_entrance_pending',(state['depth'],state.get('branch',0),door))
        return False,p.cell(door,'room: open observed '+journey.kind+' entrance before spending its potion',
                            intent=Intent.REPOSITION)
    return False,None


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
            # This hungry scout bypasses the normal candidate selection below.
            # Without a carried flight supply it can only pull us back from
            # other floor work, then yield at the bank and repeat indefinitely.
            if not any('DRINK' in i.get('actions',[]) and (
                    base_name(i)==demand.potion or unknown_potion(i)
                    and (state['depth'],base_name(i)) not in p.puzzle_drinks
                    and sum(d==state['depth'] for d,_ in p.puzzle_drinks)<MAX_ROOM_POTION_TESTS)
                    for i in state['inventory']):
                continue
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
            if demand.kind=='gas' and getattr(p,'reserve_floor_puzzle_supplies',False):
                staged=stage_known_gas(p,state,known,neighbors)
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
            i.get("quantity",1)==1 or bandolier_protected(p,state),
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
        if candidate.get("quantity",1)>1 and not bandolier_protected(p,state) and demand.kind != 'gas':
            continue  # Safe identification above is still allowed; an unprotected stack is not a drink test.
        if hero["hp"]<0.95*hero["max_hp"]:
            continue  # Safe identification is not permission for a risky drink.
        if demand.kind=="frost":
            if sum(d==state["depth"] for d,_ in p.puzzle_drinks)>=MAX_ROOM_POTION_TESTS:
                continue
            width=state["map"]["width"]
            barriers=[c for c,t in p.tiles.items() if t.get("visible") and fire_barrier(t)]
            paths=p.paths(state)
            # Seeing the fire from an intermediate route square does not mean
            # the committed observation vantage was reached. Finish that
            # admitted travel before visible-only bank checks can yield to
            # unrelated exploration and repeatedly pull us back.
            plan=p.frost_view_plan
            if plan and fire_barrier(p.tiles.get(plan['barrier'],{})):
                if hero['cell']==plan['view']:
                    p.frost_view_attempts.add((plan['barrier'],plan['view']))
                    p.frost_view_plan=None
                else:
                    # The nearest tile in a multi-tile fire wall may change
                    # mid-route. The existing plan owns its original anchor.
                    anchor=Demand('frost','potion of frost',plan['barrier'])
                    refresh=refresh_barrier(p,state,anchor,paths,distance)
                    if refresh:return refresh
            banks=[c for c in paths if len(p.route(paths,c))<=12
                   and safe_test_bank(p,state,c,distance,neighbors,allow_dry=True)
                   and any((c%width==b%width or c//width==b//width)
                           and distance(c,b,width)==2 for b in barriers)]
            # Preflight a new frost approach: a safe drink square alone does
            # not protect the other potions. Decline futile staging locally.
            # At the current bank, retain the real protection/receipt checks
            # below; an already-started stash retains its recovery path too.
            if not p.potion_stash:
                banks=[c for c in banks if c==hero["cell"] or can_protect_potions(
                    p,dict(state,hero=dict(hero,cell=c)),candidate,
                    distance,neighbors,safe_test_bank)]
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
                return use_room_supply(p,candidate,"DRINK","room: test unconfirmed frost beside barrier with one intervening square; verify fire removal",kind='frost')
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
        if sum(d == state["depth"] for d,_ in p.puzzle_drinks) >= MAX_ROOM_POTION_TESTS:
            continue
        if (state["depth"],base_name(candidate)) in p.puzzle_drinks:
            continue
        paths = p.paths(state)
        banks = [c for c in paths if len(p.route(paths,c)) <= 41
                  and (demand.kind=='flight'
                       or demand.kind=='pool' and getattr(p,'reserve_floor_puzzle_supplies',False)
                       or distance(c,demand.cell,state["map"]["width"]) <= 5)
                  and (safe_test_bank(p,state,c,distance,neighbors,allow_dry=True,pool_bank=True)
                        if demand.kind=='pool' and getattr(p,'reserve_floor_puzzle_supplies',False)
                        else safe_test_bank(p,state,c,distance,neighbors,allow_dry=demand.kind in {'flight','sentry','gas'}
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
                if journey and entrance_actionable(p,staged,journey):journeys[bank]=journey
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
                if demand.kind=='pool':
                    staged=revisit_pool(p,state,demand,neighbors)
                    if staged:return staged
            continue
        # A protected reward route alone is insufficient for an unknown drink:
        # frost could destroy the other carried potions. Admit the same remote
        # stash route used by protect_potions BEFORE committing to a test bank.
        # Infeasible, unstarted preparation declines locally; it must not raise
        # a stash obligation that disables all other floor potion supplies.
        banks = [bank for bank in banks if can_protect_potions(
            p,dict(state,hero=dict(hero,cell=bank)),candidate,
            distance,neighbors,safe_test_bank,isolated_stack=demand.kind=='gas')]
        if not banks:
            continue
        bank = min(banks,key=lambda c:len(p.route(paths,c)))
        if bank != hero["cell"]:
            return p.toward(state,bank,"room: stage unconfirmed potion test on safe water",paths,
                            intent=Intent.REPOSITION)
        if bank in journeys:
            ready,opening=open_journey_entrance(p,state,journeys[bank])
            if not ready:
                if opening:return opening
                continue
        stash=protect_potions(p,state,candidate,distance,neighbors,safe_test_bank,isolated_stack=demand.kind=='gas')
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
            return use_room_supply(p,candidate,"DRINK",f"room: test unconfirmed {demand.potion} hypothesis on water; verify actual effect",kind=demand.kind)
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
