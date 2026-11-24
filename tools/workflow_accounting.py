"""Typed interruption accounting and exact accepted-action ownership witnesses."""
import copy
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from enum import Enum

try:
    from .objective_episodes import Scope
except ImportError:
    from objective_episodes import Scope


class RecoveryPhase(str, Enum):
    DECLINED = "declined"
    ACTIVE = "active"
    PAUSED = "paused"
    DESCENDED = "descended"
    EXHAUSTED = "exhausted"
    DIED = "died"
    REJECTED = "rejected"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class OwnedAction:
    owner: int
    scope: Scope
    origin: int
    action: tuple
    intent: str
    controller: str | None
    route: tuple

    @classmethod
    def capture(cls, owner, state, decision, route):
        return cls(owner, Scope.of(state), state["hero"]["cell"],
                   tuple(sorted(decision.action.items())), decision.intent,
                   decision.controller, tuple(route))

    def matches(self, owner, state, decision):
        return (self.owner == owner
                and (state.get("depth"), state.get("branch", 0)) ==
                    (self.scope.depth, self.scope.branch)
                and state.get("hero", {}).get("cell") == self.origin
                and tuple(sorted(decision.action.items())) == self.action
                and decision.intent == self.intent and decision.controller == self.controller)

    def record(self):
        return dict(owner=self.owner,depth=self.scope.depth,branch=self.scope.branch,
                    origin=self.origin,action=dict(self.action),intent=self.intent,
                    controller=self.controller,route=list(self.route))


@dataclass
class AcceptedBudget:
    total_limit: int = 64
    stall_limit: int = 8
    accepted: int = 0
    owned: int = 0
    interruptions: int = 0
    unattributed: int = 0
    stalled: int = 0
    best_distance: int = 64

    @property
    def exhausted(self):
        return self.accepted >= self.total_limit or self.stalled >= self.stall_limit

    def accept(self, owned, distance=None):
        self.accepted += 1
        if not owned:
            self.interruptions += 1
            return
        self.owned += 1
        if distance is not None and distance < self.best_distance:
            self.best_distance = distance
            self.stalled = 0
        else:
            self.stalled += 1


@dataclass
class RecoveryEpisode(MutableMapping):
    """One state owner with a dictionary-compatible diagnostic view.

    The published report is a snapshot, never an input to scheduling. Mapping
    aliases permit reduced historical fixtures without another counter store.
    """
    details: dict
    phase: RecoveryPhase = RecoveryPhase.DECLINED
    budget: AcceptedBudget = field(default_factory=AcceptedBudget)
    receipts: set = field(default_factory=set)
    report: dict = field(default_factory=dict, compare=False)

    COUNTERS = dict(accepted_actions="accepted", owned_actions="owned",
                    interruptions="interruptions", unattributed_actions="unattributed", stalled_actions="stalled",
                    best_distance="best_distance")

    @classmethod
    def from_record(cls, record):
        record = copy.deepcopy(record)
        phase = RecoveryPhase(record.pop("status", "declined"))
        counters = {attr: record.pop(key) for key, attr in cls.COUNTERS.items()
                    if key in record}
        if "unattributed" not in counters:
            counters["unattributed"] = max(0,counters.get("accepted",0) -
                counters.get("owned",0) - counters.get("interruptions",0))
        episode = cls(record, phase, AcceptedBudget(**counters))
        episode.publish()
        return episode

    def publish(self):
        self.report.clear()
        self.report.update(copy.deepcopy(self.details), status=self.phase.value,
                           **{key: getattr(self.budget, attr)
                              for key, attr in self.COUNTERS.items()})

    def __getitem__(self, key):
        if key == "status":
            return self.phase.value
        if key in self.COUNTERS:
            return getattr(self.budget, self.COUNTERS[key])
        return self.details[key]

    def __setitem__(self, key, value):
        if key == "status":
            self.phase = RecoveryPhase(value)
        elif key in self.COUNTERS:
            setattr(self.budget, self.COUNTERS[key], value)
        else:
            self.details[key] = value
        self.publish()

    def __delitem__(self, key):
        if key == "status" or key in self.COUNTERS:
            raise TypeError("Episode lifecycle/counters cannot be deleted")
        del self.details[key]
        self.publish()

    def __iter__(self):
        return iter((*self.details, "status", *self.COUNTERS))

    def __len__(self):
        return len(self.details)+1+len(self.COUNTERS)
