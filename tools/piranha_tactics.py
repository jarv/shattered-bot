"""Persistent observed piranha/chest objective; potion availability is not identity."""
try:
    from .special_rooms import component
    from .policy_geometry import neighbors,distance
except ImportError:
    from special_rooms import component
    from policy_geometry import neighbors,distance


def pending(p):
    return {cell:room for cell,room in p.piranha_rooms.items() if not room['collected']}


def observe(p,state):
    width,height=state['map']['width'],state['map']['height']
    # Copy accepted pickup receipts before ordinary loot bookkeeping clears them.
    for cell,room in p.piranha_rooms.items():
        if cell in p.loot_collection_receipts:
            room['collected']=True
    for actor in p.room_actors.values():
        if 'piranha' not in actor['name'].lower():continue
        water=component(actor['cell'],p.tiles,{29},width,height)
        shore={n for c in water for n in neighbors(c,width,height)}
        for cell,obj in p.loot.items():
            if 'chest' not in obj.get('name','').lower() or obj.get('for_sale') or cell not in water|shore:
                continue
            room=p.piranha_rooms.setdefault(cell,{'water':set(),'collected':False})
            room['water'].update(water)
    # Remember the hazard habitat, not a hidden actor's current location.
    for room in p.piranha_rooms.values():
        blocked=room['water']|{n for c in room['water'] for n in neighbors(c,width,height)}
        p.room_blocked.update(blocked)
        p.room_skipped.update(blocked)


def choose(p,state,enemies):
    try:
        from .room_supplies import exhausted
    except ImportError:
        from room_supplies import exhausted
    if exhausted(p,state,'pool'):return None
    rooms=pending(p)
    if not rooms or enemies or p.recent_threats or state.get('danger_cells') or p.room_journey \
            or p.puzzle_probe or state.get('status')!='ready' or state.get('modal'):return None
    try:
        from .puzzle_supplies import stage_known_pool,prepare_supplies,Demand
        from .consumable_tactics import base_name
    except ImportError:
        from puzzle_supplies import stage_known_pool,prepare_supplies,Demand
        from consumable_tactics import base_name
    potion=next((i for i in state['inventory'] if base_name(i)=='potion of invisibility'
                 and 'DRINK' in i.get('actions',[])),None)
    target=min(rooms,key=lambda c:distance(c,state['hero']['cell'],state['map']['width']))
    p.planner.report['piranha_room']={'reward':target,'collected':False,
        'floor_supply':'PoolRoom supplies PotionOfInvisibility on this floor; search/test prior, not an item identity',
        'status':'Use carried known invisibility' if potion else 'Seek/identify/test observed floor potions'}
    if potion:
        return stage_known_pool(p,state,Demand('pool','potion of invisibility',target),potion,distance,neighbors)
    return prepare_supplies(p,state,enemies,distance,neighbors)


def staging_bank(p,state,cell):
    """Known dry approach for a later visible recheck, not an unknown-drink permit."""
    width,height=state['map']['width'],state['map']['height']
    around={cell,*neighbors(cell,width,height)}
    return p.tiles.get(cell,{}).get('terrain') in {1,3,9,11,14,19,20} \
        and cell not in p.room_blocked and cell not in p.loot \
        and all(c in p.tiles and p.tiles[c].get('observed') is not False
                and p.tiles[c]['terrain'] in {1,3,4,5,6,9,11,12,14,19,20}
                and not p.tiles[c].get('plant') and not p.tiles[c].get('trap')
                and not p.effects_block_movement(p.tiles[c]) for c in around) \
        and sum(p.walkable(n) for n in neighbors(cell,width,height))>=2
