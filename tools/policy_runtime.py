"""Small, synchronous behavior selectors and transactional policy execution.

A leaf returns a Decision, returns None to decline, or raises Finished to stop.
Selectors are reactive: they restart at the highest priority on every observation.
Long-running intent belongs to tactic memory, never to the selector itself.
"""
import copy
from dataclasses import dataclass, field
from typing import Callable

try:
    from .policy_decision import Decision
except ImportError:
    from policy_decision import Decision


@dataclass(frozen=True)
class Leaf:
    name: str
    tick: Callable[["Context"], Decision | None]
    requires: str | None = None

    def __call__(self, context):
        profile = getattr(context.policy, "profile", None)
        if self.requires and not getattr(profile, self.requires, True):
            return None
        result = self.tick(context)
        context.trace.append({"node": self.name, "selected": result is not None})
        if result is not None:
            result.controller = self.name
        return result


@dataclass(frozen=True)
class Selector:
    name: str
    children: tuple["Leaf | Selector", ...]

    def __call__(self, context):
        for child in self.children:
            result = child(context)
            if result is not None:
                return result
        return None


@dataclass
class Context:
    policy: object
    state: dict
    boss: object = None
    enemies: list = field(default_factory=list)
    active: list = field(default_factory=list)
    engage: list = field(default_factory=list)
    planning_combat: bool = False
    trace: list = field(default_factory=list)

    @property
    def hero(self):
        return self.state["hero"]

    @property
    def inventory(self):
        return self.state["inventory"]

    @property
    def pos(self):
        return self.hero["cell"]

    @property
    def width(self):
        return self.state["map"]["width"]

    @property
    def hp(self):
        return self.hero["hp"] / max(1, self.hero["max_hp"])

    @property
    def buffs(self):
        return " ".join(b["name"].lower() for b in self.hero.get("buffs", []))

    @property
    def danger(self):
        return set(self.state.get("danger_cells", []))


class Transaction:
    """Rollback local intent only after an API explicitly rejects an input.

    Snapshot the entire object graphs together, preserving aliases. No manually
    maintained field allowlist: new tactics and subclass state participate too.
    Never use this on timeouts, whose execution status is unknown.
    """

    def __init__(self, *owners):
        self.owners = owners
        self.before = copy.deepcopy([vars(owner) for owner in owners])

    def rollback(self):
        for owner, before in zip(self.owners, self.before):
            vars(owner).clear()
            vars(owner).update(before)
