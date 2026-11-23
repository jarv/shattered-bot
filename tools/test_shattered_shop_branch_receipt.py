"""Condensed run 000188 decisions 2540–2545: branch arrival, then search.

Public cell numbers and the accepted target are retained; this is a minimal
fixture, not recorded runtime memory or a claim about undiscovered shop stock.
"""
import copy
import unittest

from tools.objective_planning import observe
from tools.shop_tactics import _track_shop
from tools.survival_policy import SurvivalPolicy
from tools.test_survival_bot import state


class ShopBranchReceiptTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["depth"] = 6
        s["observation_id"] = 5080
        s["hero"]["cell"] = 943
        s["map"] = {"width": 40, "height": 43, "cells": [
            dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
            for c, t in {902: 1, 942: 1, 943: 6, 944: 1, 945: 1,
                         946: 1, 947: 1}.items()]}
        p = SurvivalPolicy()
        p.update(s)
        d = _track_shop(p, s, p.cell(944, "shop: inspect entrance-door branch",
                                    intent="shop"))
        return p, s, d

    def test_accepted_branch_arrival_releases_commitment_before_preemption(self):
        p, s, d = self.fixture()
        after = copy.deepcopy(s)
        after["observation_id"] += 1
        after["hero"]["cell"] = 944
        observe(p, s, d, after)
        self.assertIsNone(p.shop_search_target)
        self.assertEqual(1, p.entrance_visit_steps)
        self.assertEqual(944, p.objective_progress["shop-target:944"]["actual_cell"])
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertEqual(set(), p.entrance_doors_checked)
        self.assertNotIn(944, p.exhausted)
        # Duplicate feedback cannot spend another accepted input.
        observe(p, s, d, after)
        self.assertEqual(1, p.entrance_visit_steps)

    def test_opening_without_arrival_keeps_target(self):
        p, s, d = self.fixture()
        after = copy.deepcopy(s)
        after["observation_id"] += 1
        observe(p, s, d, after)
        self.assertEqual(944, p.shop_search_target["target"])

    def test_other_floor_cannot_release_target_or_earn_progress(self):
        p, s, d = self.fixture()
        after = copy.deepcopy(s)
        after["depth"] = 7
        after["hero"]["cell"] = 944
        observe(p, s, d, after)
        self.assertEqual(944, p.shop_search_target["target"])
        self.assertEqual(0, p.entrance_visit_steps)

    def test_arrival_does_not_cancel_a_different_owned_target(self):
        p, s, d = self.fixture()
        p.shop_search_target = dict(target=776, reason="shop: check entrance door before descent")
        after = copy.deepcopy(s)
        after["observation_id"] += 1
        after["hero"]["cell"] = 944
        observe(p, s, d, after)
        self.assertEqual(776, p.shop_search_target["target"])


if __name__ == "__main__":
    unittest.main()
