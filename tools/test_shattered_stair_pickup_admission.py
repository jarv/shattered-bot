"""Reduced public run 000077 decision 1229: meat on exit 757, hero at 728.

This is a deterministic selector/wrapper fixture, not reconstructed runtime
memory or a game replay. No observation is supplied after the changed choice.
"""
import copy
import unittest
from unittest.mock import patch

from tools.policy_decision import Decision, GameplayBlocked, Intent, TacticalBlocked
from tools.region_navigation import choose
from tools.survival_policy import SurvivalPolicy
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def encounter():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=728, hp=34, max_hp=35, strength=11)
    s["map"] = dict(width=30, height=32, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in ((667, 1), (728, 2), (727, 1), (757, 8))])
    obj = dict(cell=757, name="mystery meat",
               top_item=dict(name="mystery meat", quantity=1, identified=True))
    s["objects"] = [obj]
    p = verified()
    p.update(s)
    return p, s


class StairPickupAdmissionTests(unittest.TestCase):
    def wrapped(self, p, s, d):
        # Exercise the actual Mage post-selection gates; the lower selector
        # proposal is either obtained independently below or deliberately unsafe.
        with patch.object(SurvivalPolicy, "choose", return_value=d):
            return p.choose(s)

    def test_region_pickup_survives_final_stair_gate_without_collection_credit(self):
        p, s = encounter()
        d = choose(p, s, p.paths(s), set())
        self.assertEqual({"type": "cell", "cell": 757}, d.action)
        self.assertEqual(Intent.LOOT, d.intent)
        self.assertIn("freshly visible pile", d.reason)
        before = copy.deepcopy(s)
        try:
            selected = self.wrapped(p, s, d)
        except TacticalBlocked as error:
            self.fail("Fresh adjacent pickup was vetoed as a transition: " + error.code)
        self.assertEqual(d.action, selected.action)
        self.assertEqual(Intent.LOOT, selected.intent)
        self.assertEqual(before, s)
        self.assertIn(757, p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertNotIn(3, p.cleared_floors)
        self.assertIn(757, p.navigation_barriers(s, Intent.EXPLORE))

    def test_unverified_or_nonpickup_clicks_still_cannot_descend(self):
        for case in ("empty", "unseen", "sale", "distant", "threat",
                     "visible-enemy", "explore", "reposition", "batch"):
            with self.subTest(case=case):
                p, s = encounter()
                d = Decision(dict(type="cell", cell=757), "probe", Intent.LOOT)
                if case == "empty": s["objects"] = []
                elif case == "unseen": p.tiles[757]["visible"] = False
                elif case == "sale": s["objects"][0]["for_sale"] = True
                elif case == "distant": s["hero"]["cell"] = 667
                elif case == "threat":
                    p.recent_threats[727] = dict(cell=727, name="gnoll scout")
                elif case == "visible-enemy":
                    s["objects"].append(dict(cell=727, name="gnoll scout"))
                elif case == "explore": d.intent = Intent.EXPLORE
                elif case == "reposition": d.intent = Intent.REPOSITION
                elif case == "batch": d.movement_batch = (728, 757, 787)
                with self.assertRaises(TacticalBlocked) as raised:
                    self.wrapped(p, s, d)
                self.assertEqual("unplanned-stairs", raised.exception.code)
                self.assertIn(757, p.loot)

    def test_explicit_descent_still_requires_progression_pickup(self):
        p, s = encounter()
        s["objects"] = []
        p.loot[727] = dict(cell=727, name="scroll of upgrade",
                           top_item=dict(name="scroll of upgrade", quantity=1))
        # Suspend quiet-room routing so this exercises the mandatory gate,
        # rather than its equally valid earlier collection intervention.
        p.recent_threats[728] = dict(cell=728, name="gnoll scout")
        d = Decision(dict(type="cell", cell=757), "explicit descent", Intent.DESCEND)
        with self.assertRaisesRegex(GameplayBlocked, "upgrade/strength resource"):
            self.wrapped(p, s, d)
        self.assertIn(727, p.loot)
        self.assertNotIn(3, p.cleared_floors)


if __name__ == "__main__":
    unittest.main()
