import unittest
from unittest.mock import patch

from tools.test_challenge_systems import ready
from tools.survival_policy import SurvivalPolicy
from tools.policy_decision import Decision, Intent, Finished


class RecentPursuitTests(unittest.TestCase):
    def test_wounded_loot_reentry_does_not_forget_recent_giant_reach(self):
        s,p=ready()
        s["hero"]["hp"]=10
        p.recent_threats[26]={"cell":26,"name":"marsupial rat","description":"_Giant Champion_","observations_ago":1}
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":24},"arbitrary prose",Intent.LOOT)):
            with self.assertRaises(Finished):p.choose(s)

    def test_recent_threat_expires_or_clears_on_public_empty_tile(self):
        for visible in (True,False):
            s,p=ready()
            s["objects"]=[{"name":"marsupial rat","cell":26,"description":"_Giant Champion_"}]
            p.update(s)
            self.assertIn(26,p.recent_threats)
            s["objects"]=[]
            next(t for t in s["map"]["cells"] if t["cell"]==26)["visible"]=visible
            for _ in range(1 if visible else 7):p.update(s)
            self.assertNotIn(26,p.recent_threats)
