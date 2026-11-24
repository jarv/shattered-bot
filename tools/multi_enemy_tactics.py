"""Single-attacker retreats with separate public ground/flying approach geometry."""
from collections import deque
from math import ceil
try:
    from .combat_items import stats
    from .policy_geometry import distance,neighbors
    from .challenge_combat import reach,visibly_accelerated
    from .policy_decision import Intent
    from .retreat_geometry import onward_exit
except ImportError:
    from combat_items import stats
    from policy_geometry import distance,neighbors
    from challenge_combat import reach,visibly_accelerated
    from policy_decision import Intent
    from retreat_geometry import onward_exit


def can_attack(p,state,enemy,cell):
    if enemy.get('sleeping'):return False
    if distance(cell,enemy['cell'],state['map']['width'])<=reach(enemy):return True
    return 'ranged-attacks' in p.unit_strategies.profile(enemy).capabilities and p.enemy_can_see(state,enemy,cell)


def footable(p,enemy,cell):
    terrain=p.tiles.get(cell,{}).get('terrain')
    if terrain is None:return True  # Unknown enemy approach is not a certified wall.
    if terrain==0:return p.unit_strategies.profile(enemy).movement=='flying'
    return terrain in {1,2,3,5,6,7,8,9,11,14,15,17,18,19,20,24,29,30,32,37}


def approach_pressure(p,state,enemies,cell):
    """Conservative approach-slot matching, not invented enemy actions.

    Multiple queued ground enemies cannot all occupy the one doorway slot.
    Flyers may instead occupy distinct adjacent pit/trap-field flank slots.
    """
    width,height=state['map']['width'],state['map']['height'];options=[]
    # Identified over-strength armor makes a hero move take longer than one
    # turn. Round enemy approach opportunities upward: exact actor timing is
    # not public. Unknown armor requirements and hidden ring effects are not
    # inferred here, nor is this envelope a prediction of actual enemy actions.
    strength=state['hero'].get('strength')
    move_delay=1
    if isinstance(strength,(int,float)):
        for item in state.get('inventory',[]):
            value=stats(item) if item.get('equipped') and item.get('identified') else None
            if value and value[0]=='armor' and value[2]>strength:
                move_delay=max(move_delay,1.2**(value[2]-strength))
    for enemy in enemies:
        if enemy.get('sleeping'):continue
        slots=set()
        if 'ranged-attacks' in p.unit_strategies.profile(enemy).capabilities and p.enemy_can_see(state,enemy,cell):
            slots.add(('ranged',enemy['cell']))
        profile=p.unit_strategies.profile(enemy)
        fast='fast-movement' in profile.capabilities or visibly_accelerated(enemy)
        positions={enemy['cell']};front={enemy['cell']}
        # Ordinary contact rats attack rather than sidestep (Mob.Hunting).
        # At an established hold, inventing that sidestep lets the queued
        # rat occupy the vacated gate and falsely counts two attack slots.
        # Keep prospective movement, fast foes and other species conservative.
        hold=getattr(p,'doorway_hold',None)
        contact_rat=hold and hold['depth']==state['depth'] \
            and cell==state['hero']['cell']==hold['hide'] and enemy['cell']==hold['door'] and not fast \
            and enemy['name'].lower() in {'marsupial rat','albino rat'} \
            and distance(cell,enemy['cell'],width)<=1
        steps=0 if profile.movement=='stationary' or contact_rat else ceil(move_delay*(2 if fast else 1))
        for _ in range(steps):
            front={n for start in front for n in neighbors(start,width,height) if n!=cell and footable(p,enemy,n)}-positions
            positions.update(front)
        for candidate in positions:
            if candidate!=cell and distance(candidate,cell,width)<=reach(enemy) and footable(p,enemy,candidate):slots.add(candidate)
        options.append(slots)
    occupied={}
    def assign(index,seen):
        for slot in sorted(options[index],key=str):
            if slot in seen:continue
            seen.add(slot)
            if slot not in occupied or assign(occupied[slot],seen):occupied[slot]=index;return True
        return False
    return sum(assign(i,set()) for i in range(len(options)))


def single_file(p,state,enemies,cell):
    """Known-geometry doorway choke; do not count pits as walls for flyers."""
    width,height=state['map']['width'],state['map']['height']
    around=list(neighbors(cell,width,height))
    if any(c not in p.tiles for c in around):return False
    for gate in around:
        if p.tiles[gate]['terrain'] not in {5,6}:continue
        valid=True
        for enemy in enemies:
            if enemy.get('sleeping'):continue
            # The gate is the one allowed attacker slot. Starting the flank
            # search on its occupant would bypass the very gate we exclude
            # from every other enemy's search. Contact/approach pressure is
            # checked separately; other enemies must still have no flank.
            if enemy['cell']==gate:continue
            slots={c for c in around if c!=gate and footable(p,enemy,c)}
            queue=deque([enemy['cell']]);seen={cell,gate,enemy['cell']}
            while queue and valid:
                current=queue.popleft()
                if current in slots:valid=False;break
                for n in neighbors(current,width,height):
                    if n not in seen and n in p.tiles and footable(p,enemy,n):seen.add(n);queue.append(n)
            if not valid:break
        if valid:return True
    return False


def needs_retreat(p, state, enemies):
    """Act before simultaneous contact when distinct awake fronts are closing."""
    if not getattr(p, 'unit_strategies_enabled', False):
        return False
    active = [e for e in enemies if not e.get('sleeping')]
    if len(active) < 2:
        return False
    pos = state['hero']['cell']
    current = sum(can_attack(p, state, e, pos) for e in active)
    if current > 1:
        return True
    if single_file(p, state, active, pos) and approach_pressure(p, state, active, pos) <= 1:
        return False  # Do not abandon an actually verified single-file hold.
    close = [e for e in active if distance(pos, e['cell'], state['map']['width']) <= 4]
    return approach_pressure(p, state, active, pos) > 1 or (
        len(close) >= 2 and (current > 0 or any(distance(pos, e['cell'], state['map']['width']) <= 3 for e in close)))


def choose(p,state,enemies):
    p.multi_retreat_pending=None
    if not getattr(p,'unit_strategies_enabled',False) or state.get('status')!='ready' or state.get('modal'):return None
    active=[e for e in enemies if not e.get('sleeping')]
    pos=state['hero']['cell'];width=state['map']['width']
    count=lambda cell:sum(can_attack(p,state,e,cell) for e in active)
    current=count(pos)
    if p.multi_door_plan:
        # A closing door can hide the pursuing group after the first accepted
        # retreat. Do not discard that route and immediately explore back into
        # the protected escape edge. Memories constrain this continuation only;
        # they never start a route or authorize attacks/clearance.
        route_enemies=active
        occluded=len(active)<2
        if occluded and p.multi_door_plan['steps']>0 and pos!=p.multi_door_plan['door']:
            visible={e['cell'] for e in enemies}
            route_enemies=active+[e for c,e in p.recent_threats.items()
                                  if c not in visible and not e.get('sleeping')]
        committed=doorway_route(p,state,route_enemies,current,occluded=occluded)
        if committed:return committed
    if not needs_retreat(p,state,active):
        p.multi_retreat_streak=0
        return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('root','paral','vertigo')):return None
    # Preparation yields to closing multiple fronts before its pursuit review.
    # Reach the same bounded, safety-gated intervention here, including regular
    # mode, rather than indefinitely preempting it with non-choke movement.
    try:
        from .pursuit_budget import reassess
    except ImportError:
        from pursuit_budget import reassess
    intervention=reassess(p,state,active)
    if intervention:return intervention
    # A usable door is the first retreat objective, not a last resort after
    # spending several turns in an open-room exchange. Preserve all doorway
    # route, health-loss, flight-aware hold and accepted-input checks below.
    doorway=doorway_route(p,state,active,max(current,approach_pressure(p,state,active,pos)))
    if doorway:return doorway
    paths=p.paths(state,{e['cell'] for e in active});choices=[]
    for cell in paths:
        route=p.route(paths,cell)
        if not 2<=len(route)<=6:continue
        if any(p.tiles[c]['terrain'] in {5,7,8,10,18,21,22,31,37,38} or p.tiles[c].get('trap')
               or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c]) or c in p.loot
               or c in state.get('danger_cells',[]) for c in route[1:]):continue
        next_pressure=approach_pressure(p,state,active,route[1])
        if p.multi_retreat_streak>=3 and next_pressure>1:continue
        if count(cell)>1 or approach_pressure(p,state,active,cell)>1 or count(route[1])>max(1,current) \
                or next_pressure>max(1,current,approach_pressure(p,state,active,pos)):continue
        if next_pressure>1 and p.multi_retreat_edges[(pos,route[1])]>=3:continue
        choke=single_file(p,state,active,cell)
        # Low current approach pressure does not make a cul-de-sac a refuge.
        # Keep verified chokes, but require ordinary endpoints to have an
        # admitted onward square beyond the route's arrival edge.
        if not choke and not onward_exit(p,state,cell,route[-2],
                                         {e['cell'] for e in active},active):continue
        choices.append(((next_pressure>1,not choke,count(cell),max(count(c) for c in route[1:]),len(route),p.visits[cell],cell),route,choke))
    if not choices:
        p.log_continuation_error(state,'no-single-attacker-retreat',
            'Multiple observed attackers, but no admitted single-attacker square/approach route; continue best-effort combat rather than invent safety',
            {'observed_attackers':current,'hero_cell':pos,'accepted_multi_pressure_streak':p.multi_retreat_streak,
             'flying_foes':[e['name'] for e in active if p.unit_strategies.profile(e).movement=='flying']})
        return None
    _,route,choke=min(choices,key=lambda c:c[0]);step=route[1]
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=p.ranged_plan=None
    if choke and step==route[-1] and p.tiles[pos]['terrain'] in {5,6}:
        p.doorway_hold={'depth':state['depth'],'door':pos,'hide':step,'inputs':0,'quiet':0,'waits':0}
    p.multi_retreat_pending={'depth':state['depth'],'branch':state.get('branch',0),'from':pos,'to':step}
    p.planner.report['multi_enemy_retreat']={'route':route,'attackers_before':current,'attackers_next':count(step),
        'next_approach_slots':approach_pressure(p,state,active,step),
        'endpoint_attackers':count(route[-1]),'endpoint_approach_slots':approach_pressure(p,state,active,route[-1]),
        'known_doorway_choke':choke,'flight_aware':True,
        'qualification':'Observed positions and public movement capabilities; enemies can move, no guaranteed survival or hidden blockers'}
    return p.cell(step,'combat: retreat toward single-attacker '+('doorway choke' if choke else 'observed square'),intent=Intent.RETREAT)


def doorway_route(p,state,enemies,current,occluded=False):
    """Commit to an observed door; only certify the far-side hold after observing it."""
    pos=state['hero']['cell'];width,height=state['map']['width'],state['map']['height']
    plan=p.multi_door_plan
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if len(enemies)<2 or state.get('danger_cells') or any(b in buffs for b in ('root','paral','vertigo')):
        p.multi_door_plan=None;return None
    if occluded and (not plan or plan['steps']<=0 or pos==plan['door']):
        p.multi_door_plan=None;return None
    paths=p.paths(state,{e['cell'] for e in enemies})
    def gas_entrance(cell):
        # Closing a door clears its threshold cloud, not the remembered cloud
        # behind it. Opening/occupying that door can expose the hero again.
        # This is an ordinary combat refuge, not a protected room journey.
        return p.tiles[cell]['terrain']==5 and any(
            "toxic gas" in effect.lower()
            for n in neighbors(cell,width,height)
            for effect in p.tiles.get(n,{}).get('effects',[]))
    def admitted(route):
        return 2<=len(route)<=9 and not any(c in p.loot or c in state.get('danger_cells',[])
            or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} or p.tiles[c].get('trap')
            or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
            or gas_entrance(c) for c in route[1:]) \
            and sum(can_attack(p,state,e,route[1]) for e in enemies) <= max(
                1,sum(can_attack(p,state,e,pos) for e in enemies)) \
            and (not occluded or (p.tiles[route[1]].get('observed')
                and p.tiles[route[1]].get('visible')
                and not any(can_attack(p,state,e,route[1]) for e in enemies)))
    def pressure(cell):return approach_pressure(p,state,enemies,cell)
    if plan:
        if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0) or plan['steps']>=12 \
                or state['hero']['hp']<.35*state['hero']['max_hp'] \
                or plan['start_hp']-state['hero']['hp']>.3*state['hero']['max_hp'] \
                or p.tiles.get(plan['door'],{}).get('terrain') not in {5,6}:
            p.log_continuation_error(state,'doorway-retreat-incomplete',
                'Committed doorway route lost safety, health or accepted-input budget; no choke or clearance inferred',dict(plan))
            p.multi_door_plan=None;return None
        door=plan['door']
    else:
        # This is a new, unverified doorway setup, not a known single-attacker
        # retreat. Honor the same accepted-pursuit loss budget as other lures;
        # choose() may still select an already verified sight break/choke.
        # Do not initiate a setup that its continuation health gate would
        # immediately cancel, even if the first input loses no health.
        # Already verified single-attacker retreats in choose() remain eligible.
        if p.pursuit_lure_exhausted or state['hero']['hp']<.35*state['hero']['max_hp']:return None
        options=[]
        for door in paths:
            if p.tiles[door]['terrain'] not in {5,6} or p.multi_door_attempts[door]>=2:continue
            # Reobserve an unknown far side, but against flyers do not commit
            # to a door whose known surroundings rule out every flight-aware
            # hold. Ground-only observation-first doorway setups are unchanged.
            # This is only a negative preflight, never arrival certification.
            around=list(neighbors(door,width,height))
            holds=[c for c in around if p.walkable(c)]
            known=all(p.tiles.get(c,{}).get('observed') for c in around) and all(
                p.tiles.get(n,{}).get('observed')
                for c in holds for n in neighbors(c,width,height))
            if known and any(p.unit_strategies.profile(e).movement=='flying' for e in enemies) \
                    and not any(single_file(p,state,enemies,c) for c in holds):continue
            route=p.route(paths,door)
            if not admitted(route) or pressure(route[1])>max(1,current):continue
            # Do not prefer simultaneous contact just to reach a nearer door
            # when another admitted route limits current contact to one foe.
            # Keep distance ranking within each class, including the existing
            # single-attacker doorway setup. Future positions/holds are unknown.
            contact=sum(can_attack(p,state,e,route[1]) for e in enemies)
            options.append((contact>1,len(route),door))
        if not options:return None
        _,_,door=min(options)
        plan={'depth':state['depth'],'branch':state.get('branch',0),'door':door,'steps':0,
              'start_hp':state['hero']['hp']}
        p.multi_door_plan=plan;p.multi_door_attempts[door]+=1
    if pos==door:
        # Opening a door is not enough: stand behind it, not among the swarm.
        hides=[]
        for cell in neighbors(door,width,height):
            if cell not in paths or not single_file(p,state,enemies,cell):continue
            route=p.route(paths,cell)
            if admitted(route) and pressure(cell)<=1 and sum(can_attack(p,state,e,cell) for e in enemies)<=1:
                hides.append((len(route),cell))
        if not hides:
            p.multi_door_plan=None
            p.log_continuation_error(state,'doorway-hold-unverified',
                'Opened/reached door, but no observed flight-aware single-attacker holding square; replan without claiming safety',{'door':door})
            return None
        _,hide=min(hides);route=p.route(paths,hide);step=route[1]
        if step==hide:
            p.doorway_hold={'depth':state['depth'],'door':door,'hide':hide,'inputs':0,'quiet':0,'waits':0}
    else:
        if door not in paths or not admitted(p.route(paths,door)):
            p.multi_door_plan=None;return None
        route=p.route(paths,door);step=route[1]
        if pressure(step)>max(1,current):
            p.multi_door_plan=None;return None
    p.ambush_plan=p.snake_door_reset=p.ranged_plan=None
    p.multi_retreat_pending={'depth':state['depth'],'branch':state.get('branch',0),'from':pos,'to':step,
                             'door_route':True,'door':door}
    p.planner.report['multi_enemy_doorway']={'door':door,'route':route,'accepted_steps':plan['steps'],
        'status':'Move to observed door, open and reobserve before selecting hold' if pos!=door else 'Move behind verified flight-aware choke',
        'qualification':'Unknown far side is not certified safe; route rechecked each observation, no guaranteed survival'}
    return p.cell(step,'combat: committed multi-enemy doorway retreat; open/reobserve before holding',intent=Intent.RETREAT)


def observe_accepted(p,before,decision,after):
    plan=p.multi_retreat_pending;p.multi_retreat_pending=None
    if not plan or decision.controller!='multi-threat-retreat' or decision.intent!=Intent.RETREAT \
            or decision.action!={'type':'cell','cell':plan['to']}:return None
    if before.get('depth')!=plan['depth'] or before.get('branch',0)!=plan['branch'] \
            or before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0) \
            or before['hero']['cell']!=plan['from']:return None
    moved=after['hero']['cell']==plan['to']
    opened=plan.get('door_route') and after['hero']['cell']==plan['from'] \
        and any(t['cell']==plan['to'] and t.get('terrain')==5 for t in before.get('map',{}).get('cells',[])) \
        and any(t['cell']==plan['to'] and t.get('terrain')==6 for t in after.get('map',{}).get('cells',[]))
    if not moved and not opened:return None
    if plan.get('door_route') and p.multi_door_plan and p.multi_door_plan['door']==plan['door']:
        p.multi_door_plan['steps']+=1
        if p.doorway_hold and after['hero']['cell']==p.doorway_hold['hide']:p.multi_door_plan=None
    p.multi_retreat_edges[(plan['from'],plan['to'])]+=1
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    actual=sum(can_attack(p,after,e,after['hero']['cell']) for e in after.get('objects',[]) if is_hostile(e))
    p.multi_retreat_streak=p.multi_retreat_streak+1 if actual>1 else 0
    return dict(plan,accepted_edge_traversals=p.multi_retreat_edges[(plan['from'],plan['to'])])
