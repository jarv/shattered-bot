"""Reobserve cached confusion exposure from ordinary ground; never expire it."""
from dataclasses import dataclass

try:
    from .objective_episodes import Scope
    from .objective_planning import exhausted,mark
    from .policy_decision import Intent
    from .policy_geometry import distance,line_clear
    from .hunger_budget import admits,forecast,travel_cost
    from .escape_commitment import reverses
except ImportError:
    from objective_episodes import Scope
    from objective_planning import exhausted,mark
    from policy_decision import Intent
    from policy_geometry import distance,line_clear
    from hunger_budget import admits,forecast,travel_cost
    from escape_commitment import reverses


@dataclass
class ResourceView:
    scope: Scope
    resource: int
    vantage: int
    searched: bool = False

    @property
    def key(self):
        return f"resource-observation:{self.scope.depth}:{self.scope.branch}:{self.resource}"


def refresh(p,state,resources):
    """Observation can end an information trip, not receipt a pickup."""
    plan=getattr(p,"resource_view_plan",None)
    if plan and (plan.scope!=Scope.of(state) or plan.resource not in resources
                 or p.tiles.get(plan.resource,{}).get("visible")):
        p.resource_view_plan=None


def choose(p,state,resources,enemies,*,start=False):
    if enemies or p.recent_threats or p.unseen_damage_turns or state.get("danger_cells") \
            or state.get("status")!="ready" or state.get("modal") \
            or any(getattr(p,name,None) for name in (
                "room_journey","puzzle_probe","potion_stash","trap_payload_return","drop_plan")):
        return None
    buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
    if any(b in buffs for b in ("burn","poison","bleed","ooze","paral","root","vertigo","blind")):
        return None
    standing=p.tiles.get(state["hero"]["cell"],{})
    if not standing.get("observed") or not standing.get("visible") \
            or any(standing.get(k) for k in ("effects","trap","plant")) \
            or state["hero"]["cell"] in p.room_blocked:
        return None
    refresh(p,state,resources)
    # This provider supports only a previously observed confusion cloud on a
    # mandatory resource. Age, an inactive source trap or an old message cannot
    # establish that the resource or its approach is now safe.
    candidates={c for c in resources if p.tiles.get(c,{}).get("observed")
                and not p.tiles[c].get("visible") and p.tiles[c].get("effects")
                and all("cloud of confusion gas" in e.lower()
                        for e in p.tiles[c]["effects"])}
    if not candidates:return None
    excluded=p.navigation_barriers(state,Intent.REPOSITION)|{
        c for c,t in p.tiles.items() if not t.get("observed")
        or t["terrain"] not in {1,2,3,5,6,9,11,14,15,19,20,29,30}
        or any(t.get(k) for k in ("trap","plant","effects")) or c in p.loot}
    paths=p.paths(state,excluded)
    pos=state["hero"]["cell"]
    width=state["map"]["width"]
    observed={c:t for c,t in p.tiles.items() if t.get("observed")}
    budget=forecast(p,state)
    plan=p.resource_view_plan
    if plan is None and not start:
        return None  # Start only when ordinary work would otherwise descend.
    if plan and (plan.resource not in candidates or plan.vantage not in paths):
        return None  # Paused intent does not acquire a new budget or hazard permit.
    if plan is None:
        choices=[]
        for target in sorted(candidates):
            key=ResourceView(Scope.of(state),target,pos).key
            if exhausted(p,key,48,8):continue
            for view in paths:
                if view==pos or not 1<=distance(view,target,width)<=4 \
                        or not line_clear(view,target,width,observed):
                    continue
                route=p.route(paths,view)
                spent=p.objective_progress.get(key,{}).get("accepted",0)
                if len(route)-1+spent>48 or budget is not None \
                        and 2*travel_cost(state,p,route)+4>budget["optional_turns"]:
                    continue
                if any(reverses(p,dict(state,hero=dict(state["hero"],cell=a)),b)
                       for a,b in zip(route,route[1:])):
                    continue
                choices.append((len(route),distance(view,target,width),target,view))
        if not choices:return None
        _,_,target,view=min(choices)
        p.resource_view_plan=plan=ResourceView(Scope.of(state),target,view)
    if exhausted(p,plan.key,48,8):return None
    route=p.route(paths,plan.vantage)
    if not admits(p,state,2*travel_cost(state,p,route)+4):return None
    if pos==plan.vantage:
        if plan.searched:return None
        plan.searched=True
        action=p.decision({"type":"search"},"loot: one bounded observation from safe confusion-cloud vantage")
    else:
        step=route[1]
        if not p.tiles[step].get("visible") or not p.escape_step_allowed(state,step) \
                or reverses(p,state,step):return None
        action=p.toward(state,plan.vantage,
            "loot: reobserve cached confusion-cloud resource from ordinary safe ground",
            paths,intent=Intent.REPOSITION)
    if action:
        p.planner.report["resource_reobservation"]={
            "resource":plan.resource,"vantage":plan.vantage,"route":route,
            "hazard_retired":False,"collection_credited":False,
            "qualification":"Reobservation only; no expiry, protection or pickup inferred"}
        return mark(p,state,action,plan.key,plan.vantage,route)
