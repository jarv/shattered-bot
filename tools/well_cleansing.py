"""Clean spare curses by throwing into publicly recognized health water."""
try:
    from .combat_items import known_cursed,stats,accessory_kind
    from .consumable_tactics import base_name
    from .inventory_tactics import quiet
    from .resource_tactics import healing_water
    from .policy_geometry import distance,neighbors
except ImportError:
    from combat_items import known_cursed,stats,accessory_kind
    from consumable_tactics import base_name
    from inventory_tactics import quiet
    from resource_tactics import healing_water
    from policy_geometry import distance,neighbors


def choose(p,state,enemies):
    if not getattr(p,'unit_strategies_enabled',False) or not quiet(p,state,enemies):return None
    plan=p.well_cleanse_plan
    if plan:
        plan['steps']+=1
        if plan['steps']>5:
            p.well_cleanse_plan=None
            p.log_continuation_error(state,'well-cleanse-unverified','Cleansing/retrieval not confirmed; no retry',dict(plan))
            return None
        carried=[i for i in state['inventory'] if base_name(i)==plan['name']]
        if carried:
            p.planner.report['well_cleansing']={'name':plan['name'],
                'confirmed':any(i.get('curse_known') and not known_cursed(i) for i in carried),
                'qualification':'Public carried curse state, not a claim based on the throw alone'}
            p.well_cleanse_plan=None
            return None
        obj=next((o for o in state.get('objects',[]) if o['cell']==plan['cell'] and o.get('top_item')
                  and base_name(o['top_item'])==plan['name']),None)
        tile=p.tiles.get(plan['cell'],{})
        if obj and tile.get('visible') and not tile.get('trap') and not tile.get('plant') \
                and (healing_water(tile) or not p.effects_block_movement(tile)):
            return p.cell(plan['cell'],'well: retrieve deliberately cleansed spare; verify carried curse state')
        p.well_cleanse_plan=None
        p.log_continuation_error(state,'well-cleanse-unverified','Thrown equipment not observed at well; no guessed recovery or retry',dict(plan))
        return None
    hero=state['hero'];buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    # The item consumes the well. Preserve it for immediate healing, food and
    # equipped curses; do not bind overweight equipment just to cleanse it.
    if hero['hp']<.85*hero['max_hp'] or any(t in buffs for t in ('hungry','starving','blind')) \
            or any(i.get('equipped') and known_cursed(i) for i in state['inventory']):return None
    items=[i for i in state['inventory'] if known_cursed(i) and not i.get('equipped')
           and 'THROW' in i.get('actions',[]) and (stats(i) or accessory_kind(i))
           and sum(base_name(j)==base_name(i) for j in state['inventory'])==1]
    pos=hero['cell'];w,h=state['map']['width'],state['map']['height'];paths=p.paths(state)
    for cell,tile in p.tiles.items():
        if not tile.get('visible') or not healing_water(tile) or cell in p.loot \
                or cell in p.neutral_actor_cells or tile.get('trap') or tile.get('plant'):continue
        for item in items:
            key=(cell,base_name(item))
            if key in p.well_cleanse_attempts:continue
            banks=[c for c in neighbors(cell,w,h) if c in paths and len(p.route(paths,c))<=16
                   and all(not p.tiles[n].get('trap') and not p.tiles[n].get('plant')
                           and not p.effects_block_movement(p.tiles[n]) for n in p.route(paths,c))]
            if not banks:continue
            bank=min(banks,key=lambda c:len(p.route(paths,c)))
            if bank!=pos:return p.toward(state,bank,'well: approach observed health water to cleanse spare equipment',paths)
            if not p.shot_clear(state,cell):continue
            p.well_cleanse_attempts.add(key)
            p.well_cleanse_plan={'name':base_name(item),'cell':cell,'steps':0}
            return p.use(item,'THROW','well: cleanse known cursed spare in health water regardless of hero strength',target=cell)
    return None
