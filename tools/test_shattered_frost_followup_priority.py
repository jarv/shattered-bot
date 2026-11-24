"""Condensed public geometry from recording 000228, decisions 281-284.

These are independent selector fixtures, not reconstructed runtime memory.
The extinguished entrance is separated from the hero by observed cold.
"""
import copy
import unittest

from tools.barrier_followup import begin
from tools.policy_geometry import neighbors
from tools.priority_resources import choose, targets
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


COLD = "The air is unnaturally frigid here."
FIRE = "A wall of magical fire; extinguish it."


class FrostFollowupPriorityTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["hero"].update(cell=1073, hp=25, max_hp=25, strength=10)
        terrain = {
            1040: 29, 1041: 4, 1042: 4, 1043: 12, 1044: 4,
            1071: 29, 1072: 29, 1073: 6, 1074: 29, 1075: 29,
            1076: 14, 1077: 14, 1078: 14, 1079: 4,
            1104: 29, 1105: 4, 1106: 29, 1107: 1, 1108: 14,
            1109: 14, 1110: 14, 1111: 4,
            1136: 29, 1137: 4, 1138: 29, 1139: 29, 1140: 14,
            1141: 14, 1142: 14, 1143: 4,
        }
        s["map"] = {"width": 32, "height": 41, "cells": [
            dict(cell=c, terrain=t, visible=True, observed=True,
                 effects=[FIRE] if c in {1076, 1108} else [])
            for c, t in terrain.items()]}
        s["objects"] = [dict(cell=1141, name="scroll of upgrade",
                             top_item=dict(name="scroll of upgrade", identified=True))]
        s["inventory"].append(dict(id="mapping", name="scroll of magic mapping",
                                    identified=True, actions=["READ"]))
        p = verified()
        p.update(s)
        begin(p, s, 1076, neighbors)  # Explicit fixture setup, not a runtime receipt.
        after = copy.deepcopy(s)
        for t in after["map"]["cells"]:
            t["effects"] = [COLD] if t["cell"] in {1074, 1075, 1106, 1107} else []
        p.update(after)
        return after, p

    def test_required_pickup_retains_followup_instead_of_mapping_or_leaving(self):
        s, p = self.fixture()
        self.assertNotIn(1141, p.paths(s))
        d = choose(p, s, [])
        self.assertIsNotNone(d)
        self.assertEqual({"type": "wait"}, d.action)
        self.assertIsNotNone(p.barrier_followup)
        self.assertIn(1141, targets(p))
        self.assertNotIn(1074, p.paths(s))
        self.assertFalse(p.completed_room_rewards)

    def test_independent_clear_snapshot_hands_back_to_real_pickup(self):
        s, p = self.fixture()
        for t in s["map"]["cells"]:
            t["effects"] = []
        p.update(s)
        d = choose(p, s, [])
        self.assertEqual("cell", d.action["type"])
        self.assertNotEqual(1073, d.action["cell"])
        self.assertIn(1141, targets(p))  # Selection is not collection.

    def test_full_selector_keeps_the_required_return_transaction(self):
        s, p = self.fixture()
        d = p.choose(s)
        self.assertEqual({"type": "wait"}, d.action)
        self.assertEqual("priority-progression-pickup", d.controller)
        self.assertIsNotNone(p.barrier_followup)

    def test_observation_hold_is_finite_and_requires_safe_fresh_evidence(self):
        for condition in ("threat", "damage", "warning", "hungry", "unsafe",
                          "unseen", "other_effect", "budget"):
            with self.subTest(condition=condition):
                s, p = self.fixture()
                if condition == "threat":
                    p.recent_threats[1072] = {"name": "rat", "cell": 1072}
                elif condition == "damage":
                    p.unseen_damage_turns = 1
                elif condition == "warning":
                    s["danger_cells"] = [1073]
                elif condition == "hungry":
                    s["hero"]["buffs"] = [{"name": "hungry"}]
                elif condition == "unsafe":
                    p.tiles[1073]["effects"] = [COLD]
                elif condition == "unseen":
                    for c in (1074, 1075, 1106, 1107):
                        p.tiles[c]["visible"] = False
                elif condition == "other_effect":
                    for c in (1074, 1075, 1106, 1107):
                        p.tiles[c]["effects"] = ["A cloud of toxic gas."]
                else:
                    p.barrier_followup["cold_waits"] = 12
                d = choose(p, s, [])
                self.assertTrue(d is None or d.action != {"type": "wait"})
                self.assertIn(1141, targets(p))


if __name__ == "__main__":
    unittest.main()
