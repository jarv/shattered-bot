"""Contextual coordination state, not an action selector or hazard permission.

Physical drops/rewards remain in the obligation ledger; reopening an episode
never resolves those items.
"""
from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETE = "complete"
    EXHAUSTED = "exhausted"


class EvidenceKind(str, Enum):
    NEW_UNTESTED_SUPPLY = "new-untested-supply"


@dataclass(frozen=True)
class Scope:
    depth: int
    branch: int = 0

    @classmethod
    def of(cls, state):
        return cls(state["depth"], state.get("branch", 0))


@dataclass(frozen=True)
class Evidence:
    kind: EvidenceKind
    scope: Scope
    resource: str
    observation_id: object = None


@dataclass
class Episode:
    objective: str
    scope: Scope
    status: Status = Status.READY
    reason: str = ""
    attempt: int = 1
    retry_on: frozenset = field(default_factory=frozenset)
    last_evidence: str = ""

    def record(self):
        return dict(objective=self.objective, depth=self.scope.depth,
                    branch=self.scope.branch, status=self.status.value,
                    reason=self.reason, attempt=self.attempt,
                    retry_on=sorted(k.value for k in self.retry_on),
                    last_evidence=self.last_evidence)


@dataclass
class EpisodeRegistry:
    episodes: dict = field(default_factory=dict)
    seen: set = field(default_factory=set)

    def allowed(self, objective, scope):
        episode = self.episodes.get((objective, scope))
        return episode is None or episode.status == Status.READY

    def exhaust(self, objective, scope, reason, *, retry_on=()):
        key = objective, scope
        episode = self.episodes.setdefault(key, Episode(objective, scope))
        episode.status = Status.EXHAUSTED
        episode.reason = reason
        episode.retry_on = frozenset(retry_on)
        return episode

    def accept(self, evidence):
        """Domain-validated accepted evidence only; never speculative plans.

        Tokens deduplicate callbacks across repeated exhaustion. Without a public
        observation id the runner must call this once per accepted input.
        """
        if evidence.observation_id is not None:
            token = (evidence.scope, evidence.kind, evidence.resource,
                     evidence.observation_id)
            if token in self.seen:
                return []
            self.seen.add(token)
        changed = []
        for episode in self.episodes.values():
            if episode.scope != evidence.scope \
                    or episode.status != Status.EXHAUSTED \
                    or evidence.kind not in episode.retry_on:
                continue
            episode.status = Status.READY
            episode.reason = "context changed: " + evidence.kind.value
            episode.last_evidence = evidence.resource
            episode.attempt += 1
            episode.retry_on = frozenset()
            changed.append(episode.objective)
        return changed

    def records(self):
        return [e.record() for e in self.episodes.values()]
