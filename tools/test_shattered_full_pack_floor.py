"""Reduced public-input regression for run 000004's refused underfoot pickups.

Decisions 2794-2796 show unchanged inventory, persistent pasty, and fresh
can't-carry messages. This tests bookkeeping, not a replacement route or pickup.
"""
import copy
import unittest

from tools.inventory_tactics import observe_accepted, signature
from tools.loot_completion import required_loot
from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision, Intent
from tools.priority_resources import targets
from tools.room_loot import before_room_exit, inventory_context
from tools.test_survival_bot import fully_known, state


class FullPackFloorTests(unittest.TestCase):
    def fixture(self, name="pasty", receipt=True, changed=False, destination=24):
        s = fully_known(state())
        s["depth"] = 7
        s["hero"].update(hp=30, max_hp=55, buffs=[{"name": "starving"}])
        s["objects"] = [{"cell": 24, "name": name,
                         "top_item": {"name": name, "quantity": 1}}]
        p = MagePolicy()
        p.update(s)
        decision = Decision({"type": "cell", "cell": destination},
                            "loot: finish shortest observed-room collection tour",
                            Intent.LOOT)
        for attempt in range(2):
            after = copy.deepcopy(s)
            if receipt:
                after["ui"]["texts"].append(f"You can't carry: {name}.")
                observe_accepted(p, s, decision, after)
            if changed:
                after["inventory"][0]["quantity"] = attempt + 2
            p.last_state = copy.deepcopy(s)
            p.last_decision = decision
            p.update(after)
            s = after
        return s, p

    def test_refusal_defers_item_without_blocking_occupied_floor(self):
        s, p = self.fixture()
        self.assertIsNotNone(p.inventory_pressure)
        self.assertEqual(signature(s), p.inventory_pressure["signature"])
        self.assertNotIn(24, p.blocked)
        self.assertEqual(inventory_context(s), p.room_loot_deferred.get(24))
        self.assertNotIn(24, p.failed_moves)
        self.assertIn(24, required_loot(p))
        self.assertNotIn(24, p.loot_collection_receipts)
        decision = Decision({"type": "cell", "cell": 25},
                            "explore: frontier", Intent.EXPLORE)
        self.assertIsNone(before_room_exit(p, s, decision))
        away = copy.deepcopy(s)
        away["hero"]["cell"] = 25
        self.assertIn(24, p.paths(away))
        p.tiles[24]["trap"] = "observed trap"
        self.assertNotIn(24, p.paths(away))

    def test_mandatory_resources_remain_outstanding(self):
        for name in ("scroll of upgrade", "potion of strength"):
            with self.subTest(name=name):
                s, p = self.fixture(name)
                self.assertNotIn(24, p.blocked)
                self.assertIn(24, targets(p))
                self.assertIn(24, required_loot(p))
                self.assertNotIn(24, p.loot_collection_receipts)

    def test_inventory_change_reopens_ordinary_collection_obligation(self):
        s, p = self.fixture()
        # An isolated alternate public inventory context, not a gameplay replay.
        changed = copy.deepcopy(s)
        changed["inventory"][0]["quantity"] = 2
        decision = Decision({"type": "cell", "cell": 25},
                            "explore: frontier", Intent.EXPLORE)
        selected = before_room_exit(p, changed, decision)
        self.assertIsNotNone(selected)
        self.assertEqual({"type": "cell", "cell": 24}, selected.action)
        self.assertNotIn(24, p.loot_collection_receipts)

    def test_no_receipt_or_changed_inventory_keeps_existing_failure_handling(self):
        for kwargs in ({"receipt": False}, {"changed": True}, {"destination": 25}):
            with self.subTest(kwargs=kwargs):
                _, p = self.fixture(**kwargs)
                self.assertIn(kwargs.get("destination", 24), p.blocked)


if __name__ == "__main__":
    unittest.main()
