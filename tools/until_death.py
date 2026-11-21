"""Explicit ready-game continuation; never bypass ambiguous execution or unknown UI."""
import json
try:
    from .continuation import best_effort
    from .survival_policy import is_hostile
    from .policy_decision import GameplayBlocked,TacticalBlocked,NoSafeAction,PlannerStuck
except ImportError:
    from continuation import best_effort
    from survival_policy import is_hostile
    from policy_decision import GameplayBlocked,TacticalBlocked,NoSafeAction,PlannerStuck


def recover(p,state,error):
    if not isinstance(error,(GameplayBlocked,TacticalBlocked,NoSafeAction)):return None
    if state.get('scene')!='GameScene' or state.get('status')!='ready' or state.get('modal') \
            or state.get('hero',{}).get('hp',0)<=0:return None
    p.planner.begin();p.update(state)
    p.log_continuation_error(state,'until-death-gameplay-continuation',error.reason)
    try:
        decision=best_effort(p,state,[o for o in state.get('objects',[]) if is_hostile(o)])
    except (GameplayBlocked,TacticalBlocked,NoSafeAction) as rescue_error:
        raise PlannerStuck(error.reason + "; rescue declined: " + rescue_error.reason) from None
    if decision is None:
        raise PlannerStuck(error.reason)
    if decision:decision.controller='until-death-continuation'
    return decision


class ClockDeadlock:
    """No HP plateau timeout: hunger/regeneration can delay death for many turns."""
    def __init__(self):
        self.stalled=0

    def observe(self,before,action,after):
        a=before.get('evaluation_stats',{}).get('elapsed_turns')
        b=after.get('evaluation_stats',{}).get('elapsed_turns')
        # Only a non-advancing clock AND identical public gameplay state after
        # repeated accepted waits can signal execution deadlock. Changing buffs
        # (e.g. a time bubble), HP or hunger are real progress, not deadlock.
        def snapshot(s):
            return json.dumps({k:s.get(k) for k in ('depth','branch','hero','objects','inventory','map','danger_cells','status','modal')},sort_keys=True)
        if action=={'type':'wait'} and a is not None and b==a and snapshot(before)==snapshot(after):
            self.stalled+=1
        else:self.stalled=0
        return self.stalled>=32
