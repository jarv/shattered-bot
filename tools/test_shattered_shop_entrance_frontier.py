"""Entrance scouting ordering derived from run 000031's public decision 2240."""
import unittest

from tools.survival_policy import SurvivalPolicy
from tools.policy_geometry import neighbors
from tools.shop_tactics import visit_entrance_shop
from tools.test_survival_bot import state


class EntranceFrontierTests(unittest.TestCase):
    def fixture(self):
        # Condense the observed conflict: an unchecked northern door and an
        # unfinished southern entrance chamber. Unknown space is not traversed.
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 1290
        s["map"] = {"width": 26, "height": 65, "cells": [
            {"cell": c, "terrain": {1290: 7, 1264: 1, 1238: 5,
                                    1316: 1, 1342: 1}.get(c, 4),
             "visible": True, "observed": True, "effects": []}
            for c in range(65 * 26) if c != 1368]}
        p = SurvivalPolicy(goal="survival")
        p.update(s)
        p.exhausted.add(1290)
        return p, s

    def test_reveal_entrance_before_leaving_through_known_door(self):
        p, s = self.fixture()
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)
        self.assertEqual(1316, d.action["cell"])
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(set(), p.entrance_doors_checked)
        self.assertEqual(1, p.entrance_visit_steps)

    def test_exhausted_frontier_still_allows_door_search(self):
        p, s = self.fixture()
        p.exhausted.add(1342)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertEqual(1264, d.action["cell"])

    def test_trapped_frontier_is_not_a_navigation_alternative(self):
        p, s = self.fixture()
        p.tiles[1342].update(terrain=18, trap="shocking trap")
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: check entrance door before descent", d.reason)


if __name__ == "__main__":
    unittest.main()
