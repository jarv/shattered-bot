"""Bounded observed-position exit before exhausted, low-health snake melee."""
from collections import deque
try:
    from .challenge_combat import champion,exposure
    from .policy_geometry import distance,neighbors,line_clear
    from .policy_decision import Intent
except ImportError:
    from challenge_combat import champion,exposure
    from policy_geometry import distance,neighbors,line_clear
    from policy_decision import Intent


def choose(p,state,enemies,remembered=(),resume_only=False):
    plan=p.boxed_snake_escape
    if resume_only and not plan:return None
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):return None
    hero=state['hero'];pos=hero['cell'];w=state['map']['width'];h=state['map']['height']
    if plan and (plan['depth']!=state['depth'] or pos==plan['target'] or plan['steps']>=3):
        p.boxed_snake_escape=plan=None
        if resume_only:return None
    active=[e for e in enemies if not e.get('sleeping')]
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if p.room_journey or p.drop_plan or p.puzzle_probe or state.get('boss_health_text') \
            or any(t in buffs for t in ('root','paral','vertigo','burning','poison','bleed','ooze')) \
            or any(champion(e) or e['name'].lower() not in {'sewer snake','marsupial rat','albino rat','gnoll scout'} for e in active):
        return None
    if not plan and (p.boxed_snake_escape_uses>=2 or hero['hp']>0.5*hero['max_hp']
            or p.charged_magic(state) or not any(e['name'].lower()=='sewer snake' and distance(pos,e['cell'],w)==1 for e in active)):
        return None
    threats=list({(e['cell'],e['name']):e for e in [*remembered,*(plan['threats'] if plan else []),*active]}.values())
    current=exposure(p,state,threats,pos,distance,line_clear)
    if not current['exposure']:return None
    occupied={e['cell'] for e in threats}
    queue=deque([[pos]]);seen={pos};options=[]
    limit=3-plan['steps'] if plan else 3
    while queue:
        route=queue.popleft();end=route[-1]
        risk=exposure(p,state,threats,end,distance,line_clear)
        if len(route)>1:
            previous=exposure(p,state,threats,route[-2],distance,line_clear)
            if risk['exposure']>previous['exposure'] or risk['ranged']>previous['ranged']:continue
            if risk['exposure']==0 and (not plan or end==plan['target']):
                onward=sum(p.walkable(c,occupied) and c not in route for c in neighbors(end,w,h))
                if onward:options.append(((len(route),-onward,sum(p.visits[c] for c in route),end),route))
        if len(route)-1>=limit:continue
        for c in neighbors(end,w,h):
            if c not in seen and p.walkable(c,occupied) and c not in p.loot \
                    and p.tiles[c]['terrain'] not in {5,7,8,10,21,22,31,37,38} and not p.tiles[c].get('plant'):
                seen.add(c);queue.append(route+[c])
    if not options:
        p.boxed_snake_escape=None
        return None
    _,route=min(options,key=lambda x:x[0])
    if not plan:
        p.boxed_snake_escape_uses+=1
        plan=p.boxed_snake_escape={'depth':state['depth'],'target':route[-1],'steps':0,'threats':threats}
    plan['steps']+=1
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    p.planner.report['boxed_snake_escape']={'route':route,'exposure_before':current['exposure'],
        'exposure_next':exposure(p,state,threats,route[1],distance,line_clear)['exposure'],
        'endpoint_exposure':0,'uses':p.boxed_snake_escape_uses,
        'caveat':'At most three movements/two starts per floor; current observed positions, no survival guarantee'}
    return p.cell(route[1],'recovery: bounded observed escape before exhausted snake melee',intent=Intent.RETREAT)
