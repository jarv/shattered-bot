"""Reduced selector fixture from the recorded sleeping-crab frontier reversal."""
from collections import Counter
import copy
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.priority_resources import choose as priority_pickup, targets
from tools.loot_completion import required_loot
from tools.test_survival_bot import state


class SleepingFrontierCommitmentTests(unittest.TestCase):
    def fixture(self):
        # Decisions 1056-1057: the crab at 194 is publicly magically asleep;
        # showing it at 155 switches away from the committed region planner.
        # Reduce the distant branch to 158 and expose two explicit viewing tasks.
        s = state()
        s["depth"] = 3
        s["hero"].update(cell=155, hp=9, max_hp=35)
        floors = {119, 155, 156, 157, 158, 194}
        s["map"] = {"width": 35, "height": 7, "cells": [
            {"cell": c, "terrain": 1 if c in floors else 4,
             "visible": True, "observed": True}
            for c in range(245)]}
        crab = {"cell": 194, "name": "sewer crab", "sleeping": True,
                "status_icons": ["magical sleep"], "health_bar": [2, 21]}
        s["objects"] = [crab]
        p = MagePolicy()
        p.update(s)
        p.exploration_goal = {"kind": "frontier", "cell": 158,
                              "steps": 1, "edges": Counter()}
        return s, p, crab

    def probe(self, s, p, enemies):
        report = p.exploration_report
        with patch.object(p, "exploration_report", side_effect=lambda st, paths:
                          dict(report(st, paths), unexplored_frontiers=[119, 158],
                               unopened_doors=[])):
            return p.explore(s, enemies)

    def test_sleeping_visibility_does_not_reverse_committed_frontier(self):
        s, p, crab = self.fixture()
        # Independent, undispatched probes, not a simulated observation sequence.
        hidden_s, hidden_p = copy.deepcopy((s, p))
        hidden_s["objects"] = []
        without = self.probe(hidden_s, hidden_p, [])
        visible = self.probe(s, p, [crab])
        self.assertEqual({"type": "cell", "cell": 156}, without.action)
        self.assertEqual(without.action, visible.action)
        self.assertEqual(158, p.exploration_goal["cell"])
        self.assertNotIn(194, p.paths(s, {crab["cell"]}))

    def test_active_or_mixed_enemies_keep_existing_selector_admission(self):
        s, p, crab = self.fixture()
        active = dict(crab, sleeping=False, status_icons=[])
        for enemies in ([active], [crab, active]):
            self.assertFalse(p.systematic_exploration_enabled(s, enemies))
        p.engine = "planner"
        self.assertFalse(p.systematic_exploration_enabled(s, [crab]))

    def test_hazard_and_progression_pickup_constraints_remain(self):
        s, p, crab = self.fixture()
        p.tiles[156]["trap"] = "observed trap"
        self.assertFalse(p.walkable(156))
        self.assertNotIn(158, p.paths(s, {194}))
        p.tiles[156].pop("trap")
        for name in ("potion of strength", "scroll of upgrade"):
            with self.subTest(name=name):
                q = copy.deepcopy(p)
                obj = {"cell": 156, "name": name,
                       "top_item": {"name": name, "quantity": 1}}
                q.loot[156] = obj
                s["objects"] = [crab, obj]
                # Mandatory pickup's higher-priority leaf retains its existing
                # enemy veto. Exploration cannot waive the outstanding item.
                self.probe(s, q, [crab])
                self.assertIn(156, targets(q))
                self.assertIn(156, required_loot(q))
                self.assertIsNone(priority_pickup(q, s, [crab]))
                decision = priority_pickup(q, s, [])
                self.assertEqual(Intent.LOOT, decision.intent)
                self.assertEqual(156, decision.action["cell"])
                self.assertNotIn(156, q.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
