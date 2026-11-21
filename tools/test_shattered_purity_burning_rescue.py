"""Reduced public inputs from run 000050, decision 823 (log line 2396).

Isolated selector fixtures, not recovered runtime memory or gameplay replay.
"""
import copy
import unittest

from tools.combat_positioning import rinse_ooze
from tools.policy_decision import Finished
from tools.policy_geometry import distance, neighbors
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class PurityBurningRescueTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s.update(depth=3, branch=0)
        s["hero"].update(cell=339, hp=15, max_hp=30,
                         buffs=[{"name": "burning",
                                 "description": "Turns of burning remaining: 7."}])
        s["objects"] = []
        s["danger_cells"] = []
        # The hero and the next known route cell both have active fire.
        s["map"] = {"width": 27, "height": 39, "cells": [
            {"cell": c, "terrain": t, "visible": True, "observed": True,
             "effects": ["A fire is raging here."] if c in {339, 365} else [],
             **({"trap": "burning trap"} if c == 339 else {})}
            for c, t in [(339, 19), (365, 1), (392, 9), (422, 29)]]}
        s["inventory"] = [
            {"id": "item-8", "name": "waterskin", "status": "0/20",
             "identified": True, "actions": ["DROP", "THROW"]},
            {"id": "item-9", "name": "potion of purity", "quantity": 1,
             "identified": True, "actions": ["DROP", "THROW", "DRINK"]},
            {"id": "item-10", "name": "jade potion", "identified": False,
             "quantity": 1, "actions": ["DROP", "THROW", "DRINK"]}]
        p = verified()
        p.update(s)
        return s, p

    def rescue(self, s, p):
        try:
            return rinse_ooze(p, s, [], distance, neighbors)
        except Finished:
            return None

    def assert_purity(self, s, p, a):
        self.assertIsNotNone(a, "Known purity self-splash must precede burning exhaustion")
        self.assertEqual({"type": "item", "id": "item-9", "action": "THROW"}, a.action)
        self.assertEqual(339, p.target)
        self.assertEqual("emergency", a.potion_purpose)

    def test_fire_blocked_water_uses_known_purity_without_fabricating_receipt(self):
        s, p = self.fixture()
        before = copy.deepcopy(s)
        self.assertEqual({339}, set(p.paths(s)))
        self.assert_purity(s, p, self.rescue(s, p))
        self.assertEqual(before, s)
        self.assertIsNone(p.room_supply_permit)
        self.assertFalse(p.room_supply_spent_elsewhere)
        self.assertFalse(p.cleared_floors)

    def test_priority_tree_reaches_the_same_rescue(self):
        s, p = self.fixture()
        try:
            a = p.choose(s)
        except Finished:
            a = None
        self.assert_purity(s, p, a)
        self.assertEqual("burning-recovery", a.controller)

    def test_airborne_rescue_does_not_assume_water_can_rinse(self):
        s, p = self.fixture()
        s["hero"]["buffs"].append({"name": "levitation"})
        self.assert_purity(s, p, self.rescue(s, p))

    def test_unknown_or_unthrowable_potion_does_not_authorize_rescue(self):
        for change in ({"name": "golden potion", "identified": False},
                       {"identified": False},
                       {"actions": ["DRINK"]}):
            s, p = self.fixture()
            s["inventory"][1].update(change)
            self.assertIsNone(self.rescue(s, p))

    def test_adjacent_safe_water_preserves_purity(self):
        s, p = self.fixture()
        p.tiles[340] = {"cell": 340, "terrain": 29, "visible": True, "observed": True}
        self.assertEqual({"type": "cell", "cell": 340}, self.rescue(s, p).action)

    def test_well_pit_and_active_plate_do_not_certify_a_self_splash(self):
        for terrain in (0, 24, 18):
            s, p = self.fixture()
            p.tiles[339]["terrain"] = terrain
            self.assertIsNone(self.rescue(s, p))


if __name__ == "__main__":
    unittest.main()
