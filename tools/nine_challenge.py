#!/usr/bin/env python3
"""Legacy explicit all-nine/eight-challenge preset; regular bot: survival_bot.py."""
import sys
try:
    from .mage_policy import MagePolicy,CHALLENGES,POISONOUS
    from .challenge_rules import ChallengeRules
    from .survival_bot import main
except ImportError:
    from mage_policy import MagePolicy,CHALLENGES,POISONOUS
    from challenge_rules import ChallengeRules
    from survival_bot import main


class NineChallengePolicy(MagePolicy):
    """Compatibility preset for historical tests, replays and explicit launchers."""
    _legacy_all_nine_verification=True
    unit_strategies_enabled=False
    reserve_floor_puzzle_supplies=False  # Historical replay compatibility, not the configured Mage default.
    def __init__(self,goal='survival',engine='legacy',seed=None,on_diet=True):
        if not isinstance(on_diet,bool):raise ValueError('on_diet must be an explicit boolean')
        super().__init__(goal=goal,engine=engine,seed=seed,
                         rules=ChallengeRules.preset('all-nine' if on_diet else 'eight-without-on-diet'),
                         stop_on_no_safe_action=True,stop_on_incomplete_loot=True)


if __name__=='__main__':sys.exit(main(policy_factory=NineChallengePolicy))
