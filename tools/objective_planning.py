"""Persistent preparation objectives, explicit blockers and accepted progress.

This layer schedules existing admitted actions; it never grants hazard access,
infers item identity, or marks a reward collected.
"""
from dataclasses import dataclass, field
from enum import Enum
try:
    from .policy_runtime import Transaction
except ImportError:
    from policy_runtime import Transaction


class Status(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETE = "complete"
    EXHAUSTED = "exhausted"


@dataclass
class Result:
    status: Status
    reason: str
    action: object = None
    prerequisites: list = field(default_factory=list)


def publish(p, objective, result):
    record = dict(status=result.status.value, reason=result.reason,
                  prerequisites=result.prerequisites)
    p.objective_results[objective] = record
    p.planner.report["objectives"] = dict(p.objective_results)
    p.planner.report["objective_progress"] = {
        k: dict(v) for k, v in p.objective_progress.items()}
    return result.action


def resolve(p, objective, prerequisites):
    """Try ordered prerequisite providers; record *why* each one declined.

    Providers retain their own action admission. A dependency cycle is a
    structured blocker, not recursion or permission to bypass an obligation.
    """
    if objective in p.objective_stack:
        return publish(p, objective, Result(Status.BLOCKED, "dependency cycle",
                                            prerequisites=list(p.objective_stack)))
    p.objective_stack.append(objective)
    attempts = []
    try:
        for name, provider in prerequisites:
            transaction = Transaction(p)
            result = provider()
            attempts.append(dict(objective=name, status=result.status.value, reason=result.reason))
            if result.status == Status.READY and result.action is not None:
                return publish(p, objective, Result(Status.READY, "execute prerequisite: "+name,
                                                     result.action, attempts))
            transaction.rollback()  # A declined provider does not own a plan/resource.
        return publish(p, objective, Result(Status.BLOCKED, "no admitted prerequisite action",
                                            prerequisites=attempts))
    finally:
        p.objective_stack.pop()


def available(action, reason):
    return Result(Status.READY if action else Status.BLOCKED, reason, action)


def exhausted(p, key, total, stagnant=8):
    progress = p.objective_progress.get(key, {})
    return progress.get("accepted", 0) >= total or progress.get("stagnant", 0) >= stagnant


def mark(p, state, action, key, target, route):
    """Attach the proposal to the action, so preemption cannot earn progress."""
    action.objective_receipt = dict(key=key, target=target, route=list(route),
                                    depth=state["depth"], branch=state.get("branch", 0),
                                    origin=state["hero"]["cell"], action=dict(action.action))
    return action


def observe(p, before, decision, after):
    receipt = getattr(decision, "objective_receipt", None)
    if not receipt or decision.action != receipt["action"] \
            or (before.get("depth"), before.get("branch", 0)) != (receipt["depth"], receipt["branch"]) \
            or (after.get("depth"), after.get("branch", 0)) != (receipt["depth"], receipt["branch"]) \
            or before.get("hero", {}).get("cell") != receipt["origin"]:
        return None
    # One callback per accepted input. Identical observations do not double-credit.
    token = after.get("observation_id")
    progress = p.objective_progress.setdefault(receipt["key"], dict(accepted=0, stagnant=0))
    if token is not None and progress.get("observation_id") == token:
        return None
    old = {t["cell"]: t for t in before.get("map", {}).get("cells", [])}
    new = {t["cell"]: t for t in after.get("map", {}).get("cells", [])}
    revealed = any(t.get("visible") and not old.get(c, {}).get("observed", old.get(c, {}).get("visible", False))
                   for c, t in new.items())
    opened = any(old.get(c, {}).get("terrain") == 5 and t.get("terrain") == 6 for c, t in new.items())
    actual = after.get("hero", {}).get("cell")
    toward = actual in receipt["route"][1:]
    progress.update(accepted=progress["accepted"]+1,
                    stagnant=0 if revealed or opened or toward else progress["stagnant"]+1,
                    observation_id=token, target=receipt["target"], actual_cell=actual,
                    revealed=revealed, opened=opened, advanced=toward)
    if receipt["key"].startswith("shop-target:"):
        p.entrance_visit_steps += 1
        # Arrival completes this travel commitment, even if corridor search,
        # loot or safety preempts the shop leaf on the next observation.
        # This is not a shop visit, door check or exploration-clear receipt.
        plan = p.shop_search_target
        if actual == receipt["target"] and plan and plan["target"] == actual:
            p.shop_search_target = None
    return dict(objective=receipt["key"], **progress)
