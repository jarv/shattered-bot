"""Chest-independent public pool recognition, dry scouting and protected surveys."""
try:
    from .special_rooms import component,adjacent
    from .policy_geometry import neighbors,distance
    from .policy_decision import Intent
except ImportError:
    from special_rooms import component,adjacent
    from policy_geometry import neighbors,distance
    from policy_decision import Intent


def classify(p,state,water):
    width,height=state['map']['width'],state['map']['height']
    border={n for c in water for n in adjacent(c,width,height)}-water
    walls={c for c in border if p.tiles.get(c,{}).get('observed')
           and p.tiles[c].get('terrain') in {4,12}}
    strip={c for c in border if p.tiles.get(c,{}).get('observed') and p.tiles[c].get('terrain')==14}
    doors={n for c in strip for n in neighbors(c,width,height)
           if p.tiles.get(n,{}).get('observed') and p.tiles[n].get('terrain') in {5,6}}
    # PoolRoom's flooded interior touches its enclosing wall and has an entrance
    # strip of special flooring. AquariumRoom instead has a dry ring around water.
    if walls and strip and doors:return 'pool'
    if border and all(p.tiles.get(c,{}).get('observed')
                      and p.tiles[c].get('terrain') in {1,3,14,20} for c in border):
        return 'aquarium'
    return 'candidate'


def observe(p,state,before=None):
    width,height=state['map']['width'],state['map']['height']
    for actor in p.room_actors.values():
        if 'piranha' not in actor.get('name','').lower() \
                or p.tiles.get(actor['cell'],{}).get('terrain')!=29:continue
        water=component(actor['cell'],p.tiles,{29},width,height)
        matches=[key for key,h in p.piranha_habitats.items() if h['water']&water]
        key=min(matches) if matches else min(water)
        habitat=p.piranha_habitats.setdefault(key,{'water':set(),'profile':'candidate',
            'scout_steps':0,'scouted':set(),'pending':None,'surveyed':False})
        for old in matches:
            if old==key:continue
            other=p.piranha_habitats.pop(old)
            habitat['water'].update(other['water'])
            habitat['scouted'].update(other['scouted'])
            habitat['scout_steps']+=other['scout_steps']
        habitat['water'].update(water)
    for habitat in p.piranha_habitats.values():
        habitat['profile']=classify(p,state,habitat['water'])
        pending=habitat.get('pending');decision=p.last_decision
        if pending is not None and before and decision \
                and (before.get('depth'),before.get('branch',0))==(state['depth'],state.get('branch',0)) \
                and decision.action=={'type':'cell','cell':state['hero']['cell']} \
                and before.get('hero',{}).get('cell')!=state['hero']['cell'] \
                and state['hero']['cell']==pending and p.tiles[pending].get('visible'):
            habitat['scouted'].add(pending);habitat['pending']=None
    if p.piranha_habitats:
        p.planner.report['piranha_profiles']=[{'water':sorted(h['water']),'profile':h['profile'],
            'chest_required_for_recognition':False,'scout_steps':h['scout_steps']}
            for h in p.piranha_habitats.values()]


def matching(p):
    return [h for h in p.piranha_habitats.values() if h['profile']=='pool' and not h['surveyed']]


def scout(p,state):
    """Ordinary paths retain the whole habitat/shore exclusion, including fast fish."""
    if p.recent_threats or state.get('danger_cells') or p.room_journey or p.potion_stash:return None
    if state['hero']['hp']<.8*state['hero']['max_hp']:return None
    try:
        from .hunger_budget import admits,travel_cost
    except ImportError:
        from hunger_budget import admits,travel_cost
    paths=p.paths(state);width=state['map']['width']
    for h in p.piranha_habitats.values():
        if h['profile']!='candidate' or h['scout_steps']>=48 or len(h['scouted'])>=4:continue
        if any(room['water']&h['water'] for room in p.piranha_rooms.values()):continue
        choices=[]
        for c in paths:
            route=p.route(paths,c)
            if c==state['hero']['cell'] or c in h['scouted'] or not 2<=len(route)<=25 \
                    or min(distance(c,w,width) for w in h['water'])>6:continue
            if any(p.tiles[n]['terrain'] not in {1,3,5,6,9,11,14,19,20}
                   or n in p.loot or any(p.tiles[n].get(k) for k in ('trap','plant','effects')) for n in route[1:]):continue
            if not admits(p,state,2*travel_cost(state,p,route)+12):continue
            choices.append((c!=h['pending'],len(route),c))
        if choices:
            _,_,c=min(choices);h['pending']=c;h['scout_steps']+=1
            return p.toward(state,c,'room: observe piranha habitat profile from safe dry exterior',paths,intent=Intent.REPOSITION)
    return None


def survey_plan(p,state):
    """A matched pool admits a bounded invisibility survey without an invented chest."""
    try:
        from .protected_rewards import enclosure,paths,RewardTrip
        from .room_tactics import remaining
    except ImportError:
        from protected_rewards import enclosure,paths,RewardTrip
        from room_tactics import remaining
    bank=state['hero']['cell'];width=state['map']['width'];height=state['map']['height']
    choices=[]
    for h in matching(p):
        room=enclosure(p,state,min(h['water']))
        if not room or any(c in room for c in p.piranha_rooms):continue
        # Keep the independently observed exterior bank connected via ordinary
        # safe approaches; those paths cannot admit the habitat or its shore.
        exterior=set(p.paths(state))
        allowed=room|exterior
        graph=paths(p,state,bank,'pool',allowed,probe=True)
        for c in room&graph.keys():
            if c==bank or c in p.neutral_actor_cells:continue
            route=p.route(graph,c)
            back=paths(p,state,c,'pool',allowed,probe=True)
            if bank not in back:continue
            cost=len(route)+len(p.route(back,bank))-2+3
            if cost> (remaining(state,'invisible') or 20):continue
            # A genuine observation opportunity near the unseen remainder,
            # rather than consuming invisibility to visit arbitrary known water.
            unknown=sum(n not in p.tiles or p.tiles[n].get('observed') is False
                        for n in neighbors(c,width,height))
            if not unknown:continue
            choices.append((-unknown,-len(route),c,route,room,cost))
    if not choices:return None
    _,_,_,route,room,cost=min(choices,key=lambda c:c[:3])
    return RewardTrip('pool',route,state['depth'],room,[],cost,
                      branch=state.get('branch',0),survey=True)
