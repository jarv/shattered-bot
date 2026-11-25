"""Named, immutable objective profiles; combat engine selection is independent."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    quests: bool = True
    special_rooms: bool = True
    full_exploration: bool = True
    secret_hunting: bool = True


PROFILES = {
    "legacy-bot": Profile("legacy-bot"),
    "simple-bot": Profile("simple-bot", False, False, False, False),
}


def resolve(name="legacy-bot"):
    if not isinstance(name, str) or name not in PROFILES:
        raise ValueError("Unknown bot implementation: %r" % (name,))
    return PROFILES[name]


def enabled(policy, feature):
    return getattr(getattr(policy, "profile", PROFILES["legacy-bot"]), feature)
