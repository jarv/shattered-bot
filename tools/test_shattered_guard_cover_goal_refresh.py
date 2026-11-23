"""Reduced public run 000172 decision 2554 geometry, not recorded memory.

The copied plan shape comes from an isolated helper reconstruction matching
decisions 2553-2554. No inputs are dispatched or changed-game futures supplied.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.ranged_tactics import choose


def fixture(goal=430):
    terrain = {374: 1, 401: 4, 402: 1, 403: 4, 429: 4, 430: 1,
               431: 4, 457: 4, 458: 6, 459: 4, 484: 20, 485: 1,
               486: 1, 487: 4}
    s = dict(scene="GameScene", status="ready", modal=False, depth=7, branch=0,
             hero=dict(cell=458, hp=14, max_hp=55, name="mage", strength=12,
                       buffs=[dict(name="starving")], talents=[]),
             inventory=[], danger_cells=[], ui=dict(texts=[], buttons=[]),
             objects=[dict(name="prison guard", cell=485,
                           health_bar=[14, 16], status_icons=[])],
             map=dict(width=28, height=53, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
                 for c, t in terrain.items()]))
    p = MagePolicy()
    p.update(s)
    p.ranged_plan = dict(name="prison guard", goal=goal, mode="cover",
                         steps=1, waits=0, hp=14, dot=True, harmful=[])
    return s, p


class GuardCoverGoalRefreshTests(unittest.TestCase):
    def test_moving_guard_invalidates_old_destination_before_arrival(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertTrue(p.enemy_can_see(s, s["objects"][0], 430))
        self.assertFalse(p.enemy_can_see(s, s["objects"][0], 402))
        d = choose(p, s, s["objects"], escape_only=True)
        self.assertEqual(dict(type="cell", cell=430), d.action)
        self.assertEqual(402, p.ranged_plan["goal"])
        self.assertIn("commit", d.reason)
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)

    def test_still_separated_destination_keeps_committed_route(self):
        s, p = fixture(goal=402)
        d = choose(p, s, s["objects"], escape_only=True)
        self.assertEqual(dict(type="cell", cell=430), d.action)
        self.assertEqual(402, p.ranged_plan["goal"])
        self.assertIn("finish committed", d.reason)

    def test_no_safe_replacement_does_not_retain_exposed_destination(self):
        s, p = fixture()
        p.tiles[402]["trap"] = "burning trap"
        self.assertIsNone(choose(p, s, s["objects"], escape_only=True))
        self.assertIsNone(p.ranged_plan)


if __name__ == "__main__":
    unittest.main()
