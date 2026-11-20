"""Reduced public-input fixture for run 000019 decisions 1657 and 1669.

This is a selector fixture, not recovered runtime memory or a gameplay replay.
The small floor patch retains the recorded coordinates and visible empty
last-seen NPC cell; walls close the synthetic map for readiness checks.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.ghost_quest import visit_ghost
from tools.policy_geometry import distance, neighbors


class VisibleEmptyGhostMemoryTests(unittest.TestCase):
    def fixture(self):
        floors = {690, 691, 731, 732, 772}
        state = {
            "scene": "GameScene", "status": "ready", "modal": False,
            "depth": 4, "branch": 0, "danger_cells": [],
            "hero": {"cell": 772, "hp": 45, "max_hp": 45,
                     "strength": 12, "buffs": []},
            "inventory": [{
                "id": "item-0", "name": "staff of magic missile +3",
                "status": "3/7", "actions": ["ZAP", "IMBUE"],
                "equipped": True, "identified": True,
            }],
            "map": {"width": 40, "height": 39, "cells": [
                {"cell": c, "terrain": 1 if c in floors else 4,
                 "visible": True, "observed": True, "effects": []}
                for c in range(40 * 39)
            ]},
            "objects": [{"name": "sad ghost", "cell": 731}],
            "ui": {"texts": [], "buttons": []},
        }
        policy = MagePolicy()
        policy.update(state)
        absent = copy.deepcopy(state)
        absent["objects"] = []
        policy.update(absent)
        self.assertEqual(policy.ghost_quest["last_cell"], 731)
        return absent, policy

    def visit(self, state, policy):
        return visit_ghost(policy, state, [], distance, neighbors)

    def test_visible_empty_memory_does_not_start_recorded_neighbor_orbit(self):
        state, policy = self.fixture()
        before = copy.deepcopy(policy.ghost_quest)
        self.assertIsNone(self.visit(state, policy))
        self.assertEqual(policy.ghost_quest, before)
        self.assertIsNone(policy.ghost_menu)

    def test_adjacent_empty_memory_does_not_select_another_neighbor(self):
        state, policy = self.fixture()
        state["hero"]["cell"] = 691
        policy.update(state)
        self.assertIsNone(self.visit(state, policy))

    def test_unseen_memory_remains_an_approach_prior(self):
        state, policy = self.fixture()
        next(t for t in state["map"]["cells"] if t["cell"] == 731)["visible"] = False
        policy.update(state)
        action = self.visit(state, policy)
        self.assertIsNotNone(action)
        self.assertIn("last observed Sad Ghost", action.reason)
        self.assertIsNone(policy.ghost_menu)

    def test_distant_memory_still_allows_bounded_area_approach(self):
        state, policy = self.fixture()
        state["hero"]["cell"] = 690
        # Move the remembered prior two cells away on the same synthetic patch.
        policy.ghost_quest["last_cell"] = 732
        policy.update(state)
        self.assertIsNotNone(self.visit(state, policy))
        self.assertIsNone(policy.ghost_menu)

    def test_fresh_visible_ghost_still_allows_dialogue(self):
        state, policy = self.fixture()
        state["objects"] = [{"name": "sad ghost", "cell": 731}]
        policy.update(state)
        self.assertEqual(self.visit(state, policy).action,
                         {"type": "cell", "cell": 731})
        self.assertEqual(policy.ghost_menu["stage"], "dialogue")

    def test_pending_reward_is_not_waived_by_empty_last_seen_cell(self):
        state, policy = self.fixture()
        policy.ghost_quest["stage"] = "reward"
        action = self.visit(state, policy)
        self.assertIsNotNone(action)
        self.assertIn("first Sad Ghost encounter area", action.reason)
        self.assertEqual(policy.ghost_quest["stage"], "reward")


if __name__ == "__main__":
    unittest.main()
