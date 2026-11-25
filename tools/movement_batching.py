"""Short native destination clicks with actual movement receipts."""
try:
    from .policy_decision import Intent
    from .policy_geometry import neighbors
    from .combat_items import unencumbered,known_cursed
except ImportError:
    from policy_decision import Intent
    from policy_geometry import neighbors
    from combat_items import unencumbered,known_cursed


MAX_STEPS=6
MIN_STEPS=3
GROUND={1,3,11,14,19,20}
WALLS={4,12}
BENIGN_TRAVEL_BUFFS={'barrier','wands empowered','lingering magic'}


def prepare(p,state,decision):
    simple = getattr(getattr(p, 'profile', None), 'name', None) == 'simple-bot'
    if not getattr(p,'unit_strategies_enabled',False) or 'movement_trace' not in state.get('capabilities',[]) \
            or p.movement_batch_disabled or state.get('status')!='ready' or state.get('modal') \
             or state.get('danger_cells') or decision.intent not in ({Intent.EXPLORE,Intent.LOOT,Intent.DESCEND} if simple else {Intent.EXPLORE,Intent.LOOT}) \
            or decision.action.get('type')!='cell' or p.recent_threats or p.unseen_damage_turns:return decision
    if state.get('evaluation_stats',{}).get('elapsed_turns',0)<p.movement_batch_ready_at:return decision
    route=decision.navigation_route;hero=state['hero'];pos=hero['cell'];w,h=state['map']['width'],state['map']['height']
    if len(route)<MIN_STEPS+1 or route[0]!=pos or route[1]!=decision.action['cell'] \
            or hero['hp']<.8*hero['max_hp'] or not unencumbered(state) \
            or any(i.get('equipped') and known_cursed(i) for i in state.get('inventory',[])):return decision
    # Unknown status effects default to single steps too; do not accidentally
    # batch through a new kind of timed protection or immobilization.
    if any(b['name'].lower() not in BENIGN_TRAVEL_BUFFS for b in hero.get('buffs',[])):return decision
    if any(getattr(p,k,None) for k in ('ambush_plan','doorway_hold','multi_door_plan','ranged_plan',
            'escape_commitment','room_journey','puzzle_probe','potion_stash','drop_plan','food_freeze_plan',
            'hungry_cooking_plan','well_cleanse_plan','wood_burn_plan','trap_payload_return','suspect_probe_plan',
            'secret_search_goal','barrier_followup','fly_escape_plan','boxed_snake_escape')):return decision
    try:
        from .survival_policy import is_container
    except ImportError:
        from survival_policy import is_container
    if any(not o.get('top_item') and not is_container(o) for o in state.get('objects',[])):return decision
    dx,dy=route[1]%w-pos%w,route[1]//w-pos//w
    if abs(dx)+abs(dy)!=1:return decision  # No diagonal/corner-cutting batches.
    forbidden=p.navigation_barriers(state,decision.intent)
    def clear(cell):
        tile=p.tiles.get(cell,{})
        return tile.get('visible') and tile.get('observed') and (simple or p.visits[cell]>0) and cell not in forbidden \
            and tile.get('terrain') in GROUND and not tile.get('trap') and not tile.get('plant') \
            and not tile.get('effects') and cell not in p.loot and cell not in p.room_blocked \
            and not p.failed_moves[cell] and cell not in p.blocked and p.walkable(cell)
    def corridor(cell):
        if not clear(cell):return False
        x,y=cell%w,cell//w
        if not (0<x<w-1 and 0<y<h-1):return False
        along={cell-dy*w-dx,cell+dy*w+dx}
        for n in neighbors(cell,w,h):
            tile=p.tiles.get(n,{})
            if simple:
                # Fully observed open ground is fine, but not unknown edges,
                # door interactions, actors, loot, hazards or timed terrain.
                if not tile.get('visible') or not tile.get('observed'):return False
                if tile.get('terrain') in WALLS:
                    if tile.get('effects') or tile.get('plant') or tile.get('trap') or n in p.loot:return False
                elif not clear(n):return False
                continue
            if n in along:
                if not clear(n):return False
            elif not tile.get('visible') or not tile.get('observed') or tile.get('terrain') not in WALLS \
                    or tile.get('effects') or tile.get('plant') or tile.get('trap') or n in p.loot:return False
        return True
    segment=[]
    for index,cell in enumerate(route[:MAX_STEPS+1]):
        if cell!=pos+index*(dy*w+dx) or not corridor(cell):break
        segment.append(cell)
    if len(segment)<MIN_STEPS+1:return decision
    original=decision.action['cell'];decision.action=dict(decision.action,cell=segment[-1])
    decision.movement_batch=tuple(segment)
    goal=p.exploration_goal
    if goal and goal.get('proposed')==(state['depth'],pos,original):
        goal['proposed']=(state['depth'],pos,segment[-1])
    p.planner.report['movement_batch']={'route':segment,'requested_steps':len(segment)-1,
        'qualification':('Native walking on fully observed safe straight ground' if simple else
                         'Native walking on visited visible straight corridor')+
                        '; arrival and actual steps require receipt'}
    return decision


def confirmed_path(before,decision,after):
    planned=decision.movement_batch;trace=after.get('movement_trace',{})
    if not isinstance(trace,dict):return None
    if not planned or before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0) \
            or trace.get('depth')!=before.get('depth') or trace.get('branch',0)!=before.get('branch',0) \
            or not trace.get('same_floor') or trace.get('truncated'):return None
    cells=trace.get('cells',[])
    if not isinstance(cells,list) or not cells or cells[0]!=before['hero']['cell'] or cells[-1]!=after['hero']['cell'] \
            or len(cells)>len(planned) or tuple(cells)!=planned[:len(cells)]:return None
    return cells


def observe(p,before,decision,after):
    if not decision.movement_batch:return None
    cells=confirmed_path(before,decision,after)
    if cells is None:
        p.movement_batch_disabled=True
        return {'status':'unverified','requested_route':list(decision.movement_batch),
                'qualification':'Missing/unexpected actual route; batching disabled for floor, no intermediate movement credit'}
    for cell in cells[1:-1]:p.visits[cell]+=1  # Final position is counted by the next ordinary observation update.
    reached=cells[-1]==decision.movement_batch[-1]
    if not reached:p.movement_batch_ready_at=after.get('evaluation_stats',{}).get('elapsed_turns',0)+6
    return {'status':'completed' if reached else 'interrupted','actual_route':cells,
            'confirmed_steps':len(cells)-1,'requested_steps':len(decision.movement_batch)-1,
            'qualification':'One accepted input, actual recorded movement only; no inferred arrival, pickup or clearance'}
