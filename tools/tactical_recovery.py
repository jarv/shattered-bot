"""Soft tactical failures: ordinary visible actions, never hard-gate bypasses."""
try:
    from .challenge_combat import champion, exposure, reach, mixed_water_escape
    from .policy_decision import Intent,Finished
    from .consumable_tactics import choose_consumable
    from .wand_tactics import choose_transfusion
    from .room_loot import inventory_context
    from .retreat_geometry import onward_exit
    from .objective_planning import exhaust_preparation
    from .stash_workflow import workflow, StashPhase
    from .payload_workflow import workflow as payload_workflow, PayloadPhase
except ImportError:
    from challenge_combat import champion, exposure, reach, mixed_water_escape
    from policy_decision import Intent,Finished
    from consumable_tactics import choose_consumable
    from wand_tactics import choose_transfusion
    from room_loot import inventory_context
    from retreat_geometry import onward_exit
    from objective_planning import exhaust_preparation
    from stash_workflow import workflow, StashPhase
    from payload_workflow import workflow as payload_workflow, PayloadPhase


def recover(p,state,enemies,blocked,distance,neighbors,line_clear):
    if state.get("status")!="ready" or state.get("modal") or state.get("danger_cells"):
        return None
    p.soft_failures[blocked.code]+=1
    if blocked.code in {'navigation-loop','systematic-route-stall'} and p.exploration_goal:
        try:
            from .region_navigation import decline_goal
        except ImportError:
            from region_navigation import decline_goal
        decline_goal(p,state,blocked.reason)
    if blocked.code.startswith("obligation:"):
        controller=blocked.code.split(":",1)[1]
        pending=[{"kind":"unresolved "+controller,"cell":state["hero"]["cell"]}]
        if controller=="potion-stash":
            plan=workflow(p)
            if plan:pending[0]["cell"]=plan.cell
            if plan:
                # Clearing executable intent must not erase owned quantities.
                # Pending drops are not silently promoted to confirmed items.
                p.physical_ledger.defer(plan,blocked.reason,plan.pending)
                if plan.unresolved:
                    pending=[]  # The typed ledger is the sole physical owner.
            # Only a blocked, confirmed retrieval can be retried with a new
            # floor supply. Failed drops, budgets and probes stay disabled.
            retry = bool(
                plan and plan.depth==state["depth"]
                and plan.branch==state.get("branch",0)
                and plan.phase==StashPhase.RETRIEVE and plan.outstanding
                and not plan.pending and plan.steps<=48
                and (plan.cell not in p.paths(state)
                     or p.tiles.get(plan.cell,{}).get("effects")))
            exhaust_preparation(p,state,blocked.reason,new_supply_can_retry=retry)
            p.potion_stash=None
            p.puzzle_probe=None
        elif controller=="potion-probe":
            exhaust_preparation(p,state,blocked.reason)
            p.puzzle_probe=None
        elif controller=="trap-payload":
            plan=payload_workflow(p)
            if plan:
                uncertain=plan.proposal if plan.phase in {
                    PayloadPhase.PROPOSED,PayloadPhase.AIMING,PayloadPhase.UNVERIFIED} else None
                p.physical_ledger.defer(plan,blocked.reason,uncertain)
                pending=[]  # The typed ledger, not a copied generic record, owns it.
            p.trap_payload_return=None
        elif controller=="mimic-hunt":
            pending=[{"kind":"unverified mimic reward","cell":c} for c in p.mimic_obligations]
            for c in p.mimic_obligations:
                p.unconfirmed_loot[c]={'cell':c,'name':'Unconfirmed suspicious chest reward'}
            p.mimic_obligations.clear()
        elif controller=="room-journey":
            try:
                from .reward_lifecycle import interrupt
            except ImportError:
                from reward_lifecycle import interrupt
            interrupt(p,blocked.reason)
            p.room_journey=None
            p.deferred_room_controllers.add(controller)
        elif controller=="drop-room":
            p.drop_plan=None
            p.deferred_room_controllers.add(controller)
        p.defer_obligations(state,pending,blocked.reason)
    if blocked.code=="room-loot-stall" and p.room_loot_plan:
        p.room_loot_deferred[p.room_loot_plan["target"]]=inventory_context(state)
        p.room_loot_plan=None  # Retry after public inventory context changes; hard obligations are not waived.
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    hero=state["hero"]
    pos,width,height=hero["cell"],state["map"]["width"],state["map"]["height"]
    active=[e for e in enemies if not e.get("sleeping")]
    if blocked.code=="descent-obligation" and not active:
        reroute=locked_room_route(p,state,enemies)
        if reroute:return mark(p,reroute,blocked)
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if 'burning' in buffs and pos not in state.get('danger_cells',[]) and p.tiles[pos]['terrain']!=29:
        try:
            from .combat_positioning import rinse_ooze
        except ImportError:
            from combat_positioning import rinse_ooze
        rescue=rinse_ooze(p,state,enemies,distance,neighbors)
        if rescue:return mark(p,rescue,blocked)
    invisible="invisib" in buffs or "cloaked" in buffs
    remembered=[e for c,e in p.recent_threats.items() if c not in {o["cell"] for o in active}]
    threats=active+remembered  # Memories only constrain movement; never attack them.
    try:
        from .fly_tactics import defer_threatened_loot,escape
    except ImportError:
        from fly_tactics import defer_threatened_loot,escape
    if blocked.code=='recent-pursuit':defer_threatened_loot(p,state,threats)
    action=None if invisible else choose_consumable(p,state,enemies,distance,neighbors) or choose_transfusion(p,state,enemies,distance)
    if action:return mark(p,action,blocked)
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .ranged_tactics import choose as ranged_recovery
        except ImportError:
            from ranged_tactics import choose as ranged_recovery
        ranged=ranged_recovery(p,state,enemies)
        if ranged:return mark(p,ranged,blocked)
    fly_escape=escape(p,state,enemies,remembered)
    if fly_escape:return mark(p,fly_escape,blocked)
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .fly_tactics import desperate_attack
        except ImportError:
            from fly_tactics import desperate_attack
        strike=desperate_attack(p,state,enemies)
        if strike:return mark(p,strike,blocked)
    water_escape=mixed_water_escape(p,state,enemies,distance,neighbors,line_clear,remembered)
    if water_escape:return mark(p,water_escape,blocked)
    moves=[]
    try:
        from .escape_commitment import reverses
    except ImportError:
        from escape_commitment import reverses
    for cell in neighbors(pos,width,height):
        if any(b in buffs for b in ("root","paral","vertigo")):continue
        if not p.walkable(cell,{e["cell"] for e in enemies}) or cell in p.loot \
                or p.tiles[cell]["terrain"] in {7,8,21,22,31,37,38} or p.tiles[cell].get("plant"):
            continue
        risk=exposure(p,state,threats,cell,distance,line_clear)
        if risk["exposure"] or p.soft_recovery_edges[(pos,cell)]>=2:
            continue
        if reverses(p,state,cell):continue
        if active and not onward_exit(p,state,cell,pos,{e['cell'] for e in threats},threats):
            continue
        if p.tiles[pos]["terrain"]==29 and p.tiles[cell]["terrain"]!=29 \
                and any(champion(e)=="blazing" and distance(cell,e["cell"],width)<=reach(e)+1
                        and line_clear(e["cell"],cell,width,p.tiles) for e in threats):
            continue
        moves.append((p.soft_recovery_edges[(cell,pos)],p.visits[cell],cell))
    if moves and p.soft_failures[blocked.code]<=12:
        cell=min(moves)[-1]
        p.soft_recovery_edges[(pos,cell)]+=1
        return mark(p,p.cell(cell,"recovery: replan tactical stall onto observed unexposed ground",intent=Intent.RETREAT),blocked)
    try:
        from .boxed_snake_escape import choose as snake_exit
    except ImportError:
        from boxed_snake_escape import choose as snake_exit
    bounded=snake_exit(p,state,enemies,remembered)
    if bounded:return mark(p,bounded,blocked)
    if not invisible:
        try:
            from .incoming_damage import priority
        except ImportError:
            from incoming_damage import priority
        targets=[e for e in active if p.shot_clear(state,e["cell"])
                 or distance(pos,e["cell"],width)==1]
        for target in sorted(targets,key=lambda e:(-priority(p,state,active,e),not p.charged_magic(state) and e["name"].lower()=="sewer snake",
                                                  e.get("health_bar",[1,1])[0]/max(1,e.get("health_bar",[1,1])[1]),
                                                  distance(pos,e["cell"],width))):
            attack=p.best_attack(state,target)
            if attack:
                attack.reason="recovery: best available observed attack after tactical decline; risk accepted"
                return mark(p,attack,blocked)
    if moves:
        cell=min(moves)[-1]
        p.soft_recovery_edges[(pos,cell)]+=1
        return mark(p,p.cell(cell,"recovery: continue observed repositioning without attacking an unseen target",intent=Intent.RETREAT),blocked)
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .ranged_tactics import exposed_wait
        except ImportError:
            from ranged_tactics import exposed_wait
        if exposed_wait(p,state,enemies):p.stop_no_safe_action('Tactical recovery cannot wait in an observed ranged firing lane')
    if getattr(p,'unit_strategies_enabled',False) and any(e['name'].lower()=='swarm of flies' and not e.get('sleeping')
            and distance(pos,e['cell'],width)==1 for e in enemies):
        p.stop_no_safe_action('Fly pressure: no bounded attack or reduced-pressure retreat; do not silently recharge under adjacent attacks')
    if getattr(p,'unit_strategies_enabled',False) and not active and any(b in buffs for b in ('hungry','starving')):
        food=p.food_items(state)
        if food and 'starving' in buffs:
            return mark(p,p.use(food[0],'EAT','recovery: eat available food rather than idle while starving'),blocked)
        if p.soft_failures[blocked.code]>=3:
            p.defer_obligations(state,[{'kind':'unresolved '+blocked.code,'cell':pos}],
                                'No admitted progress action while hungry; bounded idle recovery exhausted')
            p.stop_gameplay('Hungry no-progress recovery exhausted; stop alive rather than silently wait to starvation',
                            kind="navigation-stalled")
    return mark(p,p.decision({"type":"wait"},"recovery: observe approach or recharge after tactical decline"),blocked)


def mark(p,action,blocked):
    action.controller="tactical-recovery"
    p.planner.report["soft_recovery"]={"code":blocked.code,"occurrences":p.soft_failures[blocked.code],
                                       "outcome":"continue with ordinary action; no kill guarantee"}
    return action


def locked_room_route(p,state,enemies=()):
    """Refuse the descent, not the run, when a required door has a usable key."""
    try:
        from .survival_policy import DOOR_KEYS
    except ImportError:
        from survival_policy import DOOR_KEYS
    paths=p.paths(state,{e["cell"] for e in enemies})
    targets=[c for c,t in p.tiles.items() if t["terrain"] in {10,21} and c in paths
             and p.keys.get(DOOR_KEYS[t["terrain"]],0)>0 and c not in p.optional_locks]
    for target in sorted(targets,key=lambda c:len(p.route(paths,c))):
        action=p.toward(state,target,"recovery: finish reachable keyed room instead of descending",paths,intent=Intent.EXPLORE)
        if action:return action
    return None
