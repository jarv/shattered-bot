"""Execute and audit policy decisions; never retry ambiguously executed inputs."""
import json
from pathlib import Path
import time
from itertools import count

try:
    from .player_api import PlayerAPIError
    from .policy_decision import Finished, Intent, TacticalBlocked, NoSafeAction, PlannerStuck
    from .policy_runtime import Transaction
    from .survival_policy import SurvivalPolicy, NavigationLoopGuard, MenuLoopGuard
    from .decision_engine import source_revision
    from .combat_observation import observe_accepted_attack
except ImportError:
    from player_api import PlayerAPIError
    from policy_decision import Finished, Intent, TacticalBlocked, NoSafeAction, PlannerStuck
    from policy_runtime import Transaction
    from survival_policy import SurvivalPolicy, NavigationLoopGuard, MenuLoopGuard
    from decision_engine import source_revision
    from combat_observation import observe_accepted_attack


def rejected_before_execution(error):
    return error.status == 409 or (error.status == 400 and any(message in error.message for message in
                                  ("Button is no longer available", "A menu requires input")))


def run(api, policy, max_actions, delay, log_path, *, bounded=False):
    state = api.observation or api.state()
    result = {"outcome": "limit", "reason": "Action budget reached", "actions": 0, "attempts": 0,
              "goal": getattr(policy, "goal", "survival"), "engine": getattr(policy, "engine", "legacy"),
              "policy_revision": source_revision()}
    last_decision_state = state
    loop_guard = NavigationLoopGuard()
    menu_guard = MenuLoopGuard()
    try:
        from .until_death import recover as continue_alive,ClockDeadlock
    except ImportError:
        from until_death import recover as continue_alive,ClockDeadlock
    # Survival runs continue until death or explicit planner exhaustion. Bounds
    # are for tests/checkpoint evaluation, not a selectable survival mode.
    until_death=getattr(policy,'goal',None)=='survival' and not bounded;deadlock=ClockDeadlock()
    try:
        from .fallback_progress import FallbackProgress
    except ImportError:
        from fallback_progress import FallbackProgress
    fallback_progress = FallbackProgress()
    last_resource_veto = None
    result['until_death']=until_death
    with Path(log_path).open("x") as log:
        for index in (count() if until_death else range(max_actions)):
            transaction = Transaction(policy, loop_guard, menu_guard)
            decision=None
            try:
                decision = policy.choose(state)
                loop_guard.check(state, decision)
                menu_guard.check(state, decision)
            except Finished as done:
                report=dict(policy.planner.report) if isinstance(policy,SurvivalPolicy) else {}
                if report.get('priority_resource') and 'resource remains uncollected' in done.reason.lower():
                    veto={'kind':'resource-obligation','reason':done.reason,
                          'priority_resource':report['priority_resource']}
                    encoded=json.dumps(veto,sort_keys=True)
                    if encoded!=last_resource_veto:
                        log.write(json.dumps({'index':index,'policy_veto':veto})+'\n')
                        log.flush()
                        last_resource_veto=encoded
                decision=None
                if isinstance(done,TacticalBlocked) and isinstance(policy,SurvivalPolicy):
                    transaction.rollback()
                    try:
                        decision=policy.recover_tactical_block(state,done)
                    except Finished as hard:
                        done=hard
                    if decision:
                        try:
                            loop_guard.check(state,decision)
                            menu_guard.check(state,decision)
                        except Finished as rejected:
                            decision = None
                            done = NoSafeAction("Recovery rejected by loop guard: " + rejected.reason)
                        log.write(json.dumps({"index":index,"soft_failure":{"code":getattr(done,"code","recovery-loop"),"reason":done.reason,
                                                "policy_report":report}},ensure_ascii=False)+"\n")
                        log.flush()
                if decision is None and isinstance(done,NoSafeAction) and isinstance(policy,SurvivalPolicy):
                    transaction.rollback()
                    try:
                        decision=policy.recover_no_safe_action(state,done)
                    except Finished as hard:
                        done=hard  # Do not turn a separate validation/item veto into a risky input.
                if decision is None:
                    transaction.rollback()
                    try:
                        decision=continue_alive(policy,state,done) if until_death and isinstance(policy,SurvivalPolicy) else None
                    except Finished as hard:
                        done=hard
                if decision is None:
                    result.update(outcome=done.outcome, reason=done.reason)
                    if isinstance(done, PlannerStuck):
                        report = dict(policy.planner.report)
                        result["death_reason"] = done.reason
                        result["planner_failure"] = {
                            "kind": "stuck-planner", "reason": done.blocker,
                            "depth": state.get("depth"), "cell": state.get("hero", {}).get("cell"),
                            "review_priority": "high",
                        }
                        log.write(json.dumps({"index": index, "state": state,
                            "planner_failure": result["planner_failure"],
                            "policy_report": report}, ensure_ascii=False) + "\n")
                        log.flush()
                    if isinstance(policy,SurvivalPolicy):result["terminal_policy_report"]=report
                    break
            # Recovery inside the exception handlers can bypass the priority
            # tree (including its gas leaf). Never dispatch a recovery wait there.
            if decision.action == {"type": "wait"}:
                try:
                    from .toxic_escape import in_toxic_gas, escape as escape_toxic_gas
                except ImportError:
                    from toxic_escape import in_toxic_gas, escape as escape_toxic_gas
                if in_toxic_gas(state):
                    transaction.rollback()
                    policy.update(state)
                    try:
                        decision = escape_toxic_gas(policy, state)
                    except Finished as blocked:
                        result.update(outcome=blocked.outcome, reason=blocked.reason)
                        break
            record = {"index": index, "state": state, "action": decision.action, "reason": decision.reason,
                        "intent": decision.intent, "controller": decision.controller}
            if getattr(decision,"potion_purpose",None):record["potion_purpose"]=decision.potion_purpose
            if decision.movement_batch:record['requested_movement_route']=list(decision.movement_batch)
            if isinstance(policy, SurvivalPolicy):
                record["controllers"] = policy.planner.report.get("controllers", [])
                if policy.engine == "planner":
                    record["decision_engine"] = policy.planner.report
            if hasattr(policy, "challenge_combat"):
                record["challenge_report"] = policy.planner.report
                if policy.planner.report.get("nonfatal_obligations"):
                    log.write(json.dumps({"index":index,"nonfatal_obligations":policy.planner.report["nonfatal_obligations"]})+"\n")
            if isinstance(policy,SurvivalPolicy) and policy.planner.report.get('continuation_error'):
                error=policy.planner.report['continuation_error']
                log.write(json.dumps({'index':index,'continuation_error':error})+'\n')
                if error['occurrences']==1:
                    print(f"ERROR D{error['depth']} [{error['kind']}]: {error['reason']}; continuing",flush=True)
            if decision.intent == Intent.DESCEND and isinstance(policy, SurvivalPolicy):
                record["exploration"] = policy.exploration_report(state, policy.paths(state))
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            hero = state.get("hero", {})
            print(f"{index:04d} D{state.get('depth', '-')} HP {hero.get('hp', '-')}/{hero.get('max_hp', '-')} "
                  f"{decision.reason}: {decision.action}", flush=True)
            if delay:
                time.sleep(delay)
            result["attempts"] += 1
            try:
                next_state = api.step(decision.action)
            except PlayerAPIError as error:
                if rejected_before_execution(error):
                    transaction.rollback()
                    log.write(json.dumps({"rejected": str(error), "index": index}) + "\n")
                    state = api.state()
                    continue
                raise
            try:
                from .floor_metrics import snapshot
            except ImportError:
                from floor_metrics import snapshot
            log.write(json.dumps({'index':index,'accepted_transition':{'before':snapshot(state),
                'action':decision.action,'after':snapshot(next_state),'reason':decision.reason}},ensure_ascii=False)+'\n')
            log.flush()
            if isinstance(policy,SurvivalPolicy):
                try:
                    from .fly_tactics import observe_fallback
                    from .multi_enemy_tactics import observe_accepted as observe_multi_retreat
                    from .seed_strategies import observe as observe_seed
                    from .mapping_knowledge import observe as observe_mapping
                    from .corruption_tactics import observe as observe_corruption
                    from .movement_batching import observe as observe_movement_batch
                    from .room_supplies import observe as observe_room_supply
                    from .descent_potions import observe as observe_descent_potion
                except ImportError:
                    from fly_tactics import observe_fallback
                    from multi_enemy_tactics import observe_accepted as observe_multi_retreat
                    from seed_strategies import observe as observe_seed
                    from mapping_knowledge import observe as observe_mapping
                    from corruption_tactics import observe as observe_corruption
                    from movement_batching import observe as observe_movement_batch
                    from room_supplies import observe as observe_room_supply
                    from descent_potions import observe as observe_descent_potion
                for label,feedback in (('observed_fly_fallback',observe_fallback(policy,state,decision,next_state)),
                                       ('observed_multi_retreat',observe_multi_retreat(policy,state,decision,next_state)),
                                       ('observed_seed_input',observe_seed(policy,state,decision,next_state)),
                                       ('observed_full_mapping',observe_mapping(policy,state,decision,next_state)),
                                       ('observed_corruption_input',observe_corruption(policy,state,decision,next_state)),
                                       ('observed_movement_batch',observe_movement_batch(policy,state,decision,next_state)),
                                       ('observed_room_supply',observe_room_supply(policy,state,decision,next_state)),
                                       ('observed_descent_potion',observe_descent_potion(policy,state,decision,next_state))):
                    if feedback:log.write(json.dumps({'index':index,label:feedback})+'\n');log.flush()
                try:
                    from .inventory_tactics import observe_accepted as observe_inventory
                    from .trap_field_tactics import observe_accepted as observe_scan
                except ImportError:
                    from inventory_tactics import observe_accepted as observe_inventory
                    from trap_field_tactics import observe_accepted as observe_scan
                for label,feedback in (('observed_inventory_management',observe_inventory(policy,state,decision,next_state)),
                                       ('observed_trap_scan',observe_scan(policy,state,decision,next_state))):
                    if feedback:
                        log.write(json.dumps({'index':index,label:feedback})+'\n');log.flush()
                try:
                    from .resource_tactics import observe_hazard_recheck
                except ImportError:
                    from resource_tactics import observe_hazard_recheck
                recheck=observe_hazard_recheck(policy,state,decision,next_state)
                if recheck:
                    log.write(json.dumps({'index':index,'observed_hazard_recheck':recheck})+'\n')
                    log.flush()
                if getattr(policy,'unit_strategies_enabled',False):
                    try:
                        from .unit_strategies import observe_accepted as observe_unit_movement
                    except ImportError:
                        from unit_strategies import observe_accepted as observe_unit_movement
                    movement=observe_unit_movement(policy,state,decision,next_state)
                    if movement:
                        log.write(json.dumps({'index':index,'observed_unit_movement':movement})+'\n')
                        log.flush()
                try:
                    from .incoming_damage import observe as observe_incoming
                except ImportError:
                    from incoming_damage import observe as observe_incoming
                incoming=observe_incoming(policy,state,next_state)
                if incoming:
                    log.write(json.dumps({'index':index,'observed_incoming_damage':incoming})+'\n')
                    log.flush()
                feedback=observe_accepted_attack(policy,state,decision,next_state)
                if feedback:
                    log.write(json.dumps({"index":index,"observed_combat_damage":feedback})+"\n")
                    log.flush()
                try:
                    from .region_navigation import accepted_navigation
                except ImportError:
                    from region_navigation import accepted_navigation
                navigation=accepted_navigation(policy,state,decision,next_state)
                if navigation:
                    log.write(json.dumps({'index':index,'observed_navigation':navigation})+'\n')
                    log.flush()
                if hasattr(policy,'challenge_combat'):
                    try:
                        from .loot_completion import observe_collected
                    except ImportError:
                        from loot_completion import observe_collected
                    collection=observe_collected(policy,state,decision,next_state)
                    if collection:
                        log.write(json.dumps({'index':index,'observed_collection':collection})+'\n')
                        log.flush()
                    try:
                        from .pursuit_budget import observe_accepted
                    except ImportError:
                        from pursuit_budget import observe_accepted
                    pursuit=observe_accepted(policy,state,decision,next_state)
                    if pursuit:
                        log.write(json.dumps({'index':index,'observed_pursuit':pursuit})+'\n')
                        log.flush()
            frozen=until_death and deadlock.observe(state,decision.action,next_state)
            stalled_fallback = fallback_progress.observe(state, decision, next_state)
            last_decision_state, state = state, next_state
            result["actions"] += 1
            if frozen:
                result.update(outcome='deadlocked',reason='Execution deadlock: 32 accepted waits produced no public clock or gameplay-state progress; death cannot advance while execution is frozen')
                break
            if stalled_fallback:
                stuck = PlannerStuck("Legacy fallback exhausted 128 accepted waits without gameplay progress")
                result.update(outcome=stuck.outcome, reason=stuck.reason, death_reason=stuck.reason)
                result["planner_failure"] = {"kind": "stuck-planner", "reason": stuck.blocker,
                                             "review_priority": "high"}
                result["fallback_waits_without_progress"] = fallback_progress.waits
                break
        result.update(depth=state.get("depth"), hero=state.get("hero"),
                      game_seed=getattr(policy, "verified_seed", None),
                      max_depth=max(getattr(policy, "max_depth", 0) or 0, state.get("depth") or 0),
                      purchases=getattr(policy, "purchases", []),
                      visited_shops=sorted(getattr(policy, "shop_visited_floors", set())),
                      defeated_bosses=sorted(getattr(policy, "defeated_bosses", set())),
                       cleared_floors=getattr(policy, "cleared_floors", []))
        result["deferred_obligations"]=list(getattr(policy,"deferred_obligations",[]))
        result['missed_loot']=list(getattr(policy,'missed_loot',[]))
        result['continuation_errors']=list(getattr(policy,'continuation_errors',[]))
        result['inventory_management']=list(getattr(policy,'inventory_events',[]))
        if hasattr(policy,'stop_on_no_safe_action'):
            result['stop_policy']={'stop_on_no_safe_action':policy.stop_on_no_safe_action,
                                   'stop_on_incomplete_loot':policy.stop_on_incomplete_loot}
        if hasattr(policy,'enabled_challenges'):
            result['enabled_challenges']=list(policy.enabled_challenges)
            result['verified_challenges']=list(policy.verified_challenges)
        if hasattr(policy,'rules'):
            result['unit_strategies']={'enabled':policy.unit_strategies_enabled,
                                       'overrides':dict(policy.unit_strategies.overrides)}
            result['challenge_rules']=policy.rules.as_dict()
            result['challenge_mode']=policy.rules.mode
        if isinstance(policy, SurvivalPolicy) and policy.depth == state.get("depth") and "map" in state:
            result["exploration"] = policy.exploration_report(state, policy.paths(state))
            result["last_decision_resources"] = policy.planner.resources(policy, last_decision_state)
        log.write(json.dumps({"result": result, "state": state}, ensure_ascii=False) + "\n")
    return result
