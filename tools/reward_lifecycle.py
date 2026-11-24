"""Protected work owns a return commitment and collection goals, never stock."""
from dataclasses import dataclass, field
from enum import Enum


class ReturnPhase(str, Enum):
    HYPOTHESIS = "hypothesis"
    PROTECTED = "protected"
    EXPOSED = "exposed"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


@dataclass
class RewardLifecycle:
    depth: int
    branch: int
    kind: str
    bank: int
    goals: set = field(default_factory=set)
    receipts: set = field(default_factory=set)
    phase: ReturnPhase = ReturnPhase.HYPOTHESIS
    reason: str = ""

    def observe(self, state, duration):
        if (state["depth"], state.get("branch", 0)) != (self.depth, self.branch):
            self.interrupt("scope changed without verified return")
            return
        if self.phase in {ReturnPhase.CANCELLED, ReturnPhase.INTERRUPTED, ReturnPhase.RETURNED}:
            return
        if duration > 0 and self.phase == ReturnPhase.HYPOTHESIS:
            self.phase = ReturnPhase.PROTECTED
        if state["hero"]["cell"] != self.bank and self.phase == ReturnPhase.PROTECTED:
            self.phase = ReturnPhase.EXPOSED

    def cancel(self):
        # A failed protection test cannot discharge an actual return commitment.
        if self.phase == ReturnPhase.HYPOTHESIS:
            self.phase = ReturnPhase.CANCELLED

    def interrupt(self, reason):
        if self.phase not in {ReturnPhase.RETURNED, ReturnPhase.CANCELLED}:
            self.phase = ReturnPhase.INTERRUPTED
            self.reason = reason

    def returned(self, state):
        if (state["depth"], state.get("branch", 0), state["hero"]["cell"]) != (
                self.depth, self.branch, self.bank):
            raise ValueError("return requires the original scoped bank")
        if self.phase in {ReturnPhase.PROTECTED, ReturnPhase.EXPOSED}:
            self.phase = ReturnPhase.RETURNED

    def record(self):
        return {"depth": self.depth, "branch": self.branch, "kind": self.kind,
                "bank": self.bank, "phase": self.phase.value, "reason": self.reason,
                "goals": sorted(self.goals), "collected": sorted(self.receipts),
                "uncollected": sorted(self.goals-self.receipts),
                "owned_item_debt": False}


def lifecycle(p, trip):
    work = trip.lifecycle
    if work is None:
        bank = trip.itinerary.success_return if getattr(trip, "itinerary", None) else trip.route[0]
        goals = set(getattr(trip, "targets", [trip.route[-1]]))
        trip.lifecycle = work = RewardLifecycle(trip.depth, trip.branch, trip.kind, bank, goals)
        # Keep the controller and run history on the same canonical object.
        p.reward_lifecycles.append(work)
    work.goals.update(getattr(trip, "targets", [trip.route[-1]]))
    if hasattr(trip, "collected"):
        trip.collected = work.receipts
    return work


def interrupt(p, reason):
    trip = p.room_journey
    if trip is not None:
        lifecycle(p, trip).interrupt(reason)


def observe_collection(p, state, cell):
    """Only the accepted, inventory-backed collection receiver calls this."""
    for work in p.reward_lifecycles:
        if (work.depth, work.branch) == (state["depth"], state.get("branch", 0)) \
                and cell in work.goals:
            work.receipts.add(cell)
    trip = p.room_journey
    if trip is not None and (trip.depth, trip.branch) == (
            state["depth"], state.get("branch", 0)):
        work = lifecycle(p, trip)
        if cell in work.goals:
            work.receipts.add(cell)
