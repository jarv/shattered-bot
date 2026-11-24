"""Observe bounded root retirement; waiting never certifies terrain or pickup."""
from dataclasses import dataclass
import math
import re

try:
    from .objective_episodes import Scope
    from .policy_decision import Intent
    from .policy_geometry import distance,neighbors
    from .hunger_budget import forecast
except ImportError:
    from objective_episodes import Scope
    from policy_decision import Intent
    from policy_geometry import distance,neighbors
    from hunger_budget import forecast


# An operational bound, NOT a universal expiry claim. Regrowth can renew roots;
# its distinct cursed effects do not even share the same initial volume.
MAX_INPUTS = 16
MAX_TURNS = 16
CONTROLLER = "rooted-recovery"


@dataclass
class RootRecovery:
    scope: Scope
    start: float
    accepted: int = 0
    stagnant: bool = False


def root(state):
    return next((b for b in state.get("hero",{}).get("buffs",[])
                 if b.get("name","").lower()=="rooted"),None)


def clock(state):
    value=state.get("evaluation_stats",{}).get("elapsed_turns")
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) \
        and math.isfinite(value) else None


def choose(c):
    p,s=c.policy,c.state
    buff=root(s)
    if not buff:
        p.root_recovery_plan=None
        return None
    duration=re.search(r"Turns of root remaining:\s*(\d+(?:\.\d+)?)\.",
                       buff.get("description",""),re.I)
    if not duration or not 0<float(duration[1])<=1:
        return None
    if s.get("scene")!="GameScene" or s.get("status")!="ready" or s.get("modal") \
            or c.boss or c.enemies or p.recent_threats or p.unseen_damage_turns or c.danger:
        return None
    if c.hero["hp"]!=c.hero["max_hp"] or any(
            b["name"].lower() not in {"rooted","barrier","lingering magic"}
            for b in c.hero.get("buffs",[])):
        return None
    tiles={t["cell"]:t for t in s["map"]["cells"]}
    nearby={c.pos,*neighbors(c.pos,c.width,s["map"]["height"])}
    if any(not tiles.get(n,{}).get("visible") or not tiles[n].get("observed")
           or any(tiles[n].get(k) for k in ("effects","trap","plant"))
           for n in nearby):
        return None
    if tiles[c.pos]["terrain"] not in {1,2,3,6,9,11,14,15,19,20,29,30} \
            or c.pos in p.room_blocked or c.pos in p.fire_buffer \
            or c.pos in p.fire_spread_buffer:
        return None
    # Do not wait beside special-room actors or an observed nearby cloud/fire,
    # even when the current tile itself is clear. No expiry is inferred.
    if any(distance(c.pos,n,c.width)<=4 for n in p.room_actors) or any(
            t.get("effects") and distance(c.pos,n,c.width)<=4 for n,t in p.tiles.items()):
        return None
    turn=clock(s)
    if turn is None:return None
    plan=p.root_recovery_plan
    if plan and plan.scope!=Scope.of(s):return None
    if plan and (plan.stagnant or turn<plan.start
                 or turn-plan.start>=MAX_TURNS or plan.accepted>=MAX_INPUTS):
        p.stop_gameplay("Root recovery clock stalled or its bounded observation budget exhausted",
                        kind="immediate-safety-emergency")
    cost=MAX_TURNS if plan is None else max(1,MAX_TURNS-(turn-plan.start))
    estimate=forecast(p,s)
    # Uneaten or uncollected food is not prepaid stationary recovery fuel.
    if estimate is None or estimate["remaining_to_starvation_lower_bound"] \
            < cost+estimate["reserved_turns"]:
        return None
    if plan is None:
        p.root_recovery_plan=plan=RootRecovery(Scope.of(s),turn)
    p.planner.report["rooted_recovery"]={
        "accepted_inputs":plan.accepted,"max_inputs":MAX_INPUTS,
        "elapsed_turns":turn-plan.start,"max_turns":MAX_TURNS,
        "qualification":"One input, fresh recheck; no root expiry or collection inferred"}
    decision=p.decision({"type":"wait"},"recover: bounded fresh observation of roots",
                        intent=Intent.RECOVER)
    decision.controller=CONTROLLER
    return decision


def observe(p,before,decision,after):
    plan=p.root_recovery_plan
    if plan is None or plan.scope!=Scope.of(before):return None
    owned=decision.controller==CONTROLLER and decision.action=={"type":"wait"}
    if owned:
        plan.accepted+=1
        a,b=clock(before),clock(after)
        plan.stagnant=a is None or b is None or b<=a
    cleared=after.get("scene")=="GameScene" and after.get("depth") is not None \
        and Scope.of(after)==plan.scope and after.get("status")=="ready" and not after.get("modal") \
        and not root(after)
    report={"accepted_inputs":plan.accepted,"clock_stagnant":plan.stagnant,
            "root_absence_observed":cleared,"collection_credited":False}
    if cleared:p.root_recovery_plan=None
    return report if owned or cleared else None
