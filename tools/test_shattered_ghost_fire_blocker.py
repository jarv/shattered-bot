"""Reduced public geometry from decision 852; quest priors are reconstructed."""
import unittest
from tools.mage_policy import MagePolicy
from tools.ghost_quest import visit_ghost
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import GameplayBlocked


def fixture():
    floors = {509, 510, 544, 579, 611, 612, 613, 614}
    s = {
        "scene": "GameScene", "status": "ready", "modal": False,
        "depth": 2, "branch": 0, "danger_cells": [],
        "evaluation_stats": {"elapsed_turns": 826.25},
        "hero": {"name": "mage", "cell": 544, "hp": 30, "max_hp": 30,
                 "strength": 11, "buffs": [{"name": "hungry"}]},
        "inventory": [], "objects": [], "ui": {"texts": [], "buttons": []},
        "map": {"width": 35, "height": 44, "cells": [
            {"cell": c, "terrain": 6 if c == 613 else 1 if c in floors else 4,
             "observed": True, "visible": True,
             "effects": ["A fire is raging here."] if c == 613 else []}
            for c in range(35 * 44)]},
    }
    p = MagePolicy()
    p.update(s)
    p.ghost_quest.update(stage="reward", origin_cell=611, origin_depth=2,
                         origin_area=[611, 612], return_views=[], travel=0)
    # Public-clock reconstruction has ample current satiety, not an early meal.
    p.hunger_projection = {"turn": 826.25, "phase": "hungry",
                           "remaining": 72, "foods": {}}
    return s, p


class GhostFireBlockerTests(unittest.TestCase):
    def visit(self, s, p):
        try:
            return visit_ghost(p, s, [], distance, neighbors)
        except GameplayBlocked:
            return None

    def test_fire_disconnection_is_not_a_completed_search(self):
        s, p = fixture()
        d = self.visit(s, p)
        self.assertIsNotNone(d, "Visible fire blocking reward return needs bounded safe observation")
        self.assertEqual({"type": "wait"}, d.action)
        self.assertEqual("reward", p.ghost_quest["stage"])
        self.assertEqual([], p.ghost_quest["return_views"])
        self.assertEqual(0, p.ghost_quest["travel"])
        self.assertNotIn(613, p.paths(s))
        self.assertTrue(p.tiles[613]["effects"])
        self.assertEqual(1, p.hazard_recheck_waits)

    def test_refusals_preserve_terminal_exhaustion(self):
        for case in ("budget", "steps", "flammable", "unknown", "near_fire",
                     "mixed", "poison", "danger", "enemy", "unrelated", "hunger"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "budget": p.hazard_recheck_waits = 16
                if case == "steps": p.hazard_recheck_steps = 60
                if case == "flammable": p.tiles[544]["terrain"] = 14
                if case == "unknown": p.tiles[509]["visible"] = False
                if case == "near_fire": p.tiles[579]["effects"] = ["A fire is raging here."]
                if case == "mixed": p.tiles[613]["effects"].append("Unknown hazard")
                if case == "poison": s["hero"]["buffs"].append({"name": "poison"})
                if case == "danger": s["danger_cells"] = [544]
                if case == "enemy": s["objects"] = [{"name": "sewer snake", "cell": 510, "health_bar": [8, 8]}]
                if case == "unrelated": p.tiles[612]["terrain"] = 4
                if case == "hunger": p.hunger_projection["remaining"] = 30
                self.assertIsNone(self.visit(s, p))
                self.assertEqual("reward", p.ghost_quest["stage"])

    def test_fresh_clearance_resumes_return_without_crediting_reward(self):
        s, p = fixture()
        next(t for t in s["map"]["cells"] if t["cell"] == 613)["effects"] = []
        p.update(s)
        d = self.visit(s, p)
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 579}, d.action)
        self.assertEqual("reward", p.ghost_quest["stage"])
        self.assertIsNone(p.ghost_menu)


if __name__ == "__main__":
    unittest.main()
