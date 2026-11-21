"""Condensed public branch conflict in run 000035, decisions 1654–1655.

The entrance has another observed door, but checking one exit expands the
search into deeper chambers. This fixture is not recorded runtime memory.
"""
import unittest

from tools.policy_geometry import neighbors
from tools.shop_tactics import ShopVisitBlocked, visit_entrance_shop
from tools.survival_policy import SurvivalPolicy
from tools.test_survival_bot import state


class ShopBranchBreadthTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 38
        floor = {23: 7, 24: 1, 17: 1, 10: 5, 31: 5, 38: 1, 39: 1}
        s["map"] = {"width": 7, "height": 9, "cells": [
            {"cell": c, "terrain": floor.get(c, 4), "visible": True,
             "observed": True, "effects": []}
            for c in range(63) if c != 46]}
        p = SurvivalPolicy(goal="survival")
        p.update(s)
        p.entrance_cell = 23
        p.entrance_doors_checked.add(31)
        p.exhausted.add(38)
        return p, s

    def test_original_entrance_door_precedes_deeper_branch_frontier(self):
        p, s = self.fixture()
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual(31, d.action["cell"])
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertEqual({31}, p.entrance_doors_checked)
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(0, p.entrance_visit_steps)

    def test_unreachable_shallow_door_does_not_preempt_admitted_frontier(self):
        p, s = self.fixture()
        p.tiles[17].update(terrain=18, trap="shocking trap")
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual(39, d.action["cell"])
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)

    def test_checked_annex_still_opens_next_search_layer(self):
        p, s = self.fixture()
        p.entrance_doors_checked.add(10)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual(39, d.action["cell"])

    def test_search_budget_and_unfinished_shop_are_preserved(self):
        p, s = self.fixture()
        p.entrance_visit_steps = 80
        with self.assertRaises(ShopVisitBlocked):
            visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertNotIn(6, p.shop_visited_floors)


if __name__ == "__main__":
    unittest.main()
