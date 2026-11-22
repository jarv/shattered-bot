"""Reduced public geometry from run 000124 decision 733, not runtime memory."""
import unittest

from tools.mage_policy import MagePolicy
from tools.ghost_quest import visit_ghost
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import GameplayBlocked


class GhostInactiveTrapReturnTests(unittest.TestCase):
    def fixture(self):
        # The recorded shortest return crosses the publicly triggered trap 675.
        route = [678, 636, 676, 675, 715, 755, 754, 794]
        state = {
            "scene": "GameScene", "status": "ready", "modal": False,
            "depth": 2, "branch": 0, "danger_cells": [],
            "hero": {"name": "mage", "cell": 678, "hp": 30, "max_hp": 30,
                     "strength": 11, "buffs": []},
            "inventory": [], "objects": [], "ui": {"texts": [], "buttons": []},
            "map": {"width": 41, "height": 39, "cells": [
                {"cell": c, "terrain": 1 if c in route else 4,
                 "visible": True, "observed": True, "effects": []}
                for c in range(41 * 39)
            ]},
        }
        trap = next(t for t in state["map"]["cells"] if t["cell"] == 675)
        trap.update(terrain=19, name="Triggered trap", trap="confusion gas trap")
        p = MagePolicy()
        p.update(state)
        # Explicit reconstruction of the relevant quest prior from public sightings.
        p.ghost_quest.update(stage="reward", travel=0, origin_cell=794,
                             origin_depth=2, origin_area=[794],
                             last_cell=918, last_depth=2, return_views=[])
        return state, p

    def visit(self, s, p):
        return visit_ghost(p, s, [], distance, neighbors)

    def test_triggered_trap_name_does_not_exclude_admitted_return(self):
        s, p = self.fixture()
        self.assertTrue(p.walkable(675))
        action = self.visit(s, p)
        self.assertIsNotNone(action, "Inactive trap metadata must not deadlock reward return")
        self.assertEqual({"type": "cell", "cell": 636}, action.action)
        self.assertEqual("reposition", action.intent)
        self.assertEqual("reward", p.ghost_quest["stage"])
        self.assertNotIn("selected", p.ghost_quest)
        self.assertIsNone(p.ghost_menu)

    def test_active_trap_effect_and_plant_still_refuse_transit(self):
        for changes in ({"terrain": 18}, {"effects": ["A cloud of toxic gas"]},
                        {"plant": "sorrowmoss"}):
            with self.subTest(changes=changes):
                s, p = self.fixture()
                p.tiles[675].update(changes)
                with self.assertRaises(GameplayBlocked):
                    self.visit(s, p)
                self.assertEqual("reward", p.ghost_quest["stage"])
                self.assertEqual(0, p.ghost_quest["travel"])

    def test_threats_and_danger_still_preempt_return(self):
        for kind in ("recent", "danger", "enemy"):
            s, p = self.fixture()
            enemies = []
            if kind == "recent":
                p.recent_threats[636] = {"name": "sewer snake", "cell": 636}
            elif kind == "danger":
                s["danger_cells"] = [636]
            else:
                enemies = [{"name": "sewer snake", "cell": 636}]
            self.assertIsNone(visit_ghost(p, s, enemies, distance, neighbors))
            self.assertEqual("reward", p.ghost_quest["stage"])


if __name__ == "__main__":
    unittest.main()
