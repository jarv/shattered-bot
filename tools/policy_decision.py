"""Machine-readable decision semantics; reason is display-only text."""
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    OTHER = "other"
    EXPLORE = "explore"
    LOOT = "loot"
    DESCEND = "descend"
    SHOP = "shop"
    APPROACH = "approach"
    RETREAT = "retreat"
    REPOSITION = "reposition"
    RECOVER = "recover"
    BOSS = "boss"


class BlockerKind(str, Enum):
    OPTIONAL = "optional-work-exhausted"
    NAVIGATION = "navigation-stalled"
    PREPARATION = "mandatory-preparation-unresolved"
    SAFETY = "immediate-safety-emergency"
    EXECUTION = "execution-failure"
    UNKNOWN = "unclassified"


@dataclass
class Decision:
    action: dict
    reason: str
    intent: Intent = Intent.OTHER
    controller: str | None = None
    navigation_route: tuple = ()
    movement_batch: tuple = ()

    def __post_init__(self):
        self.intent = Intent(self.intent)

    @property
    def navigation(self):
        return self.intent in {Intent.EXPLORE, Intent.LOOT, Intent.DESCEND,
                               Intent.RETREAT, Intent.REPOSITION}

    @property
    def tracks_movement(self):
        return self.intent in {Intent.EXPLORE, Intent.LOOT, Intent.DESCEND}


class Finished(Exception):
    def __init__(self, outcome, reason, kind=BlockerKind.EXECUTION):
        self.outcome, self.reason = outcome, reason
        self.blocker_kind = BlockerKind(kind)
        super().__init__(reason)


class TacticalBlocked(Finished):
    """A recoverable tactic decline, distinguished semantically from hard gates."""
    def __init__(self,code,reason):
        kind = BlockerKind.NAVIGATION if code in {
            "navigation-loop", "escape-reversal", "navigation-stall", "unplanned-stairs"
        } else BlockerKind.UNKNOWN
        super().__init__("blocked",reason,kind)
        self.code=code


class NoSafeAction(Finished):
    """No admitted survival action, not a verification/UI/execution failure."""
    def __init__(self,reason):
        super().__init__('blocked',reason,BlockerKind.SAFETY)


class GameplayBlocked(Finished):
    """Known ready-game planning failure, never an API/UI/startup validation gate."""
    def __init__(self,reason,kind=BlockerKind.UNKNOWN):
        super().__init__('blocked',reason,kind)


class PlannerStuck(Finished):
    """Terminal planner exhaustion, not an observed in-game hero death."""
    def __init__(self, blocker, kind=BlockerKind.UNKNOWN):
        super().__init__('stuck-planner', 'stuck planner (bot unable to proceed)',kind)
        self.blocker = blocker
