"""Bounded ordinary searches before entering publicly evidenced trap fields."""
try:
    from .policy_geometry import distance
    from .policy_decision import Intent
except ImportError:
    from policy_geometry import distance
    from policy_decision import Intent


def before_move(p,state,decision,enemies):
    if decision.controller == 'trap-field-scan' or getattr(decision,'summoning_scan',False):
        return None  # Keep the accepted-search receipt selected by preparation.
    p.trap_scan_pending=None
    try:
        from .mapping_knowledge import complete
    except ImportError:
        from mapping_knowledge import complete
    if complete(p,state):return None
    if not getattr(p,'unit_strategies_enabled',False) or enemies or p.recent_threats \
            or state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):return None
    if decision.action.get('type')!='cell' or decision.intent not in {Intent.LOOT,Intent.EXPLORE,Intent.REPOSITION}:return None
    pos=state['hero']['cell'];step=decision.action['cell'];width=state['map']['width']
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if 'starving' in buffs or state['hero']['hp']<.5*state['hero']['max_hp']:return None
    tile=p.tiles[pos]
    # A publicly triggered plate retains its trap name but is inactive.
    # It may anchor an ordinary search only after the independent effect,
    # plant and room checks; this never certifies neighboring hidden ground.
    inactive=tile.get('terrain')==19 and (tile.get('visible') or tile.get('observed'))
    if (tile.get('trap') and not inactive) or tile.get('plant') \
            or p.effects_block_movement(tile) or pos in p.room_blocked:return None
    traps=[c for c,t in p.tiles.items() if t.get('trap') and t['terrain']==18
           and (t.get('visible') or t.get('observed')) and distance(step,c,width)<=4
           and p.shot_clear(state,c)]
    # A single revealed summoning trap is already a local crowding hazard:
    # summons can press neighboring traps. Inspect the immediate approach
    # without inferring any hidden trap or declaring the loot route safe.
    adjacent_summoning=any(p.tiles[c].get('visible')
        and p.tiles[c]['trap'].lower()=='summoning trap'
        and distance(pos,c,width)==1 and distance(step,c,width)<=1 for c in traps)
    if (len(traps)<3 and not adjacent_summoning) or distance(pos,step,width)!=1:return None
    if min(distance(step,c,width) for c in traps)>min(distance(pos,c,width) for c in traps):return None
    p.planner.report['trap_field']={'observed_traps':sorted(traps),'status':'Observed trap-density hypothesis; hidden cells remain unknown'}
    if p.trap_scan_cells[pos]>=2 or sum(p.trap_scan_cells.values())>=6:return None
    talisman=next((i for i in state['inventory'] if i.get('equipped') and not i.get('known_cursed')
                   and i['name'].lower().startswith('talisman of foresight') and 'SCRY' in i.get('actions',[])),None)
    raw=(talisman.get('status') or '?').rstrip('%') if talisman else '?'
    if talisman and raw.isdigit() and int(raw)>=20 and sum(d==state['depth'] for d,_ in p.scry_attempts)<2:
        target=next((c for c in sorted(traps) if (state['depth'],c) not in p.scry_attempts),None)
        if target is not None:
            p.scry_attempts.add((state['depth'],target))
            return p.use(talisman,'SCRY','trap field: prioritize foresight scan before walking',target=target)
    p.trap_scan_pending={'depth':state['depth'],'branch':state.get('branch',0),'cell':pos,'traps':sorted(traps)}
    action=p.decision({'type':'search'},'trap field: search from safe ground before approaching revealed trap cluster')
    action.controller='trap-field-scan'
    return action


def observe_accepted(p,before,decision,after):
    plan=p.trap_scan_pending;p.trap_scan_pending=None
    if not plan or not (decision.controller=='trap-field-scan' or getattr(decision,'summoning_scan',False)) \
            or decision.action!={'type':'search'}:return
    if before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0) \
            or before['hero']['cell']!=after['hero']['cell'] or after['hero']['cell']!=plan['cell']:return
    p.trap_scan_cells[plan['cell']]+=1
    return dict(plan,accepted_searches=p.trap_scan_cells[plan['cell']],
                qualification='Ordinary search is probabilistic; not proof that unseen traps are absent')
