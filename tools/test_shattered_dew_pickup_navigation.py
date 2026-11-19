"""Public depth-three dew refusal must not poison floor reachability."""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision, Intent
from tools.room_loot import before_room_exit, inventory_context
from tools.loot_completion import required_loot
from tools.test_survival_bot import state, fully_known


class DewPickupNavigationTests(unittest.TestCase):
    def fixture(self, name="dewdrop"):
        # Reduced from decisions 881-883: full HP, full skin, persistent
        # loose dew underfoot after two accepted same-cell pickup clicks.
        s = fully_known(state())
        s["depth"] = 3
        s["inventory"].append({"id": "skin", "name": "waterskin",
                               "status": "20/20", "quantity": 1,
                               "actions": ["DRINK"]})
        s["objects"] = [{"cell": 24, "name": name,
                         "top_item": {"name": name, "quantity": 1}}]
        p = MagePolicy()
        p.update(s)
        for _ in range(2):
            p.last_state = copy.deepcopy(s)
            p.last_decision = Decision({"type": "cell", "cell": 24},
                                      "loot: collect/open", Intent.LOOT)
            p.update(copy.deepcopy(s))
        return s, p

    def test_refused_dew_defers_pickup_not_floor_or_frontier(self):
        s, p = self.fixture()
        self.assertNotIn(24, p.blocked)
        self.assertEqual(inventory_context(s), p.room_loot_deferred.get(24))
        self.assertTrue(p.walkable(24))
        p.tiles[24]["trap"] = "observed trap"
        self.assertFalse(p.walkable(24))
        p.tiles[24].pop("trap")
        self.assertIn(24, required_loot(p))  # Never certify collection.
        self.assertNotIn(24, p.loot_collection_receipts)
        decision = Decision({"type": "cell", "cell": 25},
                            "explore: frontier", Intent.EXPLORE)
        self.assertIsNone(before_room_exit(p, s, decision))
        s["hero"]["cell"] = 25
        self.assertIn(24, p.paths(s))  # An observed way back stays available.

    def test_real_failed_step_still_blocks(self):
        s, p = self.fixture()
        for _ in range(2):
            p.last_state = copy.deepcopy(s)
            p.last_decision = Decision({"type": "cell", "cell": 25},
                                      "explore: frontier", Intent.EXPLORE)
            p.update(copy.deepcopy(s))
        self.assertIn(25, p.blocked)

    def test_progression_pickups_are_not_waived(self):
        for name in ("potion of strength", "scroll of upgrade"):
            with self.subTest(name=name):
                s, p = self.fixture(name)
                self.assertNotIn(24, p.room_loot_deferred)
                self.assertIn(24, required_loot(p))


if __name__ == "__main__":
    unittest.main()
