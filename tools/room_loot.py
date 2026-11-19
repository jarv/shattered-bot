"""Quiet-room observed loot: exact small tours, explicit heuristic large tours."""
from collections import deque
try:
    from .policy_decision import Intent
    from .mimic_tactics import suspicious_container
    from .policy_geometry import neighbors
    from .loot_route import shortest_tour,nearest_tour,TourTooLarge
except ImportError:
    from policy_decision import Intent
    from mimic_tactics import suspicious_container
    from policy_geometry import neighbors
    from loot_route import shortest_tour,nearest_tour,TourTooLarge

def local_loot(p,state,region,paths):
    try:
        from .inventory_tactics import discarded
    except ImportError:
        from inventory_tactics import discarded
    return [c for c,o in p.loot.items() if c in region and c in paths
            and not discarded(p,c,o)
            and (o.get('top_item') or o['name'].lower()=='chest'
                 or o['name'].lower()=='locked chest' and p.keys.get('golden',0)>0)
            and not o.get('for_sale') and not suspicious_container(o)
            and c not in p.combat_deferred_loot
            and p.room_loot_deferred.get(c)!=inventory_context(state)
            and all(n in region for n in p.route(paths,c))]


def room_region(p,state):
    pos,width,height=state["hero"]["cell"],state["map"]["width"],state["map"]["height"]
    if p.tiles[pos]["terrain"] in {5,6}:
        return set()
    region={pos}
    queue=[pos]
    for cell in queue:
        for n in neighbors(cell,width,height):
            if n not in region \
                    and p.tiles.get(n,{}).get("terrain") in {1,2,3,9,11,14,15,19,20,29,30} \
                    and p.walkable(n) and not p.tiles[n].get('plant') and not p.loot.get(n,{}).get('for_sale'):
                region.add(n)
                queue.append(n)
    return region


def room_paths(p,state,region):
    start=state['hero']['cell'];paths={start:None};queue=deque([start])
    while queue:
        cell=queue.popleft()
        if cell!=start and 'chest' in p.loot.get(cell,{}).get('name','').lower():continue
        for n in neighbors(cell,state['map']['width'],state['map']['height']):
            if n in region and n not in paths and p.walkable(n) and not p.tiles[n].get('plant'):
                paths[n]=cell;queue.append(n)
    return paths


def before_room_exit(p,state,decision):
    if decision.reason.startswith('artifact: deliberate reobserved pickup'):return None
    if decision.reason.startswith('loot: prioritize observed permanent upgrade/strength resource'):return None
    if decision.intent not in {Intent.LOOT,Intent.EXPLORE,Intent.DESCEND}:return None
    step=decision.action.get('cell');plan=p.room_loot_plan
    if not plan and not getattr(p,'strict_observed_loot',False) \
            and p.tiles.get(step,{}).get('terrain') not in {5,6,8,22}:return None
    region=room_region(p,state)
    if not region or any(e['cell'] in region for e in p.recent_threats.values()):return None
    paths=room_paths(p,state,region)
    targets=local_loot(p,state,region,paths)
    if not targets:
        p.room_loot_plan=None
        return None
    signature=tuple(sorted(region))
    if not plan or set(targets)!=set(plan['order']) or plan.get('geometry')!=signature:
        end=plan.get('exit') if plan else step if p.tiles.get(step,{}).get('terrain') in {5,6,8,22} else None
        tour=plan_tour(p,state,region,targets,end)
        if not tour:return None
        order,cost=tour
        spent=plan['steps'] if plan else 0
        budget=plan.get('budget',32) if plan else max(32,2*cost+2*len(order))
        plan=p.room_loot_plan={'target':order[0],'region':region,'steps':spent,'order':order,
                              'cost':cost,'exit':end,'budget':budget,'geometry':signature}
    target=plan['target']
    if target not in paths:p.stop_tactical('room-loot-stall','Pickup route no longer admitted; room remains unfinished')
    if plan['steps']>=plan['budget']:p.stop_tactical('room-loot-stall','Room loot tour exhausted bounded interaction budget')
    plan['steps']+=1
    return p.toward(state,target,'loot: finish shortest observed-room collection tour',paths,intent=Intent.LOOT)


def plan_tour(p,state,region,targets,exit_cell=None):
    if not targets:return None
    safe={c for c in region if p.walkable(c) and not p.tiles[c].get('plant')
          and not p.loot.get(c,{}).get('for_sale')}
    method='exact Held–Karp over observed safe BFS distances'
    try:
        tour=shortest_tour(state['hero']['cell'],targets,safe,state['map']['width'],
                           state['map']['height'],exit_cell)
    except TourTooLarge as error:
        tour=nearest_tour(state['hero']['cell'],targets,safe,state['map']['width'],state['map']['height'],exit_cell)
        method='nearest-pickup heuristic over observed safe BFS distances; NOT optimal'
    if tour:
        # If an optimal leg crosses another pickup/chest, collect it first.
        # Its prefix has the same optimal travel cost and avoids trying to walk
        # through a closed chest as though it were ordinary ground.
        start=state['hero']['cell'];paths={start:None};queue=deque([start])
        while queue and tour[0][0] not in paths:
            cell=queue.popleft()
            for n in neighbors(cell,state['map']['width'],state['map']['height']):
                if n in safe and n not in paths:paths[n]=cell;queue.append(n)
        if tour[0][0] in paths:
            first=next(c for c in p.route(paths,tour[0][0]) if c in targets)
            order=[first]+[c for c in tour[0] if c!=first]
            tour=(order,tour[1])
        p.planner.report['room_loot_route']={'order':tour[0],'movement_cost':tour[1],
            'method':method,'exit':exit_cell,
            'qualification':'Replan on pickups/new loot/terrain; no unseen items or room IDs'}
    return tour


def inventory_context(state):
    return tuple(sorted((i["name"],i.get("quantity",1)) for i in state["inventory"]))
