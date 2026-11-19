"""Budgeted observed seed setup/control; no assumed trigger, hit, or private mob state."""
try:
    from .policy_geometry import distance,neighbors
    from .challenge_combat import reach
    from .consumable_tactics import base_name
except ImportError:
    from policy_geometry import distance,neighbors
    from challenge_combat import reach
    from consumable_tactics import base_name


GROUND={1,2,3,5,6,11,14,15,19,20,29}
SELF_BUFFS={'earthroot':('herbal armor',),'swiftthistle':('time bubble',),'starflower':('blessed','recharging'),
            'sungrass':('herbal healing',)}


def turn(state):return state.get('evaluation_stats',{}).get('elapsed_turns',0)


def count(state,kind):
    return sum(i.get('quantity',1) for i in state.get('inventory',[]) if base_name(i)=='seed of '+kind)


def observe(p,before,decision,after):
    pending=p.seed_pending
    if not pending:return None
    if pending['action']=='PLANT':
        expected=decision.action.get('type')=='item' and decision.action.get('id')==pending['id'] and decision.action.get('action')=='PLANT'
    else:
        expected=decision.action=={'type':'cell','cell':pending['cell']} and before.get('status')=='targeting'
    if not expected:return None
    p.seed_pending=None
    if before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0):return None
    spent=count(after,pending['kind'])<count(before,pending['kind'])
    plant=next((t.get('plant','') for t in after.get('map',{}).get('cells',[]) if t['cell']==pending['cell']),'')
    planted=pending['kind'] in plant.lower()
    p.seed_attempts[pending['kind']]+=1
    p.seed_ready_at[pending['kind']]=turn(after)+(4 if pending['action']=='THROW' else 8)
    return {'kind':pending['kind'],'cell':pending['cell'],'seed_consumption_observed':spent,'plant_observed':planted,
            'qualification':'Accepted seed input/public consumption or plant only; no enemy trigger, status, damage or kill inferred'}


def choose(p,state,enemies):
    if p.barren_land:
        p.seed_plan=None
        return None
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):
        return None
    hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    if hero['hp']<.3*hero['max_hp'] and any(base_name(i) in {'potion of healing','waterskin'}
            and 'DRINK' in i.get('actions',[]) and p.item_action_allowed(i,'DRINK') for i in state['inventory']):
        return None  # Quiet rule-preparation runs before the emergency-healing leaf.
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('paral','vertigo','levitat','flying')):return None
    active=[e for e in enemies if not e.get('sleeping')]
    recent=[e for c,e in p.recent_threats.items() if c not in {e['cell'] for e in active}]
    threats=active+recent
    setup_threats=threats+[e for e in enemies if e.get('sleeping') and distance(pos,e['cell'],width)<=3]
    quiet_recovery=not threats and not any(distance(pos,e['cell'],width)<=3 for e in enemies) \
        and not any(distance(pos,e['cell'],width)<=3 for e in p.room_actors.values())
    def speed(e):return 2 if 'fast-movement' in p.unit_strategies.profile(e).capabilities else 1
    def ranged(e):return bool({'ranged-attacks','ranged-pull'} & set(p.unit_strategies.profile(e).capabilities))
    def time_for(inputs):
        return all(distance(pos,e['cell'],width)>reach(e)+inputs*speed(e)
                   and (not ranged(e) or not p.enemy_can_see(state,e,pos) and p.ranged_plan
                        and p.ranged_plan.get('mode')=='cover' and p.ranged_plan.get('goal')==pos) for e in setup_threats)
    def plantable(cell):
        t=p.tiles.get(cell,{})
        return t.get('visible') and t.get('terrain') in GROUND and not t.get('plant') and not t.get('trap') \
            and not p.effects_block_movement(t) and cell not in p.room_blocked and cell not in state.get('danger_cells',[])
    def seed(kind,action):
        return next((i for i in state['inventory'] if base_name(i)=='seed of '+kind and action in i.get('actions',[])
                      and not i.get('known_cursed') and p.item_action_allowed(i,action)),None)
    def available(kind):
        offense=kind not in SELF_BUFFS and kind!='mageroyal'
        return p.seed_attempts[kind]<(3 if offense else 4) and turn(state)>=p.seed_ready_at.get(kind,0) \
            and (not offense or sum(v for k,v in p.seed_attempts.items() if k not in SELF_BUFFS and k!='mageroyal')<6)
    def issue(kind,action,cell):
        item=seed(kind,action)
        if not item or not available(kind):return None
        p.seed_pending={'kind':kind,'cell':cell,'id':item['id'],'action':action}
        p.planner.report['seed_strategy']={'kind':kind,'action':action,'cell':cell,
            'timing':'Observed public reach/speed margin checked','qualification':'No guaranteed activation, enemy path, status or kill'}
        if action=='PLANT':
            p.seed_plan={'kind':kind,'cell':pos,'stage':'activate','waits':0,'before_buffs':buffs}
            return p.use(item,action,'seed: prepare '+kind+' with verified setup time margin')
        return p.use(item,action,'seed: '+kind+' on observed enemy approach; trigger not assumed',target=cell)
    plan=p.seed_plan
    if plan:
        kind=plan['kind']
        if plan['cell']!=pos:p.seed_plan=None
        elif plan['stage']=='activate':
            if kind in p.tiles[pos].get('plant','').lower() and time_for(1):
                plan['stage']='confirm'
                return p.cell(pos,'seed: activate observed '+kind+'; verify actual effect')
            p.seed_plan=None
        elif plan['stage']=='confirm':
            if kind=='sungrass' and 'herbal healing' in buffs:
                plan.update(stage='recover',heal_hp=hero['hp'],heal_progress_at=turn(state))
            else:
                p.planner.report['seed_activation']={'kind':kind,'observed_buff':any(b in buffs for b in SELF_BUFFS.get(kind,())),
                                                   'conditions_absent_after_cleansing':kind=='mageroyal' and not any(b in buffs for b in ('poison','bleed','weak','blind')),
                                                   'qualification':'No buff is inferred from merely planting/trampling'}
                p.seed_plan=None
        if p.seed_plan and plan['stage']=='recover':
            if hero['hp']>plan.get('heal_hp',hero['hp']):
                plan.update(heal_hp=hero['hp'],heal_progress_at=turn(state))
            stalled=turn(state)-plan.get('heal_progress_at',turn(state))>6
            if quiet_recovery and 'herbal healing' in buffs and 'starving' not in buffs \
                    and not any(b in buffs for b in ('burn','poison','bleed','ooze','blind')) and not stalled \
                    and ('hungry' not in buffs or p.food_items(state)) and hero['hp']<.95*hero['max_hp'] and plan['waits']<80:
                plan['waits']+=1
                return p.decision({'type':'wait'},'seed: sheltered sungrass recovery')
            p.seed_plan=None
    hp=hero['hp']/max(1,hero['max_hp'])
    if plantable(pos) and time_for(2):
        if any(b in buffs for b in ('poison','bleed','weak','blind')):
            a=issue('mageroyal','PLANT',pos)
            if a:return a
        if quiet_recovery and hp<.8 and 'herbal healing' not in buffs and 'starving' not in buffs \
                and ('hungry' not in buffs or p.food_items(state)):
            a=issue('sungrass','PLANT',pos)
            if a:return a
        if active and not recent and not any(b in buffs for b in ('burn','poison','bleed','blind','starving')):
            if hp<.65 and not any(b in buffs for b in ('time bubble','time freeze')):
                a=issue('swiftthistle','PLANT',pos)
                if a:return a
            narrow=sum(p.walkable(n) for n in neighbors(pos,width,height))<=3
            if .35<=hp<.8 and narrow and 'herbal armor' not in buffs:
                a=issue('earthroot','PLANT',pos)
                if a:return a
            if (hp<.85 or not p.charged_magic(state)) and hp>=.5 and not any(b in buffs for b in ('blessed','recharging')):
                a=issue('starflower','PLANT',pos)
                if a:return a
    if not active or recent or not time_for(1) or 'blind' in buffs:return None
    occupied={o['cell'] for o in state.get('objects',[]) if not o.get('top_item')}
    targets=[e for e in active if p.unit_strategies.profile(e).triggers_ground_plants
             and not p.unit_strategies.profile(e).strategy.startswith(('boss:','quest:'))
             and 'champion' not in e.get('description','').lower()]
    targets.sort(key=lambda e:distance(pos,e['cell'],width))
    for enemy in targets:
        gap=distance(pos,enemy['cell'],width)
        if gap>6:continue
        bar=enemy.get('health_bar')
        if bar and bar[1]>0 and bar[0]/bar[1]<.3:continue
        need_control=hp<.65 or len(active)>1 or speed(enemy)>1 or not p.charged_magic(state)
        if not need_control:continue
        cells=[c for c,t in p.tiles.items() if 1<=distance(pos,c,width)<=3 and c not in occupied and c not in p.loot
               and plantable(c) and p.walkable(c) and p.shot_clear(state,c) and distance(c,enemy['cell'],width)<gap]
        if not cells:continue
        poison_immune=enemy['name'].lower()=='prison guard' or any(t in enemy['name'].lower() for t in ('skeleton','ghost','wraith','golem','dm-','statue'))
        kinds=['blindweed','stormvine'] if hp<.65 or len(active)>1 or poison_immune else ['sorrowmoss','blindweed','stormvine']
        if not poison_immune and 'sorrowmoss' not in kinds:kinds.append('sorrowmoss')
        kinds+=['icecap','firebloom']
        for kind in kinds:
            if not seed(kind,'THROW') or not available(kind):continue
            choices=[]
            for cell in cells:
                radius=2 if kind=='firebloom' else 1
                if kind in {'icecap','firebloom'}:
                    if distance(pos,cell,width)<=radius:continue
                    area={y*width+x for y in range(max(0,cell//width-radius),min(height,cell//width+radius+1))
                          for x in range(max(0,cell%width-radius),min(width,cell%width+radius+1))}
                    if any(c not in p.tiles or not p.tiles[c].get('visible') or c in p.loot or p.tiles[c].get('plant')
                           or p.tiles[c].get('trap') or p.tiles[c].get('effects') for c in area):continue
                    if any(o['cell'] in area and o['cell'] not in {e['cell'] for e in active} for o in state.get('objects',[])):continue
                    if kind=='firebloom' and any(p.tiles[c]['terrain'] not in {1,3,4,9,11,12,14,19,20,24,25,26,28} for c in area):continue
                choices.append((sum(p.walkable(n) for n in neighbors(cell,width,height)),distance(cell,enemy['cell'],width),cell))
            if choices:
                return issue(kind,'THROW',min(choices)[-1])
    return None
