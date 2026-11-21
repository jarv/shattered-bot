"""Bounded doorway surprise with a second observed exit, never a pocket-room lure."""
from collections import deque

try:
    from .policy_geometry import neighbors,distance,projectile_line_clear
    from .policy_decision import Intent
    from .consumable_tactics import base_name
except ImportError:
    from policy_geometry import neighbors,distance,projectile_line_clear
    from policy_decision import Intent
    from consumable_tactics import base_name


GROUND={1,2,3,5,6,9,11,14,19,20,29,30}


def clean(p,state,cell,occupied=()):
    tile=p.tiles.get(cell,{})
    return tile.get('terrain') in GROUND and tile.get('observed') is not False \
        and cell not in occupied and cell not in state.get('danger_cells',[]) \
        and cell not in p.loot and not tile.get('trap') and not tile.get('plant') \
        and not p.effects_block_movement(tile) and p.walkable(cell,occupied)


def escape_route(p,state,hide,door,occupied=()):
    """A different door with two onward cells; excluding the ambush door prevents a trap."""
    width,height=state['map']['width'],state['map']['height']
    blocked=set(occupied)|{door}
    if not clean(p,state,hide,blocked):return []
    queue=deque([[hide]]);seen={hide}
    while queue:
        route=queue.popleft();cell=route[-1]
        if len(route)>16:continue
        if cell!=hide and p.tiles[cell]['terrain'] in {5,6}:
            forbidden=blocked|set(route[:-1])
            prior=route[-2]
            def beyond(n):
                return ((n%width-cell%width)*(prior%width-cell%width)
                        +(n//width-cell//width)*(prior//width-cell//width))<0
            onward=[n for n in neighbors(cell,width,height) if clean(p,state,n,forbidden)
                    and p.tiles[n]['terrain'] not in {5,6} and beyond(n)]
            if any(clean(p,state,m,forbidden|{cell,n}) and p.tiles[m]['terrain'] not in {5,6}
                   for n in onward for m in neighbors(n,width,height)):
                return route
        for n in neighbors(cell,width,height):
            if n not in seen and clean(p,state,n,blocked):
                seen.add(n);queue.append(route+[n])
    return []


def cancel(p,reason):
    if p.great_crab_plan:
        p.great_crab_attempts[p.great_crab_plan['door']]+=1
    p.great_crab_plan=None
    p.planner.report['great_crab']={'status':'replan','reason':reason}


def guard_movement(p,state,decision):
    """Shared navigation must not undo the dedicated controller's pocket veto."""
    if p.ghost_quest.get('stage') in {'reward','claiming','collect_dropped','done'}:
        return
    if state.get('status')!='ready' or state.get('modal') or decision.action.get('type')!='cell':
        return
    pos=state['hero']['cell'];step=decision.action.get('cell')
    if step==pos:return
    enemies=[o for o in state.get('objects',[]) if o.get('name','').lower()=='great crab'
             and not o.get('sleeping')]
    remembered=[o for o in p.recent_threats.values() if o.get('name','').lower()=='great crab']
    if not enemies and not remembered and not p.great_crab_plan:return
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    occupied={o['cell'] for o in state.get('objects',[]) if is_hostile(o)}
    if step in occupied:return  # Attack admission, not movement into an empty square.
    occupied.update(o['cell'] for o in remembered)
    if not escape_route(p,state,step,pos,occupied):
        p.stop_tactical('great-crab-pocket','Great crab: reject movement into a confined area without a second observed exit')


def choose(p,state,enemies):
    hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    foe=next((e for e in enemies if e['name'].lower()=='great crab'),None)
    plan=p.great_crab_plan
    if not foe and not plan:return None
    if p.ghost_quest.get('stage') in {'reward','claiming','collect_dropped','done'}:
        p.great_crab_plan=None;return None
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):
        cancel(p,'Not a quiet ready tactical observation');return None
    if foe and (foe.get('sleeping') or 'invisib' in buffs):
        attack=p.best_attack(state,foe)
        if attack:
            p.great_crab_plan=None
            attack.reason='quest: great crab surprise from publicly observed sleep or invisibility'
            return attack
    occupied={e['cell'] for e in enemies}
    other=[e for e in enemies if e is not foe and not e.get('sleeping')]
    if other:
        cancel(p,'Other active enemies preempt the single-crab lure')
        return None
    if plan:
        plan['steps']+=1
        if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0) \
                or plan['steps']>24 or hero['hp']<.5*hero['max_hp'] \
                or plan['start_hp']-hero['hp']>.2*hero['max_hp'] or other \
                or p.tiles.get(plan['door'],{}).get('terrain') not in {5,6} \
                or not escape_route(p,state,plan['hide'],plan['door'],occupied):
            cancel(p,'Doorway, escape route, health, or bounded lure budget changed')
            plan=None
        else:
            door,hide=plan['door'],plan['hide']
            if pos==hide:
                arrived=foe and foe['cell']==door and plan['last_crab']!=door
                # Confirm accepted departure. A currently closed door, or fresh
                # crab entry immediately after that departure, witnesses a new
                # sight break. Merely standing beside an open door does not.
                if p.previous_position==door and plan.get('departing') \
                        and (p.tiles[door]['terrain']==5 or arrived):
                    plan['armed']=True
                if arrived and plan.get('armed'):
                    p.great_crab_attempts[door]+=1
                    p.great_crab_plan=None  # Exactly one strike; never reuse surprise.
                    p.planner.report['great_crab']={'status':'fresh doorway entry strike',
                        'door':door,'hide':hide,'escape_route':escape_route(p,state,hide,door,occupied),
                        'qualification':'One surprise attempt from observed crossing/entry; damage is not assumed'}
                    return p.cell(door,'quest: great crab fresh doorway surprise attack')
                if foe and distance(pos,foe['cell'],width)<=1:
                    cancel(p,'Crab already adjacent without fresh surprise evidence');plan=None
                elif plan.get('armed') and plan['waits']<8:
                    plan['waits']+=1
                    if foe:plan['last_crab']=foe['cell']
                    return p.decision({'type':'wait'},'quest: await great crab at escape-backed doorway',intent=Intent.RECOVER)
                else:
                    cancel(p,'No witnessed sight break or doorway arrival budget exhausted');plan=None
            elif pos==door:
                closed=dict(p.tiles);closed[door]={'terrain':5}
                if foe and clean(p,state,hide,occupied) \
                        and not projectile_line_clear(foe['cell'],hide,width,closed):
                    plan['departing']=True;plan['last_crab']=foe['cell']
                    return p.cell(hide,'quest: close doorway sight line while retaining a second exit',intent=Intent.RETREAT)
                cancel(p,'Cannot hide safely from current public crab position');plan=None
            else:
                paths=p.paths(state,occupied)
                if door in paths:
                    route=p.route(paths,door)
                    if len(route)<=7 and all(clean(p,state,c,occupied) for c in route[1:]) \
                            and not any(foe and distance(c,foe['cell'],width)<=1 for c in route[1:]):
                        return p.toward(state,door,'quest: lure great crab toward known escape-backed doorway',
                                        paths,intent=Intent.RETREAT)
                cancel(p,'Crab blocks the known ambush approach');plan=None
    if not foe:return None  # Never attack a remembered or absent actor.
    if not other and hero['hp']>=.5*hero['max_hp'] and not p.pursuit_lure_exhausted:
        paths=p.paths(state,occupied);options=[]
        for door in paths:
            if p.tiles[door]['terrain'] not in {5,6} or p.great_crab_attempts[door]>=3:continue
            route=p.route(paths,door)
            if len(route)>7 or len(route)-1>distance(door,foe['cell'],width) \
                    or any(not clean(p,state,c,occupied) or distance(c,foe['cell'],width)<=1
                           for c in route[1:]):continue
            closed=dict(p.tiles);closed[door]={'terrain':5}
            for hide in neighbors(door,width,height):
                if p.tiles.get(hide,{}).get('terrain') in {5,6} or not clean(p,state,hide,occupied) \
                        or projectile_line_clear(foe['cell'],hide,width,closed):continue
                escape=escape_route(p,state,hide,door,occupied)
                if escape:options.append((len(route),len(escape),door,hide,escape))
        if options:
            _,_,door,hide,escape=min(options)
            p.great_crab_plan={'depth':state['depth'],'branch':state.get('branch',0),
                'door':door,'hide':hide,'start_hp':hero['hp'],'steps':0,'waits':0,
                'last_crab':foe['cell'],'armed':False}
            p.planner.report['great_crab']={'status':'lure planned','door':door,'hide':hide,
                'escape_route':escape,'qualification':'Observed geometry only; no guaranteed enemy movement'}
            if pos==door:
                p.great_crab_plan['departing']=True
                return p.cell(hide,'quest: close doorway sight line while retaining a second exit',intent=Intent.RETREAT)
            return p.toward(state,door,'quest: lure great crab toward known escape-backed doorway',
                            paths,intent=Intent.RETREAT)
    invisible=next((i for i in state['inventory'] if base_name(i)=='potion of invisibility'
                     and 'DRINK' in i.get('actions',[]) and p.item_action_allowed(i,'DRINK')),None)
    if invisible:
        return p.use(invisible,'DRINK','quest: enable great crab surprise without a confined-room lure')
    moves=[c for c in neighbors(pos,width,height) if clean(p,state,c,occupied)
           and distance(c,foe['cell'],width)>1 and distance(c,foe['cell'],width)>=distance(pos,foe['cell'],width)
           and escape_route(p,state,c,pos,occupied)]
    if moves:
        # Equal separation is not equal escape progress: a less-visited side
        # square can add a step to the very same second-exit route. Prefer the
        # shorter admitted route before exploration novelty, without predicting
        # crab movement or weakening any movement/escape admission.
        target=max(moves,key=lambda c:(distance(c,foe['cell'],width),
                   -len(escape_route(p,state,c,pos,occupied)),-p.visits[c]))
        return p.cell(target,'quest: draw great crab toward known exits, never into a dead-end pocket',intent=Intent.RETREAT)
    p.stop_tactical('quest-combat','Great crab: no fresh surprise or observed escape-backed doorway; refuse blocked attacks and confined-room lure')
