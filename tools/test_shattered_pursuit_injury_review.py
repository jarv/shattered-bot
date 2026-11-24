"""Run 266 D935-936 reduced public inputs; not recovered runtime memory.

The accepted retreat count and prior review are pinned to the recorded reports.
Only this two-input local selector transaction is reconstructed, not the run.
No observations are supplied after a changed decision.
"""
import copy
import unittest

from tools import multi_enemy_tactics as multi
from tools import pursuit_budget as pursuit
from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=681, hp=30, max_hp=30, strength=11)
    terrain = {645: 6, 681: 2, 716: 2, 717: 15, 751: 2,
               752: 2, 787: 2, 788: 2, 823: 2, 859: 5}
    s["map"] = dict(width=35, height=40, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="sewer crab", cell=645),
                    dict(name="mimic", cell=716, health_bar=[17, 21])]
    p = MagePolicy()
    p.update(s)
    # D935 report: four accepted retreats, zero loss, review at move four.
    p.pursuit_retreat_moves = p.pursuit_reassessed_move = 4
    p.pursuit_outcome = dict(hp_loss=0, charge_gain=0, new_sightings=6,
                             seen=set())
    d = multi.choose(p, s, s["objects"])
    d.controller = "multi-threat-retreat"
    return p, s, d


class PursuitInjuryReviewTests(unittest.TestCase):
    def accepted_arrival(self, hp=18):
        p, s, d = fixture()
        # Validate the earlier selected input against D935 before feedback.
        self.assertEqual({"type": "cell", "cell": 717}, d.action)
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual(859, p.multi_door_plan["door"])
        after = copy.deepcopy(s)
        after["hero"].update(cell=717, hp=hp)
        after["objects"][0]["cell"] = 681
        self.assertIsNotNone(multi.observe_accepted(p, s, d, after))
        pursuit.observe_accepted(p, s, d, after)
        p.update(after)
        self.assertEqual(5, p.pursuit_retreat_moves)
        return p, after

    def test_recorded_injury_retires_new_lures_before_periodic_review(self):
        p, s = self.accepted_arrival()
        self.assertEqual(12, p.pursuit_outcome["hp_loss"])
        pursuit.review_outcome(p, s)
        self.assertTrue(p.pursuit_lure_exhausted,
                        "Accepted injury must not wait for retreat number eight")
        multi.choose(p, s, s["objects"])
        self.assertIsNone(p.multi_door_plan,
                          "Failed doorway must not restart with start_hp=18")
        self.assertEqual(1, p.multi_door_attempts[859])
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_preparation_reaches_injury_review_before_multi_retreat(self):
        p, s = self.accepted_arrival()
        self.assertIsNone(p.preparation(s, s["objects"]))
        self.assertTrue(p.pursuit_lure_exhausted)

    def test_undamaged_continuation_is_not_retired(self):
        # Isolated alternative, not a recorded arrival or continuation.
        p, s = self.accepted_arrival(hp=30)
        pursuit.review_outcome(p, s)
        self.assertFalse(p.pursuit_lure_exhausted)
        d = multi.choose(p, s, s["objects"])
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual(30, p.multi_door_plan["start_hp"])

    def test_existing_loss_threshold_is_unchanged(self):
        for loss, exhausted in ((5, False), (6, True)):
            with self.subTest(loss=loss):
                p, s = self.accepted_arrival(hp=30-loss)
                pursuit.review_outcome(p, s)
                self.assertEqual(exhausted, p.pursuit_lure_exhausted)


if __name__ == "__main__":
    unittest.main()
