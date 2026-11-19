"""Avoid multiplying fly attackers; reposition using bounded observed routes."""
from collections import deque

try:
    from .challenge_combat import champion, exposure, reach
    from .policy_geometry import distance, neighbors, line_clear
    from .policy_decision import Intent
    from .retreat_geometry import onward_exit
except ImportError:
    from challenge_combat import champion, exposure, reach
    from policy_geometry import distance, neighbors, line_clear
    from policy_decision import Intent
    from retreat_geometry import onward_exit


def flies(enemies):
    return [e for e in enemies if e['name'].lower()=='swarm of flies' and not e.get('sleeping')]


def attackers(state,enemies,cell):
    return sum(distance(cell,e['cell'],state['map']['width'])<=reach(e) for e in flies(enemies))


def narrow(p,state,cell):
    w=state['map']['width'];h=state['map']['height'];x,y=cell%w,cell//w
    def wall(c):return p.tiles.get(c,{}).get('terrain') in {4,12}
    return (0<x<w-1 and wall(cell-1) and wall(cell+1)) or (0<y<h-1 and wall(cell-w) and wall(cell+w))


def behind_choke(p,state,cell,giants):
    pos=state['hero']['cell'];w=state['map']['width'];h=state['map']['height']
    x,y=pos%w,pos//w;nx,ny=cell%w,cell//w
    def wall(c):return p.tiles.get(c,{}).get('terrain') in {4,12}
    return (0<x<w-1 and wall(pos-1) and wall(pos+1)
            and all((e['cell']//w-y)*(ny-y)<0 for e in giants)) or (
        0<y<h-1 and wall(pos-w) and wall(pos+w)
            and all((e['cell']%w-x)*(nx-x)<0 for e in giants))


def physical_attack_unsafe(p,state,target):
    if target['name'].lower()!='swarm of flies':return False
    visible=[o for o in state.get('objects',[]) if o['name'].lower()=='swarm of flies']
    # A surprise-strike shortcut must not create another attacker while an
    # observed usable, known-uncursed damage wand can avoid splitting. Unknown
    # charges remain uncertain and retain the existing empirical cooldown gate.
    non_splitting=any(i.get('curse_known') and not i.get('known_cursed') and 'ZAP' in i.get('actions',[])
        and p.target_allowed(i,target) for i in p.charged_magic(state)) and p.shot_clear(state,target['cell'])
    override=(state['depth'],state['hero']['cell'],target['cell'])
    if getattr(p,'unit_strategies_enabled',False) and p.fly_attack_override==override and not non_splitting:return False
    return non_splitting or champion(target)=='projecting' or attackers(state,visible,state['hero']['cell'])>=2 or (
        champion(target)=='giant' and narrow(p,state,state['hero']['cell']))


def desperate_attack(p,state,enemies):
    """Bounded visible-fragment strikes instead of passive damage under a swarm."""
    if not getattr(p,'unit_strategies_enabled',False) or getattr(p,'stop_on_no_safe_action',False) \
            or state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):return None
    pos=state['hero']['cell'];width=state['map']['width']
    targets=[e for e in flies(enemies) if distance(pos,e['cell'],width)==1]
    if not targets:return None
    def fraction(e):
        bar=e.get('health_bar');return bar[0]/bar[1] if bar and bar[1]>0 else 1
    targets.sort(key=fraction)
    for target in targets:
        magic=p.best_attack(state,target,allowed_kinds={'magic'})
        if magic:return magic
    if len(targets)==1 and not physical_attack_unsafe(p,state,targets[0]):
        return None  # Ordinary single-fly melee is already admitted; do not kite it just to recharge.
    escaped=escape(p,state,enemies,list(p.recent_threats.values())) or p.retreat(state,enemies)
    current=exposure(p,state,enemies,pos,distance,line_clear)['exposure']
    if escaped and (p.fly_escape_plan or exposure(p,state,enemies,escaped.action.get('cell',pos),distance,line_clear)['exposure']<current):return escaped
    if sum(p.fly_fallback_attempts.values())>=12:return None
    for target in targets:
        bar=tuple(target.get('health_bar') or ())
        key=(pos,target['cell'],bar)
        if p.fly_fallback_attempts[key]>=3:continue
        p.fly_attack_override=(state['depth'],pos,target['cell'])
        try:attack=p.best_attack(state,target,allowed_kinds={'melee'})
        finally:p.fly_attack_override=None
        if attack:
            p.fly_fallback_pending={'depth':state['depth'],'branch':state.get('branch',0),'from':pos,
                'target':target['cell'],'bar':bar,'key':key}
            p.log_continuation_error(state,'fly-physical-last-resort',
                'No admitted non-splitting attack or pressure-reducing retreat; attempt a visible fly fragment instead of passive recharge waiting',
                {'target':target['cell'],'visible_health_bar':bar,'qualification':'Melee can miss or split; not a guaranteed kill or true HP estimate'})
            attack.reason='combat: bounded last-resort strike on visible fly fragment; splitting risk accepted'
            return attack
    return None


def observe_fallback(p,before,decision,after):
    plan=p.fly_fallback_pending;p.fly_fallback_pending=None
    if not plan or decision.action!={'type':'cell','cell':plan['target']}:return None
    if before.get('depth')!=plan['depth'] or before.get('branch',0)!=plan['branch'] \
            or before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0):return None
    if before['hero']['cell']!=plan['from'] or after['hero']['cell']!=plan['from'] \
            or not any(e['cell']==plan['target'] for e in flies(before.get('objects',[]))):return None
    p.fly_fallback_attempts[plan['key']]+=1
    return {'target':plan['target'],'visible_health_bar':plan['bar'],'accepted_attempts':p.fly_fallback_attempts[plan['key']],
            'evidence':'Accepted attack attempt at a publicly observed fly cell; no kill or damage inferred'}


def defer_threatened_loot(p,state,threats):
    fly_threats=flies(threats)
    if not fly_threats:return
    pending=[]
    for cell,obj in p.loot.items():
        name=obj['name'].lower()
        optional='chest' in name or name=='gold' or name.startswith('gold x')
        if optional and not obj.get('for_sale') and cell not in p.combat_deferred_loot and any(
                distance(cell,e['cell'],state['map']['width'])<=reach(e)+1 for e in fly_threats):
            p.combat_deferred_loot.add(cell)
            pending.append({'kind':'combat-deferred optional loot','cell':cell,'name':obj['name']})
    if pending:
        p.defer_obligations(state,pending,'Observed fly pressure; do not reopen optional loot on visibility or resource flicker')
        if p.exploration_goal and p.exploration_goal['kind']=='loot' and p.exploration_goal['cell'] in p.combat_deferred_loot:
            p.exploration_goal=None
        if p.room_loot_plan and p.room_loot_plan['target'] in p.combat_deferred_loot:p.room_loot_plan=None
        if p.planner.goal and p.planner.goal.kind=='loot' and p.planner.goal.target in p.combat_deferred_loot:
            p.planner.goal=None


def escape(p,state,enemies,remembered=()):
    """Accept reduced first-step pressure only with a short zero-exposure endpoint.

    All exposure is from currently visible positions and remembered observations,
    not a prediction that enemies will stay still or that the route is harmless.
    """
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('root','paral','vertigo','burning','poison','bleed','ooze')):return None
    if p.room_journey or p.drop_plan or p.puzzle_probe:return None
    active=[e for e in enemies if not e.get('sleeping')]
    if state.get('boss_health_text') or any(e['name'].lower() in p.boss_strategies or 'fist' in e['name'].lower() for e in active):return None
    pos=state['hero']['cell'];w=state['map']['width'];h=state['map']['height']
    plan=p.fly_escape_plan
    if plan and (plan['depth']!=state['depth'] or plan['target']==pos or plan['steps']>=3):
        p.fly_escape_plan=plan=None
    threats={(e['cell'],e['name']):e for e in [*remembered,*(plan['threats'] if plan else []),*active]}
    threats=list(threats.values())
    current=exposure(p,state,threats,pos,distance,line_clear)
    fly_count=attackers(state,active,pos)
    single_giant_choke=fly_count==1 and narrow(p,state,pos) and any(
        champion(e)=='giant' and distance(pos,e['cell'],w)<=reach(e) for e in flies(active))
    projecting=[e for e in flies(active) if champion(e)=='projecting' and distance(pos,e['cell'],w)<=reach(e)]
    if not plan and fly_count<2 and not single_giant_choke and not projecting:return None
    occupied={e['cell'] for e in threats}
    def allowed(cell):
        return p.walkable(cell,occupied) and p.tiles[cell]['terrain'] not in {5,7,8,10,21,22,31,37,38} \
            and not p.tiles[cell].get('plant') and cell not in p.loot
    limit=3-plan['steps'] if plan else 3
    queue=deque([[pos]])
    seen={pos}
    candidates=[]
    while queue:
        route=queue.popleft()
        if len(route)>1:
            end=route[-1]
            risk=exposure(p,state,threats,end,distance,line_clear)
            previous_risk=exposure(p,state,threats,route[-2],distance,line_clear)
            if risk['exposure']>previous_risk['exposure'] or risk['ranged']>previous_risk['ranged']:continue
            first=route[1]
            first_risk=exposure(p,state,threats,first,distance,line_clear)
            first_flies=attackers(state,active,first)
            if fly_count>=2 and all(not champion(e) for e in flies(active)) \
                    and not onward_exit(p,state,first,pos,occupied,threats):
                continue  # Special fly escape must not bypass ordinary anti-pocket admission.
            giants=[e for e in flies(active) if champion(e)=='giant' and distance(pos,e['cell'],w)<=reach(e)]
            # Range four can require several steps before the attacker count
            # changes. Equal exposure is permitted only moving farther from
            # every currently reaching projecting fly, with a bounded exit.
            projecting_gap=bool(projecting) and all(distance(first,e['cell'],w)>distance(pos,e['cell'],w) for e in projecting)
            progress=bool(plan) or first_flies<fly_count or single_giant_choke and behind_choke(p,state,first,giants) or projecting_gap
            if risk['exposure']==0 and progress and (not plan or end==plan['target']):
                candidates.append(((first_risk['exposure'],first_flies,len(route),sum(p.visits[c] for c in route[1:]),end),route))
        if len(route)-1>=limit:continue
        for cell in neighbors(route[-1],w,h):
            if cell not in seen and allowed(cell):
                seen.add(cell)
                queue.append(route+[cell])
    if not candidates:
        if plan:
            p.fly_escape_plan=None
            p.planner.report['fly_pressure']={'status':'bounded escape invalidated; re-evaluate ordinary safety'}
        return None
    _,route=min(candidates,key=lambda option:option[0])
    first=route[1]
    if not plan:
        plan=p.fly_escape_plan={'depth':state['depth'],'target':route[-1],'threats':threats,'steps':0}
    plan['steps']+=1
    defer_threatened_loot(p,state,threats)
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    p.planner.report['fly_pressure']={'status':'bounded pressure-reducing retreat','route':route,
        'visible_attackers_before':fly_count,'visible_attackers_next':attackers(state,active,first),
        'exposure_before':current['exposure'],
        'exposure_next':exposure(p,state,threats,first,distance,line_clear)['exposure'],
         'endpoint_exposure':0,'caveat':'observed-position route; enemies may act; no survival guarantee'}
    return p.cell(first,'combat: reduce fly pressure toward a known unexposed endpoint',intent=Intent.RETREAT)
