"""Reduced public run 000083 D2001 geometry, not a gameplay replay.

Both retreat squares are admitted and equally far from the awake crab. The
side square adds a step to the same escape route. Choosing the direct square
does not establish a future escape, surprise strike, or quest completion.
"""
import unittest

from tools.great_crab_tactics import choose, escape_route, guard_movement
from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent, TacticalBlocked


class CrabExitDetourTests(unittest.TestCase):
    def fixture(self):
        terrain = {231: 6, 232: 29, 233: 29, 273: 29, 312: 1,
                   311: 5, 310: 1, 309: 29}
        s = {
            "scene": "GameScene", "status": "ready", "modal": False,
            "depth": 4, "branch": 0, "danger_cells": [],
            "hero": {"cell": 232, "hp": 45, "max_hp": 50,
                     "strength": 12, "buffs": [{"name": "wands empowered"}]},
            "inventory": [],
            "objects": [{"cell": 231, "name": "great crab",
                         "health_bar": [18, 21], "status_icons": []}],
            "map": {"width": 40, "height": 38, "cells": [
                {"cell": c, "terrain": t, "observed": True,
                 "visible": c in {231, 232, 233, 273}, "effects": []}
                for c, t in terrain.items()]},
            "ui": {"texts": [], "buttons": []},
        }
        p = MagePolicy()
        p.update(s)
        return s, p

    def test_equal_separation_prefers_direct_escape_over_unvisited_side_square(self):
        s, p = self.fixture()
        # Isolated visit-count variant, not recovered runtime memory.
        p.visits[273] = 5
        self.assertEqual(escape_route(p, s, 233, 232, {231}),
                         [233, 273, 312, 311])
        self.assertEqual(escape_route(p, s, 273, 232, {231}),
                         [273, 312, 311])
        action = choose(p, s, s["objects"])
        self.assertEqual(action.action, {"type": "cell", "cell": 273})
        self.assertEqual(action.intent, Intent.RETREAT)
        guard_movement(p, s, action)
        self.assertIsNone(p.great_crab_plan)

    def test_unknown_or_hazardous_shortcut_is_not_admitted(self):
        for mode in ("unknown", "trap", "plant", "danger", "loot"):
            with self.subTest(mode=mode):
                s, p = self.fixture()
                if mode == "unknown":
                    p.tiles[273]["observed"] = False
                elif mode == "danger":
                    s["danger_cells"] = [273]
                elif mode == "loot":
                    p.loot[273] = {"name": "potion"}
                else:
                    p.tiles[273][mode] = "hazard"
                if mode == "danger":
                    self.assertIsNone(choose(p, s, s["objects"]))
                    continue
                with self.assertRaises(TacticalBlocked):
                    choose(p, s, s["objects"])

    def test_lost_second_exit_does_not_turn_into_a_blocked_attack(self):
        s, p = self.fixture()
        p.tiles[311]["terrain"] = 4
        with self.assertRaises(TacticalBlocked):
            choose(p, s, s["objects"])
        self.assertIsNone(p.best_attack(s, s["objects"][0]))


if __name__ == "__main__":
    unittest.main()
