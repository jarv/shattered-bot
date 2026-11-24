"""Run 227, decisions 276--277: an opened chest exposes a skeleton key.

Reduced public fixture, not reconstructed runtime memory. The heap has a
top_item receipt; its name must not make it unopened skeletal remains.
"""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.room_loot import before_room_exit
from tools.policy_decision import Decision, Intent
from tools.region_navigation import choose


class SkeletonKeyHeapTests(unittest.TestCase):
    def fixture(self, name="skeleton key", top_item=True):
        s, p = arena()
        s["hero"].update(cell=40, hp=25, max_hp=25)
        obj = {"cell": 41, "name": name}
        if top_item:
            obj["top_item"] = {"name": name, "quantity": 1, "identified": False}
        s["objects"] = [obj]
        p.update(s)
        return s, p

    def test_opened_chest_item_is_admitted_for_ordinary_pickup(self):
        s, p = self.fixture()
        original = copy.deepcopy(s)
        self.assertNotIn(41, p.room_blocked,
                         "A public skeleton key heap is not a crypt container")
        self.assertTrue(p.walkable(41))
        paths = p.paths(s)
        d = choose(p, s, paths, p.room_skipped)
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 41}, d.action)
        tour = before_room_exit(p, s, Decision(
            {"type": "cell", "cell": 42}, "explore: leave", intent=Intent.EXPLORE))
        self.assertIsNotNone(tour)
        self.assertEqual({"type": "cell", "cell": 41}, tour.action)
        self.assertIn(41, p.loot)
        self.assertFalse(p.loot_collection_receipts)
        self.assertEqual(0, p.keys.get("skeleton", 0))
        self.assertEqual(original, s)

    def test_real_containers_and_unconfirmed_names_stay_excluded(self):
        from tools.survival_policy import SurvivalPolicy
        for name in ("skeleton", "tomb", "crystal chest", "skeleton key"):
            with self.subTest(name=name):
                s, _ = self.fixture(name, top_item=False)
                if name == "skeleton":
                    s["objects"][0]["description"] = "Old bones lying on the floor."
                # Base recognition, before Mage's separately guarded crypt
                # preparation is allowed to admit actual remains.
                p = SurvivalPolicy()
                p.update(s)
                self.assertFalse(p.walkable(41))

    def test_item_does_not_waive_hazard_or_mimic_admission(self):
        for kind in ("trap", "effects", "warning-container"):
            with self.subTest(kind=kind):
                s, p = self.fixture()
                if kind == "warning-container":
                    p.loot[41]["description"] = "It feels off. Opening it is a bad idea."
                elif kind == "trap":
                    p.tiles[41].update(terrain=18, trap="toxic gas trap")
                else:
                    p.tiles[41]["effects"] = ["toxic gas"]
                self.assertFalse(p.walkable(41))


if __name__ == "__main__":
    unittest.main()
