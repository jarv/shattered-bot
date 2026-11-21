"""Condensed public geometry from run 000047, decision 250 (log line 687).

The fire and key were last visible at decision 170, log line 465. This
deterministic fixture retains those observations, not original runtime memory.
No action is dispatched and no observation after an alternative is fabricated.
"""
import unittest

from tools.priority_resources import choose, targets
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class MatchingKeyFrostTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["hero"].update(cell=836, hp=25, max_hp=25)
        # Actual coordinates, terrain, and visibility; unrelated map omitted.
        rows = ("#~~~~~~~~#", "###+######", "#~~~~~~~.#", "#~~~~~~~.#",
                "#FFFFFFFP#", "#PPPPPPPP#", "#PPPPPPPP#", "##########")
        terrain = {"#": 4, "~": 29, "+": 5, ".": 1, "F": 14, "P": 14}
        s["map"] = {"width": 34, "height": 33, "cells": [
            {"cell": y*34+x, "terrain": terrain[ch], "observed": True,
             "visible": y <= 25,
             "effects": ["magical fire"] if ch == "F" else []}
            for y, row in enumerate(rows, 24) for x, ch in enumerate(row, 14)]}
        s["map"]["cells"].append(
            {"cell": 653, "terrain": 10, "observed": True, "visible": False})
        s["inventory"].append({"id": "item-6", "name": "potion of frost",
                               "identified": True, "actions": ["THROW", "DRINK"]})
        s["objects"] = [{"cell": 1004, "name": "iron key",
                         "top_item": {"name": "iron key", "identified": True}}]
        p = verified()
        p.update(s)
        return s, p

    def test_matching_key_admits_existing_safe_frost_vantage(self):
        s, p = self.fixture()
        self.assertIn(1004, targets(p))
        self.assertNotIn(1004, p.paths(s))
        d = choose(p, s, [])
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 835}, d.action)
        self.assertEqual((836, 835, 834, 867, 902), d.navigation_route)
        self.assertTrue(all(c in p.paths(s) and c not in p.fire_buffer
                            for c in d.navigation_route))
        self.assertIn(1004, targets(p))
        self.assertIsNone(p.barrier_followup)
        self.assertNotIn(1, p.cleared_floors)

    def test_full_selector_prioritizes_preparation_not_descent(self):
        s, p = self.fixture()
        d = p.choose(s)
        self.assertEqual("priority-progression-pickup", d.controller)
        self.assertEqual({"type": "cell", "cell": 835}, d.action)

    def test_safety_and_workflow_vetoes_remain(self):
        for condition in ("enemy", "memory", "warning", "burning", "unknown",
                          "blocked_shot", "puzzle_probe", "potion_stash", "room_journey"):
            with self.subTest(condition=condition):
                s, p = self.fixture()
                enemies = []
                if condition == "enemy":
                    enemies = [{"name": "marsupial rat", "cell": 835}]
                elif condition == "memory":
                    p.recent_threats[835] = {"name": "marsupial rat", "cell": 835}
                elif condition == "warning":
                    s["danger_cells"] = [836]
                elif condition == "burning":
                    s["hero"]["buffs"] = [{"name": "burning"}]
                elif condition == "unknown":
                    s["inventory"][-1].update(name="turquoise potion",
                                              identified=False, actions=["THROW"])
                elif condition == "blocked_shot":
                    p.shot_clear = lambda *args: False
                else:
                    setattr(p, condition, {"active": True})
                self.assertIsNone(choose(p, s, enemies))
                self.assertIn(1004, targets(p))

    def test_key_without_observed_matching_lock_is_not_obligation(self):
        s, p = self.fixture()
        del p.tiles[653]
        self.assertNotIn(1004, targets(p))
        self.assertIsNone(choose(p, s, []))


if __name__ == "__main__":
    unittest.main()
