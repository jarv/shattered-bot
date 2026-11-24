"""Observed full-stack DROP, remote freezing and inventory-backed food return."""
try:
    from .consumable_tactics import base_name
    from .environment_tactics import payload,cold_trigger_safe
    from .policy_decision import Intent
    from .policy_geometry import distance,neighbors
except ImportError:
    from consumable_tactics import base_name
    from environment_tactics import payload,cold_trigger_safe
    from policy_decision import Intent
    from policy_geometry import distance,neighbors


def units(state,name):
    return sum(i.get('quantity',1) for i in state['inventory'] if base_name(i)==name)


def choose(p,state,enemies):
    if enemies or p.recent_threats or state.get('danger_cells'):return None
    if state.get('status')!='ready' or state.get('modal'):return None
    pos=state['hero']['cell'];width,height=state['map']['width'],state['map']['height']
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burning','poison','bleed','root','paral','vertigo')):return None
    plan=p.food_freeze_plan
    raw=next((i for i in state['inventory'] if base_name(i)=='mystery meat'),None)
    ice=next((i for i in state['inventory'] if base_name(i)=='seed of icecap' and 'THROW' in i.get('actions',[])),None)
    weight=payload(state)
    paths=p.paths(state)
    if not plan:
        if not raw or raw.get('quantity',1)<2 or 'DROP' not in raw.get('actions',[]) or not weight \
                or 'starving' in buffs or p.freeze_batches>=2 or p.potion_stash or p.trap_payload_return:return None
        tile=p.tiles[pos]
        if tile['terrain'] not in {1,3,9,11,14,20} or tile.get('plant') or tile.get('trap') or tile.get('effects') or pos in p.loot:return None
        area={pos,*neighbors(pos,width,height)}
        if any(c not in p.tiles or not p.tiles[c].get('visible') or p.tiles[c].get('effects')
               or p.tiles[c].get('plant') or c in p.loot for c in area):return None
        traps=[c for c in area if p.tiles[c].get('trap','').lower()=='chilling trap' and p.tiles[c]['terrain']==18]
        actuator=min(traps) if traps else pos
        kind='trap' if traps else 'seed'
        if kind=='seed' and (not ice or getattr(p,'barren_land',False)):return None
        if any(p.tiles[c].get('trap') and c!=actuator for c in area):return None
        banks=[c for c in paths if 2<=distance(c,pos,width)<=3 and distance(c,actuator,width)>=2
               and len(p.route(paths,c))<=4 and p.shot_clear(dict(state,hero=dict(state['hero'],cell=c)),actuator)
               and all(p.tiles[n]['terrain'] in {1,3,9,11,14,19,20,29} and not p.tiles[n].get('plant')
                       and not p.tiles[n].get('trap') and not p.tiles[n].get('effects') and n not in p.loot
                       for n in p.route(paths,c)[1:])]
        if not banks:return None
        p.freeze_batches+=1
        plan=p.food_freeze_plan={'depth':state['depth'],'cell':pos,'actuator':actuator,'kind':kind,
            'bank':min(banks,key=lambda c:len(p.route(paths,c))),'phase':'verify-drop','steps':0,
            'raw_units':raw.get('quantity',1),'frozen_before':units(state,'frozen carpaccio')}
        return p.use(raw,'DROP','food: drop entire raw-meat stack for one observed freezing batch')
    plan['steps']+=1
    cell=plan['cell'];actuator=plan['actuator']
    if plan['depth']!=state['depth'] or plan['steps']>32:
        p.log_continuation_error(state,'food-freezing-incomplete','Batch freezing did not complete within its floor/budget',dict(plan))
        p.food_freeze_plan=None;return None
    ground=p.loot.get(cell,{}).get('top_item',{})
    if plan['phase']=='verify-drop':
        if raw or not ground or base_name(ground)!='mystery meat' or ground.get('quantity',1)<plan['raw_units']:
            p.log_continuation_error(state,'food-drop-unconfirmed','No inventory/ground confirmation of raw stack DROP',dict(plan))
            p.food_freeze_plan=None;return None
        plan['phase']='leave'
    if plan['phase']=='leave':
        if pos!=plan['bank']:
            return p.toward(state,plan['bank'],'food: leave dropped meat outside the cold radius',paths,intent=Intent.REPOSITION)
        plan['phase']='prepare' if plan['kind']=='seed' else 'activate'
    if plan['phase']=='prepare':
        if not ice or getattr(p,'barren_land',False):plan['phase']='collect'
        else:
            plan['phase']='verify-seed'
            return p.use(ice,'THROW','food: plant observed icecap beside the dropped meat stack',target=actuator)
    if plan['phase']=='verify-seed':
        plan['phase']='activate' if 'icecap' in p.tiles.get(actuator,{}).get('plant','').lower() else 'collect'
    if plan['phase']=='activate':
        valid=distance(pos,actuator,width)>=2 and p.shot_clear(state,actuator)
        if plan['kind']=='trap':valid=valid and cold_trigger_safe(p,state,actuator,distance,neighbors)
        if not valid or not weight:plan['phase']='collect'
        else:
            try:
                from .payload_workflow import throw as throw_payload
            except ImportError:
                from payload_workflow import throw as throw_payload
            action=throw_payload(p,state,weight,actuator,
                'food: remotely trigger cold over the full dropped meat stack',
                disarm_required=plan['kind']=='trap')
            if not action:return None
            plan['phase']='cooling'
            if plan['kind']=='trap':p.trap_attempts.add((state['depth'],actuator))
            return action
    if plan['phase']=='cooling':
        if p.tiles.get(cell,{}).get('effects') or p.tiles.get(cell,{}).get('plant'):
            return p.decision({'type':'wait'},'food: observe cold expiry before recovering the freezing batch')
        plan['phase']='collect'
    if plan['phase']=='collect':
        frozen=max(0,units(state,'frozen carpaccio')-plan['frozen_before'])
        if frozen+units(state,'mystery meat')>=plan['raw_units']:
            p.planner.report['food_freezing']={'returned_frozen_units':frozen,'expected_raw_units':plan['raw_units'],
                'evidence':'inventory-backed return; not inferred from pile disappearance'}
            p.food_freeze_plan=None;return None
        if cell in paths and cell in p.loot and not p.effects_block_movement(p.tiles[cell]):
            return p.toward(state,cell,'food: recover observed processed meat after cold clears',paths,intent=Intent.LOOT)
    return None
