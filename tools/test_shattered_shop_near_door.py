"""Condensed door/frontier starvation from run 000080's entrance shop search.

The recording repeatedly scouts distant entrance-connected frontiers while
observed, admitted doors remain unchecked. This is a deterministic fixture,
not a reconstruction of the original runtime memory or a gameplay replay.
"""
import unittest

from tools.policy_decision import Intent
from tools.policy_geometry import neighbors
from tools.shop_tactics import ShopVisitBlocked, visit_entrance_shop
from tools.survival_policy import SurvivalPolicy
from tools.test_survival_bot import state


class ShopNearDoorTests(unittest.TestCase):
    def test_recorded_first_conflict(self):
        # Decision 2051, log line 5852: accumulated public terrain, with the
        # entrance/exhausted sets reconstructed from validated earlier inputs.
        terrain_groups = {
            4: [765, 766, 767, 768, 769, 818, 903, 910, 912, 952, 959,
                997, 1092, 1093, 1095, 1097, 1098, 1100, 856, 950, 1091, 1096],
            20: [810, 817],
            1: [811, 812, 813, 814, 815, 816, 857, 858, 859, 861, 862,
                863, 864, 904, 905, 906, 907, 908, 909, 911, 953, 954,
                956, 957, 958, 998, 999, 1000, 1001, 1002, 1003, 1004,
                1005, 1006, 1007, 1045, 1046, 1047, 1052, 1053, 1054, 951],
            18: [860], 7: [955], 2: [1048, 1050], 15: [1049, 1051],
            5: [1094, 1044],
        }
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 1001
        s["map"] = {"width": 47, "height": 51, "cells": [
            {"cell": c, "terrain": terrain, "visible": True,
             "observed": True, "effects": []}
            for terrain, cells in terrain_groups.items() for c in cells]}
        p = SurvivalPolicy()
        p.update(s)
        p.entrance_cell = 955
        p.exhausted.update({955, 1001})
        previous = p.paths(s)
        self.assertEqual([1001, 1047, 1094], p.route(previous, 1094))
        d = visit_entrance_shop(p, s, previous, neighbors)
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertEqual(1047, d.action["cell"])
        self.assertEqual(set(), p.entrance_doors_checked)
        self.assertNotIn(6, p.shop_visited_floors)

    def fixture(self, unknown=35):
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 30
        floor = {30: 7, 31: 1, 32: 1, 33: 1, 34: 1, 39: 5}
        s["map"] = {"width": 9, "height": 9, "cells": [
            {"cell": c, "terrain": floor.get(c, 4), "visible": True,
             "observed": True, "effects": []}
            for c in range(81) if c != unknown]}
        p = SurvivalPolicy()
        p.update(s)
        p.exhausted.add(30)
        return p, s

    def test_near_admitted_door_precedes_remote_same_layer_frontier(self):
        p, s = self.fixture()
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertEqual({"type": "cell", "cell": 39}, d.action)
        self.assertEqual(Intent.SHOP, d.intent)
        self.assertEqual(set(), p.entrance_doors_checked)
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(0, p.entrance_visit_steps)  # Proposals do not spend accepted-input budget.

    def test_equal_distance_still_reveals_local_frontier_first(self):
        p, s = self.fixture(unknown=22)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)
        self.assertEqual(31, d.action["cell"])

    def test_unadmitted_door_does_not_preempt_safe_frontier(self):
        p, s = self.fixture()
        p.blocked.add(39)
        previous = p.paths(s)
        self.assertNotIn(39, previous)
        d = visit_entrance_shop(p, s, previous, neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)
        self.assertEqual(31, d.action["cell"])

    def test_search_budget_is_unchanged_and_shop_remains_unfinished(self):
        p, s = self.fixture()
        p.entrance_visit_steps = 80
        with self.assertRaises(ShopVisitBlocked):
            visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertNotIn(6, p.shop_visited_floors)


if __name__ == "__main__":
    unittest.main()
