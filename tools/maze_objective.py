"""Observed single-entrance maze geometry; finish optional work after real prize pickup."""
try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent


def recognize(p,state,chest):
    w,h=state['map']['width'],state['map']['height'];floor={1,2,3,9,11,14,15,19,20,29,30}
    if p.tiles.get(chest,{}).get('terrain') not in floor:return None
    cells={chest};queue=[chest]
    while queue and len(cells)<600:
        c=queue.pop()
        for n in (c-w,c+w,c-1,c+1):
            if 0<=n<w*h and abs(n%w-c%w)+abs(n//w-c//w)==1 \
                    and n not in cells and p.tiles.get(n,{}).get('terrain') in floor:
                cells.add(n);queue.append(n)
    if len(cells)<25 or len(cells)>=600:return None
    left,right=min(c%w for c in cells)-1,max(c%w for c in cells)+1
    top,bottom=min(c//w for c in cells)-1,max(c//w for c in cells)+1
    if not (0<=left<right<w and 0<=top<bottom<h) or min(right-left,bottom-top)<10:return None
    boundary={y*w+x for y in range(top,bottom+1) for x in range(left,right+1)
              if x in {left,right} or y in {top,bottom}}
    doors=[c for c in boundary if p.tiles.get(c,{}).get('terrain') in {5,6}]
    if len(doors)!=1 or any(p.tiles.get(c,{}).get('terrain') not in {4,12} for c in boundary-set(doors)):return None
    interior={y*w+x for y in range(top+1,bottom) for x in range(left+1,right)}
    walls=sum(p.tiles.get(c,{}).get('terrain') in {4,12} for c in interior);turns=0
    for c in cells:
        adjacent=[n for n in (c-w,c+w,c-1,c+1) if n in cells]
        if len(adjacent)==2 and abs(adjacent[0]-adjacent[1]) not in {2,2*w}:turns+=1
    if turns<8 or walls<.2*len(interior):return None
    if any(c in interior and c!=chest and not o.get('for_sale') for c,o in p.loot.items()):return None
    return {'cells':sorted(interior),'door':doors[0],'reward':chest,'complete':False}


def observe_open(p,before,decision):
    if not getattr(p,'unit_strategies_enabled',False) or decision.action.get('type')!='cell':return
    cell=decision.action.get('cell')
    obj=next((o for o in before.get('objects',[]) if o['cell']==cell and o['name'].lower()=='chest'
              and not o.get('for_sale')),None)
    if obj and cell not in p.maze_goals:
        goal=recognize(p,before,cell)
        if goal:p.maze_goals[cell]=goal


def collected(p,cell):
    goal=p.maze_goals.get(cell)
    if not goal:return
    goal['complete']=True;p.completed_maze_cells.update(goal['cells'])
    if p.secret_search_goal and p.secret_search_goal['cell'] in p.completed_maze_cells:p.secret_search_goal=None
    if p.exploration_goal and p.exploration_goal['cell'] in p.completed_maze_cells:p.exploration_goal=None
    p.planner.report['maze_objective']={'reward_cell':cell,'reward_collected':True,
        'optional_exploration_finished':True,'qualification':'Pickup receipt only; unexplored maze cells are not claimed visited or cleared'}


def leave(p,state,enemies):
    if enemies or p.recent_threats or state.get('danger_cells'):return None
    pos=state['hero']['cell']
    for goal in p.maze_goals.values():
        if goal['complete'] and pos in goal['cells']:
            paths=p.paths(state);door=goal['door']
            if door in paths:return p.toward(state,door,'room: leave maze after confirmed treasure pickup; no further maze search',paths,intent=Intent.REPOSITION)
    return None
