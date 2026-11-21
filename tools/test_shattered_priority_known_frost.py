"""Public conflict from run 000036, decision 282 (not runtime memory).

An observed upgrade is beyond eternal fire; the hero already knows frost.
Condensed geometry preserves the three-square throwing distance and barrier.
No game execution or subsequent observation is synthesized.
"""
import unittest

from tools.priority_resources import choose, targets
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class PriorityKnownFrostTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["hero"].update(cell=31, hp=25, max_hp=25)
        s["map"] = {"width": 9, "height": 10, "cells": [
            {"cell": c, "terrain": 4 if c % 9 in {0, 8} or c // 9 in {0, 9}
             else 14 if c // 9 > 6 else 1, "visible": True,
             "observed": True, "effects": ["magical fire"] if c // 9 == 6
             and 0 < c % 9 < 8 else []} for c in range(90)]}
        s["inventory"].append({"id": "item-9", "name": "potion of frost",
                               "identified": True, "actions": ["THROW", "DRINK"]})
        s["objects"] = [{"cell": 76, "name": "scroll of upgrade",
                         "top_item": {"name": "scroll of upgrade", "identified": True}}]
        p = verified()
        p.update(s)
        return s, p

    def test_priority_leaf_can_use_known_frost_without_claiming_pickup(self):
        s, p = self.fixture()
        self.assertNotIn(76, p.paths(s))
        d = choose(p, s, [])
        self.assertIsNotNone(d)
        self.assertEqual({"type": "item", "id": "item-9", "action": "THROW"}, d.action)
        self.assertEqual("frost", d.potion_purpose)
        self.assertGreaterEqual(max(abs(p.target % 9 - 31 % 9),
                                    abs(p.target // 9 - 31 // 9)), 3)
        self.assertIn(76, targets(p))
        self.assertNotIn(1, p.cleared_floors)

    def test_full_selector_no_longer_yields_required_puzzle_to_exploration(self):
        s, p = self.fixture()
        d = p.choose(s)
        self.assertEqual("priority-progression-pickup", d.controller)
        self.assertEqual("THROW", d.action.get("action"))

    def test_threats_warnings_and_impairment_still_veto(self):
        for condition in ("enemy", "memory", "warning", "burning"):
            with self.subTest(condition=condition):
                s, p = self.fixture()
                enemies = []
                if condition == "enemy":
                    enemies = [{"name": "marsupial rat", "cell": 30}]
                if condition == "memory":
                    p.recent_threats[30] = {"name": "marsupial rat", "cell": 30}
                if condition == "warning":
                    s["danger_cells"] = [31]
                if condition == "burning":
                    s["hero"]["buffs"] = [{"name": "burning"}]
                self.assertIsNone(choose(p, s, enemies))
                self.assertIsNone(p.barrier_followup)

    def test_unknown_potion_is_not_thrown_as_frost(self):
        s, p = self.fixture()
        s["inventory"][-1].update(name="crimson potion", identified=False, actions=["THROW"])
        self.assertIsNone(choose(p, s, []))
        self.assertIn(76, targets(p))

    def test_blocked_projectile_does_not_spend_potion(self):
        s, p = self.fixture()
        p.shot_clear = lambda *args: False
        self.assertIsNone(choose(p, s, []))
        self.assertIsNone(p.barrier_followup)

    def test_active_room_workflows_are_not_replaced_by_known_frost(self):
        for field in ("puzzle_probe", "potion_stash", "room_journey"):
            with self.subTest(field=field):
                s, p = self.fixture()
                setattr(p, field, {"active": True})
                self.assertIsNone(choose(p, s, []))
                self.assertIsNone(p.barrier_followup)


if __name__ == "__main__":
    unittest.main()
