"""Persistent region-local work over observed terrain; no generated room data."""
from collections import Counter, deque

try:
    from .policy_decision import Intent
    from .policy_geometry import neighbors,distance,navigation_terrain
    from .mimic_tactics import suspicious_container
    from .room_loot import inventory_context
except ImportError:
    from policy_decision import Intent
    from policy_geometry import neighbors,distance,navigation_terrain
    from mimic_tactics import suspicious_container
    from room_loot import inventory_context


PORTALS={5,6,10,21,31,38}


def regions(tiles,cells,width,height):
    """Rebuild components as visibility grows. IDs are temporary local anchors."""
    remaining={c for c in cells if tiles[c]['terrain'] not in PORTALS|{7,8,22,37}}
    owner={}
    groups={}
    while remaining:
        anchor=min(remaining)
        group={anchor}
        remaining.remove(anchor)
        queue=deque([anchor])
        while queue:
            for n in neighbors(queue.popleft(),width,height):
                if n in remaining:
                    remaining.remove(n)
                    group.add(n)
                    queue.append(n)
        groups[anchor]=group
        owner.update((c,anchor) for c in group)
    return owner,groups


def context(p,state):
    # HP, visibility flicker and passive recharge must not resurrect a stalled goal.
    return (tuple(sorted((c,navigation_terrain(t['terrain']),t.get('trap'),tuple(t.get('effects',[]))) for c,t in p.tiles.items())),
            inventory_context(state),tuple(sorted(p.keys.items())),tuple(sorted(p.blocked)))


def safe_paths(p,state,paths):
    start=state['hero']['cell']
    forbidden=p.navigation_barriers(state,Intent.EXPLORE)
    previous={start:None}
    queue=deque([start])
    while queue:
        cell=queue.popleft()
        for n in neighbors(cell,state['map']['width'],state['map']['height']):
            if n in paths and n not in previous and n not in forbidden:
                previous[n]=cell
                queue.append(n)
    # Fresh adjacent stair piles are leaf pickup destinations, not transit.
    loot_barriers=p.navigation_barriers(state,Intent.LOOT)
    for n in neighbors(start,state['map']['width'],state['map']['height']):
        if n in paths and n not in loot_barriers and p.tiles[n]['terrain'] in {7,8,22,37}:
            previous[n]=start
    return previous


def decline_goal(p,state,reason):
    goal=p.exploration_goal
    if not goal:return
    p.exploration_declined[(goal['kind'],goal['cell'])]=context(p,state)
    if goal['kind']=='loot':
        p.room_loot_deferred[goal['cell']]=inventory_context(state)
        if p.room_loot_plan and p.room_loot_plan['target']==goal['cell']:
            p.room_loot_plan=None
    p.defer_obligations(state,[{'kind':'routing-stalled '+goal['kind'],'cell':goal['cell']}],reason)
    p.exploration_goal=None


def accepted_navigation(p,state,decision,after):
    """Account only for accepted inputs, not proposals overridden by other tactics."""
    goal=p.exploration_goal
    if goal:
        proposed=goal.pop('proposed',None)
        actual=(state.get('depth'),state.get('hero',{}).get('cell'),decision.action.get('cell'))
        if proposed==actual and decision.action.get('type')=='cell' and decision.intent in {Intent.EXPLORE,Intent.LOOT}:
            try:
                from .movement_batching import confirmed_path
            except ImportError:
                from movement_batching import confirmed_path
            path=confirmed_path(state,decision,after) if decision.movement_batch else None
            if path is not None:
                goal['steps']+=len(path)-1
                for edge in zip(path,path[1:]):goal['edges'][edge]+=1
            else:
                goal['steps']+=1
                if not decision.movement_batch:goal['edges'][(actual[1],actual[2])]+=1
    before_hero,after_hero=state.get('hero',{}),after.get('hero',{})
    if decision.navigation and state.get('depth')==after.get('depth') and before_hero and after_hero:
        return {'depth':state['depth'],'from':before_hero['cell'],'to':after_hero['cell'],
                'moved':before_hero['cell']!=after_hero['cell'],'intent':decision.intent,
                'goal':{'kind':goal['kind'],'cell':goal['cell']} if goal else None}
    return None


def choose(p,state,paths,skipped):
    try:
        from .survival_policy import DOOR_KEYS,TRANSITIONS,AVOID_CONTAINERS
    except ImportError:
        from survival_policy import DOOR_KEYS,TRANSITIONS,AVOID_CONTAINERS
    paths=safe_paths(p,state,paths)
    pos=state['hero']['cell']
    width,height=state['map']['width'],state['map']['height']
    owner,groups=regions(p.tiles,paths,width,height)
    here=owner.get(pos)
    # A hero standing in a door still belongs to its most recent observed side.
    if here is None:here=owner.get(p.region_entry_anchor)
    signature=context(p,state)
    tasks={}
    def add(cell,kind,intent,reason,priority):
        if cell not in paths or cell in skipped or cell in p.blocked:return
        if p.exploration_declined.get((kind,cell))==signature:return
        tasks[(kind,cell)]={'cell':cell,'kind':kind,'intent':intent,'reason':reason,'priority':priority}
    for cell,obj in p.loot.items():
        name=obj['name'].lower()
        if p.tiles.get(cell,{}).get('terrain') in TRANSITIONS and not obj.get('for_sale') \
                and obj.get('top_item') and not suspicious_container(obj):
            # A fresh visible heap receives the ordinary pickup interaction before
            # a level transition. Never click a remembered/empty staircase or use
            # it as transit; first reobserve from a reachable ordinary neighbour.
            fresh=any(o.get('cell')==cell and o.get('top_item') and not o.get('for_sale')
                      for o in state.get('objects',[])) and p.tiles[cell].get('visible')
            banks=[n for n in neighbors(cell,width,height) if n in paths
                   and p.tiles[n]['terrain'] not in TRANSITIONS|PORTALS
                   and p.exploration_loot_allowed(state,n,paths)]
            if fresh and pos in banks and cell in paths and p.exploration_loot_allowed(state,cell,paths):
                add(cell,'loot',Intent.LOOT,'loot: collect freshly visible pile on stairs without transitioning',1)
            elif banks and pos not in banks:
                bank=min(banks,key=lambda n:(len(p.route(paths,n)),n))
                add(bank,'reobserve-loot',Intent.EXPLORE,'loot: reobserve stair pile from safe adjacent ground',1)
            continue
        if cell not in paths or cell in skipped or cell in p.blocked or obj.get('for_sale') \
                or p.tiles[cell]['terrain'] in TRANSITIONS or suspicious_container(obj):continue
        if any(word in name for word in AVOID_CONTAINERS) and cell not in p.allowed_chests:continue
        if 'locked chest' in name and not p.keys.get('golden',0):continue
        if not p.exploration_loot_allowed(state,cell,paths):continue
        if p.room_loot_deferred.get(cell)==inventory_context(state):continue
        key='key' in name
        add(cell,'loot',Intent.LOOT,'loot: collect key' if key else 'loot: collect/open',0 if key else 1)
    for cell in p.allowed_chests:
        if cell in p.loot and not suspicious_container(p.loot[cell]) and not p.loot[cell].get('for_sale') \
                and p.room_loot_deferred.get(cell)!=inventory_context(state) \
                and p.exploration_loot_allowed(state,cell,paths):
            add(cell,'loot',Intent.LOOT,'loot: spend matching key on useful chest',1)
    for cell,tile in p.tiles.items():
        key=DOOR_KEYS.get(tile['terrain'])
        if key and cell not in p.optional_locks and p.keys.get(key,0)>0:
            add(cell,'door',Intent.EXPLORE,f'explore: unlock {key} door',3)
    report=p.exploration_report(state,paths)
    for cell in report['unexplored_frontiers']:
        add(cell,'frontier',Intent.EXPLORE,'explore: frontier',2)
    for cell in report['unopened_doors']:
        add(cell,'door',Intent.EXPLORE,'explore: unopened door',3)
    def region(task):
        cell=task['cell']
        if cell in owner:return owner[cell]
        sides={owner[n] for n in neighbors(cell,width,height) if n in owner}
        return here if here in sides else min(sides,default=None)
    counts=Counter(region(t) for t in tasks.values())
    previous=p.exploration_goal
    selected=tasks.get((previous['kind'],previous['cell'])) if previous else None
    change='continue committed target'
    # A visible pickup just across one ordinary door is concrete nearby work,
    # not a distant branch reward. Do not finish a whole region's speculative
    # frontiers first merely because the door splits the local component.
    adjacent=[]
    if (not selected or selected['kind']!='loot') and not any(
            t['kind']=='loot' and region(t)==here for t in tasks.values()):
        try:
            from .challenge_combat import reach
        except ImportError:
            from challenge_combat import reach
        for task in tasks.values():
            if task['kind']!='loot':continue
            obj=p.loot.get(task['cell'],{})
            concrete_supply=obj.get('top_item') and any(word in obj['name'].lower() for word in ('torch','scroll'))
            if not p.tiles[task['cell']].get('visible') and not concrete_supply:continue
            route=p.route(paths,task['cell'])
            portals=[c for c in route[1:] if p.tiles[c]['terrain'] in PORTALS]
            if len(route)>7 or len(portals)>1 or any(p.tiles[c]['terrain'] not in {5,6} for c in portals):continue
            if any(p.tiles[c].get('plant') or any(not e.get('sleeping') and
                    distance(c,e['cell'],width)<=reach(e) for e in p.recent_threats.values()) for c in route[1:]):continue
            adjacent.append(task)
    if adjacent:
        selected=min(adjacent,key=lambda t:(t['priority'],len(p.route(paths,t['cell'])),t['cell']))
        if not previous or previous['kind']!=selected['kind'] or previous['cell']!=selected['cell']:
            p.exploration_goal={'kind':selected['kind'],'cell':selected['cell'],'steps':0,'edges':Counter()}
        change='nearby visible loot before further frontier work'
    if selected is None:
        p.exploration_goal=None
        local=[t for t in tasks.values() if here is not None and region(t)==here]
        # Local work before a remote reward; completed branches have no tasks.
        pool=local or list(tasks.values())
        def cost(t):
            route=p.route(paths,t['cell'])
            crossings=sum(p.tiles[c]['terrain'] in PORTALS for c in route[1:])
            # Among remaining branches prefer fewer portal crossings, then travel.
            # Local pickups/keys precede local viewing positions and onward doors.
            return (t['priority'] if local else crossings,
                    p.frontier_cost(state,paths,t['cell']) if t['kind']=='frontier' else len(route),
                    t['priority'],t['cell'])
        selected=min(pool,key=cost) if pool else None
        change='finish local work' if local else 'next remaining branch'
        if selected:
            p.exploration_goal={'kind':selected['kind'],'cell':selected['cell'],'steps':0,'edges':Counter()}
    summary={'known_regions':len(groups),'regions_with_work':len(counts),'current_region':here,
             'tasks':len(tasks),'selection':change,'target':selected['cell'] if selected else None,
             'kind':selected['kind'] if selected else None}
    p.planner.report['region_navigation']=summary
    if not selected:return None
    goal=p.exploration_goal
    route=p.route(paths,selected['cell'])
    step=route[1] if len(route)>1 else selected['cell']
    if goal['steps']>=max(32,2*len(paths)) or goal['edges'][(pos,step)]>=3:
        p.stop_tactical('systematic-route-stall','Persistent exploration target exceeded bounded route progress')
    action=p.toward(state,selected['cell'],selected['reason'],paths,intent=selected['intent'])
    if not action:
        decline_goal(p,state,'No valid ordinary route to persistent exploration target')
        return None
    goal['proposed']=(state['depth'],pos,step)
    if here is not None:
        old=p.region_entry_anchor
        if old not in groups[here]:
            revisited=any(c in groups[here] for c in p.region_seen_anchors)
            summary['entry']='connector transit to remaining work' if revisited else 'first observed region entry'
            p.region_seen_anchors.add(pos)
        p.region_entry_anchor=pos
    summary['target_region']=region(selected)
    summary['route_steps']=len(route)-1
    summary['steps_on_goal']=goal['steps']
    return action
