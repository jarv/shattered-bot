"""Condensed shop/loot visibility oscillation from run 000032, decisions 2054–2056.

This is a deterministic policy fixture, not a reconstruction of runtime memory.
The observed shop step arrived at 931; preparation then selected loot back
toward 892 before peaceful_preparation could mark the arrival exhausted.
"""
import copy
import unittest

from tools.policy_decision import Intent
from tools.policy_geometry import neighbors
from tools.shop_tactics import visit_entrance_shop
from tools.survival_policy import SurvivalPolicy
from tools.test_survival_bot import state


class ShopFrontierArrivalTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 892
        # Preserve the two competing adjacent frontier destinations, but
        # condense the room. Unknown cells are never movement destinations.
        floor = {892: 7, 891: 1, 931: 29, 930: 29}
        s["map"] = {"width": 40, "height": 38, "cells": [
            {"cell": c, "terrain": floor.get(c, 4), "visible": True,
             "observed": True, "effects": []}
            for c in range(40 * 38) if c not in {932, 929}]}
        p = SurvivalPolicy(goal="survival")
        p.update(s)
        p.exhausted.update({892, 891})
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)
        self.assertEqual({"type": "cell", "cell": 931}, d.action)
        return p, s

    def test_arrival_survives_preemption_before_peaceful_preparation(self):
        p, s = self.fixture()
        arrived = copy.deepcopy(s)
        arrived["hero"]["cell"] = 931
        p.update(arrived)
        self.assertIn(931, p.exhausted)
        # Loot preparation may return to the old position. Do not call the
        # peaceful-preparation leaf at the arrival to manufacture its receipt.
        p.cell(892, "loot: finish shortest observed-room collection tour",
               intent=Intent.LOOT)
        p.update(s)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual(891, d.action["cell"])  # Route to 930, not back to 931.
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(set(), p.entrance_doors_checked)

    def test_unexecuted_shop_proposal_is_not_an_arrival(self):
        p, s = self.fixture()
        p.update(s)
        self.assertNotIn(931, p.exhausted)

    def test_other_movement_does_not_certify_shop_scouting(self):
        p, s = self.fixture()
        p.cell(931, "combat: retreat", intent=Intent.RETREAT)
        after = copy.deepcopy(s)
        after["hero"]["cell"] = 931
        p.update(after)
        self.assertNotIn(931, p.exhausted)

    def test_other_floor_does_not_inherit_arrival(self):
        p, s = self.fixture()
        after = copy.deepcopy(s)
        after["depth"] = 7
        after["hero"]["cell"] = 931
        p.update(after)
        self.assertNotIn(931, p.exhausted)

    def test_unseen_arrival_does_not_count_as_scouted(self):
        p, s = self.fixture()
        after = copy.deepcopy(s)
        after["hero"]["cell"] = 931
        next(t for t in after["map"]["cells"] if t["cell"] == 931)["visible"] = False
        p.update(after)
        self.assertNotIn(931, p.exhausted)


if __name__ == "__main__":
    unittest.main()
