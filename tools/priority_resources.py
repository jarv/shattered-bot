"""Publicly named permanent progression pickups, never potion-color guesses."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .policy_geometry import distance,neighbors
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent
    from policy_geometry import distance,neighbors


NAMES={'scroll of upgrade','potion of strength'}


def targets(p):
    return {c:o for c,o in p.loot.items() if not o.get('for_sale')
            and base_name(o.get('top_item',o)) in NAMES}


def diagnostics(p,state,enemies=(),paths=None):
    """Report existing public-policy vetoes; never relax pickup admission."""
    pending=targets(p)
    report={'depth':state.get('depth'),'branch':state.get('branch',0),
            'hero_cell':state.get('hero',{}).get('cell'),'targets':[],
            'qualification':'Observed/cached public resources and current policy bookkeeping; no pickup or safe route inferred'}
    if state.get('status')!='ready' or state.get('modal') or not state.get('hero'):
        report['general_veto']='not a ready gameplay observation'
        return report
    paths=p.paths(state) if paths is None else paths
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    report['general_veto']=[label for flag,label in (
        (bool(enemies),'current enemies'),(bool(p.recent_threats),'remembered threats'),
        (bool(state.get('danger_cells')),'rendered warnings'),
        (any(b in buffs for b in ('burn','poison','bleed','paral','root','vertigo','blind')),'damaging or impaired condition'),
        (bool(p.inventory_pressure),'inventory pressure')) if flag]
    report['preparation_state']={
        'puzzle_probe_active':bool(getattr(p,'puzzle_probe',None)),
        'puzzle_hungry_frost':bool(getattr(p,'puzzle_hungry_frost',False)),
        'reserve_floor_puzzle_supplies':bool(getattr(p,'reserve_floor_puzzle_supplies',False)),
        'room_journey_active':bool(getattr(p,'room_journey',None)),
        'potion_stash_active':bool(getattr(p,'potion_stash',None)),
        'trap_payload_return_active':bool(getattr(p,'trap_payload_return',None)),
        'deferred_room_controllers':sorted(getattr(p,'deferred_room_controllers',set())),
        'puzzle_meal_attempted':(state['depth'],'puzzle-meal') in p.room_attempts}
    width=state['map']['width']
    def rejection(cell):
        tile=p.tiles.get(cell,{})
        reasons=[]
        if cell in p.blocked:reasons.append('blocked by prior movement bookkeeping')
        if p.failed_moves[cell]:reasons.append('failed movement recorded')
        if cell in p.room_blocked:reasons.append('room hazard/obligation barrier')
        if cell in p.neutral_actor_cells and cell not in p.friendly_passage_cells:reasons.append('neutral/friendly occupancy')
        if cell in getattr(p,'fire_buffer',set()):reasons.append('observed eternal-fire safety buffer')
        if cell in getattr(p,'fire_spread_buffer',set()):reasons.append('observed fire-spread safety buffer')
        if tile.get('trap'):reasons.append('observed trap')
        if tile.get('plant'):reasons.append('observed plant')
        if p.effects_block_movement(tile):reasons.append('observed/cached harmful effects')
        if tile.get('terrain') in {7,8,10,18,21,22,31,37,38}:reasons.append('transition, lock or hazard terrain')
        if not p.walkable(cell) and not reasons:reasons.append('other walkability or interaction veto')
        return {'cell':cell,'terrain':tile.get('terrain'),'reasons':reasons}
    for cell,obj in sorted(pending.items())[:8]:
        route=p.route(paths,cell) if cell in paths else []
        entry={'cell':cell,'public_name':base_name(obj.get('top_item',obj)),
               'currently_visible':bool(p.tiles.get(cell,{}).get('visible')),
               'reachable_in_current_paths':cell in paths,'target_rejections':rejection(cell),
               'route':route[:32],'route_steps':len(route)-1 if route else None,
               'route_omitted_steps':max(0,len(route)-32)}
        entry['route_rejections']=[rejection(c) for c in route[1:] if
            c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
            or p.effects_block_movement(p.tiles[c])
            or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38}][:8]
        if not route:
            try:
                from .survival_policy import TRANSITIONS,DOOR_KEYS
            except ImportError:
                from survival_policy import TRANSITIONS,DOOR_KEYS
            expandable=[c for c in paths if c==state['hero']['cell'] or (
                p.tiles[c]['terrain'] not in TRANSITIONS|DOOR_KEYS.keys()
                and not p.loot.get(c,{}).get('for_sale')
                and 'chest' not in p.loot.get(c,{}).get('name','').lower())]
            boundary={n for c in expandable for n in neighbors(c,width,state['map']['height'])
                      if n not in paths and n in p.tiles and p.tiles[n]['terrain'] in {1,2,3,5,6,7,8,9,10,11,14,15,18,19,20,21,22,29,30,31,32,37,38}}
            entry['nearest_reachable_component_boundaries']=[rejection(c) for c in
                sorted(boundary,key=lambda c:(distance(c,cell,width),c))[:8]]
        report['targets'].append(entry)
    report['omitted_targets']=max(0,len(pending)-8)
    return report


def choose(p,state,enemies):
    resources=targets(p)
    if resources and hasattr(p,'planner'):
        p.planner.report['priority_resource']=diagnostics(p,state,enemies)
    if enemies or p.recent_threats or state.get('danger_cells') or state.get('status')!='ready' or state.get('modal'):return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burn','poison','bleed','paral','root','vertigo','blind')):return None
    if not resources:return None
    paths=p.paths(state);choices=[]
    for cell,obj in resources.items():
        if cell not in paths or p.failed_moves[cell] or cell in p.blocked:continue
        route=p.route(paths,cell)
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38}
               for c in route[1:]):continue
        choices.append((len(route),cell))
    if not choices:
        # Preparation yields to this priority leaf. If pickup is not admitted,
        # allow the existing guarded puzzle-supply controller to make progress.
        try:
            from .puzzle_supplies import prepare_supplies
        except ImportError:
            from puzzle_supplies import prepare_supplies
        return prepare_supplies(p,state,enemies,distance,neighbors)
    if p.inventory_pressure:
        try:
            from .inventory_tactics import choose as cleanup
        except ImportError:
            from inventory_tactics import choose as cleanup
        room=cleanup(p,state,enemies)
        if room:return room
        return None  # Do not repeatedly click a known full-pack pickup.
    _,cell=min(choices)
    return p.toward(state,cell,'loot: prioritize observed permanent upgrade/strength resource',paths,intent=Intent.LOOT)
