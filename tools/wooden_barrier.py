"""Purposeful unknown-fire drinking beside wood, with a committed water exit."""
try:
    from .policy_geometry import distance,neighbors
    from .policy_decision import Intent
    from .combat_items import unencumbered
    from .consumable_tactics import base_name
    from .potion_stash import protect_potions
except ImportError:
    from policy_geometry import distance,neighbors
    from policy_decision import Intent
    from combat_items import unencumbered
    from consumable_tactics import base_name
    from potion_stash import protect_potions


def prepare(p,state,demand,candidate,safe_bank):
    if not getattr(p,'reserve_floor_puzzle_supplies',False) or p.wood_burn_plan:return None
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells') or p.recent_threats:return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burn','poison','bleed','chill','frozen','paral','root','vertigo','slow','crippl',
                                'levitat','flying','magic immun','blind','drowsy')):return None
    if candidate.get('quantity',1)!=1 or p.wood_probe_attempts[demand.cell]>=2:return None
    if sum(d==state['depth'] for d,_ in p.puzzle_drinks)>=2 or not unencumbered(state):return None
    wood=demand.cell;tile=p.tiles.get(wood,{})
    if tile.get('terrain')!=13 or not tile.get('visible'):return None
    p.planner.report['wooden_barrier']={'cell':wood,'floor_supply':'Liquid flame is supplied on this wooden-barrier floor',
                                       'identity_inferred':False}
    hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    if hero['hp']<.95*hero['max_hp']:return None
    paths=p.paths(state);choices=[]
    dry={1,3,9,11,14,19,20};nonflammable={0,1,3,4,9,11,12,14,19,20,24,25,26,28,29}
    for bank in neighbors(wood,width,height):
        t=p.tiles.get(bank,{})
        if bank not in paths or len(p.route(paths,bank))>9 or t.get('terrain') not in dry \
                or not t.get('visible') or t.get('trap') or t.get('plant') or t.get('effects') \
                or bank in p.loot or bank in p.room_blocked:continue
        area={bank,*neighbors(bank,width,height)}
        if any(c not in p.tiles or not p.tiles[c].get('visible') or p.tiles[c].get('plant')
               or p.tiles[c].get('trap') or p.tiles[c].get('effects') or c in p.loot
               or c!=wood and p.tiles[c]['terrain'] not in nonflammable for c in area):continue
        if any(o['cell'] in area for o in state.get('objects',[]) if not o.get('top_item')):continue
        # One ordinary move into observed water: no promises of outrunning fire
        # along a long route, through a door, or over an unknown movement delay.
        waters=[c for c in neighbors(bank,width,height) if p.tiles.get(c,{}).get('terrain')==29
                and p.tiles[c].get('visible') and c not in p.loot and c not in p.room_blocked
                and not p.tiles[c].get('trap') and not p.tiles[c].get('plant') and not p.tiles[c].get('effects')
                and distance(c,wood,width)>=2]
        if waters:choices.append((len(p.route(paths,bank)),bank,min(waters)))
    if not choices:
        p.planner.report['potion_reservation']={'puzzle':'wooden barrier','potion':'potion of liquid flame',
            'reason':'Preserve expected floor supply: no isolated dry bank with an immediate observed water exit',
            'identity_inferred':False}
        return None
    _,bank,water=min(choices)
    if pos!=bank:
        return p.toward(state,bank,'room: stage unknown fire potion beside wooden barrier with immediate water exit',paths,intent=Intent.REPOSITION)
    stash=protect_potions(p,state,candidate,distance,neighbors,safe_bank)
    if stash:return stash
    if p.potion_stash:p.potion_stash['phase']='retrieve'
    p.wood_probe_attempts[wood]+=1
    p.puzzle_drinks.add((state['depth'],base_name(candidate)))
    p.wood_burn_plan={'depth':state['depth'],'branch':state.get('branch',0),'wood':wood,'bank':bank,
                      'water':water,'phase':'observe','steps':0}
    p.puzzle_probe={'depth':state['depth'],'kind':'flame','turns':0}
    p.potion_probe_permit=(candidate['id'],candidate['name'])
    try:
        try:
            from .room_supplies import use as use_room_supply
        except ImportError:
            from room_supplies import use as use_room_supply
        return use_room_supply(p,candidate,'DRINK','room: test unknown fire beside wood; retreat immediately to verified water if burning',kind='flame')
    finally:p.potion_probe_permit=None


def recover(p,state,enemies):
    plan=p.wood_burn_plan
    if not plan or state.get('status')!='ready' or state.get('modal'):return None
    if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0):p.wood_burn_plan=None;return None
    if enemies or state.get('danger_cells'):
        p.wood_burn_plan=None;return None  # Ordinary threat/telegraph survival takes precedence.
    plan['steps']+=1
    pos=state['hero']['cell'];buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if plan['steps']>16 or state['hero']['hp']<.5*state['hero']['max_hp']:
        p.log_continuation_error(state,'wooden-barrier-incomplete','Wood ignition/water recovery exceeded its observed budget',dict(plan))
        p.wood_burn_plan=None;return None
    if plan['phase']=='observe':
        if 'burning' not in buffs:
            p.wood_burn_plan=None;return None  # Wrong potion: normal probe recovery checks actual effects.
        plan['phase']='water'
    if plan['phase']=='water':
        if any(b in buffs for b in ('levitat','flying','root','paral','vertigo')):
            p.wood_burn_plan=None;return None  # Do not pretend water can rinse an airborne/immobile hero.
        if pos!=plan['water']:
            tile=p.tiles.get(plan['water'],{})
            if pos!=plan['bank'] or tile.get('terrain')!=29 or not tile.get('visible') \
                    or tile.get('trap') or tile.get('plant') or plan['water'] in p.loot \
                    or any(o['cell']==plan['water'] and not o.get('top_item') and o['name'].lower()!='mirror image' for o in state.get('objects',[])) \
                    or any('fire is raging' not in e.lower() for e in tile.get('effects',[])):
                p.wood_burn_plan=None;return None
            return p.cell(plan['water'],'room: extinguish tested fire immediately in committed adjacent water',intent=Intent.RETREAT)
        if 'burning' in buffs:return p.decision({'type':'wait'},'room: verify burning ends in observed water',intent=Intent.RECOVER)
        if p.puzzle_probe and p.puzzle_probe.get('kind')=='flame':p.puzzle_probe=None
        plan['phase']='verify-wood'
    wood=p.tiles.get(plan['wood'],{})
    if wood.get('visible') and wood.get('terrain') not in {13,27} and not p.effects_block_movement(wood):
        p.planner.report['wooden_barrier']={'cell':plan['wood'],'status':'Observed wooden barrier removed and entry effects clear; loot not claimed'}
        p.wood_burn_plan=None;return None
    if pos==plan['water'] and not p.effects_block_movement(p.tiles[pos]) and plan['steps']<=12:
        return p.decision({'type':'wait'},'room: observe wooden barrier ignition/fire expiry from water',intent=Intent.RECOVER)
    p.defer_obligations(state,[{'kind':'unverified burned wooden barrier','cell':plan['wood']}],
                        'Burning/clearance not visibly confirmed within bounded water observation')
    p.wood_burn_plan=None
    return None


def known_burn(p,state,enemies):
    """Throw known flame from observed isolated ground, without inventing the room interior."""
    if enemies or p.recent_threats or p.wood_burn_plan or state.get('danger_cells') \
            or state.get('status')!='ready' or state.get('modal'):return None
    hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if hero['hp']<.8*hero['max_hp'] or any(t in buffs for t in ('burn','poison','bleed','blind','vertigo','paral','root')):return None
    try:
        from .room_supplies import eligible
    except ImportError:
        from room_supplies import eligible
    flame=next((i for i in state['inventory'] if base_name(i)=='potion of liquid flame'
                and 'THROW' in i.get('actions',[]) and eligible(p,i,'THROW','flame')),None)
    if not flame:return None
    paths=p.paths(state);nonflammable={0,1,3,4,9,11,12,14,19,20,24,25,26,28,29};choices=[]
    # Shelves are optional fuel, not proof that this floor's barricade supply
    # is surplus. Keep the last known dose until ordinary branch discovery is
    # finished, and always reserve it for an actually remembered barricade.
    # This neither clears shelf backs nor admits any hazard/unknown potion use.
    reserve_shelves=False
    if getattr(p,'reserve_floor_puzzle_supplies',False) and sum(
            i.get('quantity',1) for i in state['inventory']
            if base_name(i)=='potion of liquid flame')<=1:
        report=p.exploration_report(state,paths)
        reserve_shelves=any(t.get('terrain')==13 for t in p.tiles.values()) or any(
            report[key] for key in ('unexplored_frontiers','unopened_doors',
                                   'unresolved_doors','unreachable_known_floor'))
    for wood,tile in p.tiles.items():
        key=(state['depth'],'burn',wood)
        if tile.get('terrain') not in {13,27} or key in p.room_attempts or p.known_burn_staging[wood]>=32:continue
        if tile['terrain']==27 and reserve_shelves:continue
        # Bookshelves can hide secret reward alcoves, without being a barricade
        # potion-supply room. Follow only the observed bounded fuel component.
        fuel={wood};queue=[wood]
        while queue and len(fuel)<=16:
            for n in neighbors(queue.pop(),width,height):
                if n not in fuel and p.tiles.get(n,{}).get('terrain') in {13,27}:
                    fuel.add(n);queue.append(n)
        if len(fuel)>16:continue
        area=fuel|{n for c in fuel for n in neighbors(c,width,height)}
        # Unseen far-side cells are unknown collateral risk, not certified safe floor.
        if any(c in p.loot and not base_name(p.loot[c].get('top_item',p.loot[c])).startswith('stone of ')
               or p.tiles.get(c,{}).get('plant') or p.tiles.get(c,{}).get('trap')
               or c not in fuel and c in p.tiles and p.tiles[c]['terrain'] not in nonflammable for c in area):continue
        if any(o['cell'] in area for o in state.get('objects',[]) if not o.get('top_item')):continue
        for bank in paths:
            route=p.route(paths,bank)
            if not (2 if tile['terrain']==27 else 3)<=distance(bank,wood,width)<=4 or len(route)>25:continue
            safe={bank,*neighbors(bank,width,height)}
            if any(c not in p.tiles or p.tiles[c]['terrain'] not in nonflammable or p.tiles[c].get('trap')
                    or p.tiles[c].get('plant') or p.tiles[c].get('effects')
                    or c in p.loot and not base_name(p.loot[c].get('top_item',p.loot[c])).startswith('stone of ')
                    for c in safe):continue
            if any(o['cell'] in safe for o in state.get('objects',[]) if not o.get('top_item')):continue
            staged=dict(state,hero=dict(hero,cell=bank))
            if not p.shot_clear(staged,wood):continue
            choices.append((len(route),wood,bank))
    if not choices:return None
    _,wood,bank=min(choices)
    p.planner.report['wooden_barrier']={'cell':wood,'bank':bank,'status':'Stage known flame outside impact area',
        'qualification':'Unseen room interior remains unknown; protect observed loot/allies and isolated throwing bank; no reward inferred'}
    if pos!=bank:
        p.known_burn_staging[wood]+=1
        return p.toward(state,bank,'room: approach observed barricade from isolated flame throwing bank',paths,intent=Intent.REPOSITION)
    if not p.tiles[wood].get('visible'):return None  # Never throw at a merely remembered target.
    p.room_attempts.add((state['depth'],'burn',wood))
    p.wood_burn_plan={'depth':state['depth'],'branch':state.get('branch',0),'wood':wood,'bank':bank,
                      'water':bank,'phase':'verify-wood','steps':0}
    try:
        from .room_supplies import use as use_room_supply
    except ImportError:
        from room_supplies import use as use_room_supply
    return use_room_supply(p,flame,'THROW','room: ignite observed barricade from isolated bank; verify fire expiry before entry',kind='flame',target=wood)
