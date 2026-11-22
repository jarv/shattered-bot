"""Condensed public entrance-search conflict from run 000114.

Decision 2100 (line 6201) continues scouting west/south of entrance 855
although observed doors 762 and 953 are closer to that entrance. This is
a deterministic geometry fixture, not recorded runtime memory.
"""
import unittest

from tools.policy_geometry import neighbors
from tools.shop_tactics import ShopVisitBlocked, visit_entrance_shop
from tools.survival_policy import SurvivalPolicy
from tools.test_survival_bot import state


class ShopEntranceRadiusTests(unittest.TestCase):
    def fixture(self, unknown=978):
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 913
        # Retain the recorded entrance, hero and two nearby doorway positions;
        # condense the grass-filled, continuously connected entrance component.
        floor = {y * 32 + x: 1 for y in range(24, 30) for x in range(17, 27)}
        floor.update({855: 7, 762: 5, 953: 5})
        s["map"] = {"width": 32, "height": 43, "cells": [
            {"cell": c, "terrain": floor.get(c, 4), "visible": True,
             "observed": True, "effects": []}
            for c in range(32 * 43) if c != unknown]}
        p = SurvivalPolicy()
        p.update(s)
        p.entrance_cell = 855
        p.exhausted.add(913)
        return p, s

    def test_near_entrance_door_precedes_outward_frontier_chain(self):
        p, s = self.fixture()
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertIn(d.navigation_route[-1], {762, 953})
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(set(), p.entrance_doors_checked)
        self.assertEqual(0, p.entrance_visit_steps)

    def test_unreachable_doors_do_not_suppress_admitted_frontier(self):
        p, s = self.fixture()
        p.blocked.update({762, 953})
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)

    def test_frontier_nearer_entrance_still_precedes_remote_doors(self):
        p, s = self.fixture(unknown=824)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)

    def test_budget_and_unfinished_shop_remain_mandatory(self):
        p, s = self.fixture()
        p.entrance_visit_steps = 80
        with self.assertRaises(ShopVisitBlocked):
            visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertNotIn(6, p.shop_visited_floors)


if __name__ == "__main__":
    unittest.main()
