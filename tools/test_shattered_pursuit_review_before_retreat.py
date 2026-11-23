"""Reduced public run 000196 D1331 geometry, not a gameplay continuation.

The 39 accepted retreats are public receipts through D1330 (line 3867).
No hidden enemy state or post-selection observations are supplied.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=214, hp=40, max_hp=40, strength=12,
                     buffs=[{"name": "hungry"}])
    terrain = {173: 4, 174: 12, 175: 12, 213: 20, 214: 29, 215: 29,
               216: 29, 253: 1, 254: 29, 255: 29, 256: 29}
    s["map"] = dict(width=40, height=40, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="swarm of flies", cell=215, health_bar=[2, 21]),
                    dict(name="swarm of flies", cell=216, health_bar=[6, 21]),
                    dict(name="slime", cell=256)]
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +3", status="2/7",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["ZAP", "IMBUE", "UNEQUIP"],
        description="Each bolt deals 5-14 damage.")]
    p = verified()
    p.update(s)
    p.pursuit_retreat_moves = 39
    return p, s


class PursuitReviewBeforeRetreatTests(unittest.TestCase):
    def test_closing_fronts_cannot_starve_accepted_pursuit_review(self):
        p, s = fixture()
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))
        self.assertIsNone(p.preparation(s, s["objects"]))
        self.assertTrue(p.pursuit_lure_exhausted,
                        "Emergency retreat bypassed the accepted-pursuit outcome review")
        self.assertEqual(39, p.pursuit_reassessed_move)
        self.assertIsNone(multi.doorway_route(p, s, s["objects"], 3))
        self.assertIsNone(p.multi_door_plan)
        self.assertEqual("2/7", s["inventory"][0]["status"])
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_unspent_pursuit_is_not_exhausted(self):
        p, s = fixture()
        p.pursuit_retreat_moves = 4
        self.assertIsNone(p.preparation(s, s["objects"]))
        self.assertFalse(p.pursuit_lure_exhausted)
        self.assertEqual(4, p.pursuit_reassessed_move)

    def test_existing_loss_threshold_also_applies_before_retreat(self):
        p, s = fixture()
        p.pursuit_retreat_moves = 4
        p.pursuit_outcome = {"hp_loss": 8}
        p.preparation(s, s["objects"])
        self.assertTrue(p.pursuit_lure_exhausted)


if __name__ == "__main__":
    unittest.main()
