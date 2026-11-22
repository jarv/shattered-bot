"""Reduced public D1094 geometry from recording 000134, not runtime memory.

Only the two observed doorway approaches and visible flies are retained.
No dispatch or hypothetical changed-policy continuation is performed.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=357, hp=34, max_hp=35, buffs=[{"name": "hungry"}])
    terrain = {c: 29 for c in (
        290, 322, 323, 324, 357, 358, 391, 425, 459, 494, 563)}
    terrain.update({291: 5, 529: 5})
    s["map"] = dict(width=35, height=40, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [
        dict(name="swarm of flies", cell=322, health_bar=[4, 21]),
        dict(name="swarm of flies", cell=323, health_bar=[4, 21],
             status_icons=["chilled"])]
    s["inventory"] = []
    p = MagePolicy()
    p.update(s)
    return p, s


class DoorwayRetreatContactRankingTests(unittest.TestCase):
    def test_recorded_nearer_door_must_not_preempt_unexposed_first_step(self):
        p, s = fixture()
        enemies = s["objects"]
        paths = p.paths(s, {e["cell"] for e in enemies})
        self.assertEqual([357, 358, 324, 290, 291], p.route(paths, 291))
        self.assertEqual([357, 391, 425, 459, 494, 529], p.route(paths, 529))
        self.assertEqual(2, sum(multi.can_attack(p, s, e, 358) for e in enemies))
        self.assertEqual(0, sum(multi.can_attack(p, s, e, 391) for e in enemies))
        d = multi.choose(p, s, enemies)
        self.assertEqual({"type": "cell", "cell": 391}, d.action)
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual(529, p.multi_door_plan["door"])
        self.assertEqual(0, p.multi_door_plan["steps"])
        self.assertIsNone(p.doorway_hold)  # Neither safety nor arrival is certified.
        self.assertFalse(p.loot_collection_receipts)

    def test_lower_contact_does_not_bypass_route_admission(self):
        for blocker in ("trap", "plant", "effect", "loot", "danger", "attempts"):
            with self.subTest(blocker=blocker):
                p, s = fixture()
                if blocker == "trap":
                    p.tiles[391]["trap"] = "burning trap"
                elif blocker == "plant":
                    p.tiles[391]["plant"] = "firebloom"
                elif blocker == "effect":
                    p.tiles[391]["effects"] = ["cloud of toxic gas"]
                elif blocker == "loot":
                    p.loot[391] = dict(cell=391, name="scroll of upgrade")
                elif blocker == "danger":
                    s["danger_cells"] = [391]
                else:
                    p.multi_door_attempts[529] = 2
                multi.doorway_route(p, s, s["objects"], 2)
                self.assertTrue(p.multi_door_plan is None
                                or p.multi_door_plan["door"] != 529)

    def test_single_contact_keeps_existing_nearest_door_ranking(self):
        # Isolated ranking variant, not a later recorded observation.
        p, s = fixture()
        s["objects"][0]["cell"] = 288
        p.update(s)
        self.assertEqual(1, sum(multi.can_attack(p, s, e, 358)
                                for e in s["objects"]))
        d = multi.choose(p, s, s["objects"])
        self.assertEqual({"type": "cell", "cell": 358}, d.action)
        self.assertEqual(291, p.multi_door_plan["door"])

    def test_continuation_budgets_and_proposal_receipts_remain_unchanged(self):
        p, s = fixture()
        multi.choose(p, s, s["objects"])
        self.assertEqual(0, p.multi_door_plan["steps"])
        p.multi_door_plan["steps"] = 12
        self.assertIsNone(multi.doorway_route(p, s, s["objects"], 2))
        self.assertIsNone(p.multi_door_plan)
        self.assertIsNone(p.doorway_hold)


if __name__ == "__main__":
    unittest.main()
