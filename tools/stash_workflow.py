"""Typed potion-stash lifecycle. No geometry or action admission lives here."""
from dataclasses import dataclass
from enum import Enum

try:
    from .physical_obligations import OwnedItems, DropProposal
except ImportError:
    from physical_obligations import OwnedItems, DropProposal


class StashPhase(str, Enum):
    DROP = "drop"
    READY = "ready"
    RETRIEVE = "retrieve"
    COMPLETE = "complete"


@dataclass
class StashWorkflow(OwnedItems):
    bank: int
    candidate: str = ""
    phase: StashPhase = StashPhase.DROP
    steps: int = 0
    pending: DropProposal | None = None
    purpose: str | None = None
    storage_itinerary: object = None

    def __post_init__(self):
        self.phase = StashPhase(self.phase)
        if isinstance(self.pending, tuple):
            # Old reconstructed fixtures cannot manufacture an accepted drop.
            self.pending = DropProposal(*self.pending)

    def retrieve(self):
        if self.phase != StashPhase.COMPLETE:
            self.phase = StashPhase.RETRIEVE

    def ready(self):
        if self.phase != StashPhase.DROP or self.pending is not None:
            raise ValueError("Only confirmed drops can reach the test-ready phase")
        self.phase = StashPhase.READY

    def complete(self):
        if self.phase != StashPhase.RETRIEVE or self.pending or self.unresolved:
            raise ValueError("Unfinished physical retrieval cannot complete")
        self.phase = StashPhase.COMPLETE

    def unknown_transfer(self,before,decision):
        if self.pending and decision.action==dict(type="item",id=self.pending.item_id,action="DROP") \
                and self.scope.depth==before.get("depth") \
                and self.scope.branch==before.get("branch",0):
            return self.pending
        return None

    def record(self):
        return dict(depth=self.depth, branch=self.branch, owner=self.owner, bank=self.bank,
                    cell=self.cell, candidate=self.candidate, phase=self.phase.value,
                    steps=self.steps, dropped=dict(self.dropped),
                    retrieved=dict(self.retrieved), outstanding=self.outstanding,
                    pending=self.pending.record() if self.pending else None,
                    purpose=self.purpose,
                    storage_itinerary=self.storage_itinerary.record() if self.storage_itinerary else None)

    # Narrow compatibility view for unmigrated read sites and historical fixture
    # assertions. These aliases share the typed object's fields, not a second plan.
    def __getitem__(self, key):
        if key not in self.__dataclass_fields__:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        if key not in self.__dataclass_fields__:
            raise KeyError(key)
        if key == "phase":
            value = StashPhase(value)
        elif key == "pending" and isinstance(value, tuple):
            value = DropProposal(*value)
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)


def workflow(p):
    """Normalize reconstructed test/legacy state once; production creates typed state."""
    plan = p.potion_stash
    if isinstance(plan, dict):
        p.potion_stash = plan = StashWorkflow(**plan)
    if plan and not plan.owner:
        if not p.physical_ledger.register(plan):
            p.stop_obligation("potion-stash","Stash resources belong to another unfinished workflow")
    return plan


def retrieve(p):
    plan = workflow(p)
    if plan:
        plan.retrieve()
