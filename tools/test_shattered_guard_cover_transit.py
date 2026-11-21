"""Reduced public geometry from run 000049, decision 2458 (log line 7025).

This is an isolated selector fixture, not recovered original policy memory or a
continuation of the run. No actions are dispatched.
"""
import unittest

from tools.challenge_combat import exposure
from tools.policy_geometry import distance, line_clear
from tools.ranged_tactics import choose
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class GuardCoverTransitTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s.update(depth=7, branch=0)
        s["hero"].update(cell=709, hp=24, max_hp=50, level=7, strength=12,
                         buffs=[{"name": "starving"}, {"name": "barrier",
                         "description": "Shielding remaining: 5."}])
        s["inventory"][0].update(name="staff of magic missile +3", status="0/7",
                                  identified=True, curse_known=True, known_cursed=False)
        # Only retained observed cells, with their recorded terrain values.
        terrain = {
            680: 29, 681: 2, 682: 2, 683: 4, 708: 4, 709: 2, 710: 4,
            711: 4, 717: 4, 718: 5, 719: 4, 735: 4, 736: 2, 737: 6,
            738: 14, 739: 14, 762: 4, 763: 5, 764: 4, 784: 4,
            785: 29, 786: 29, 787: 29, 788: 29, 789: 2, 790: 2,
            791: 4, 811: 4, 812: 29, 813: 29, 814: 29, 815: 29,
            816: 29, 817: 29, 818: 4,
        }
        visible = {680, 681, 682, 683, 708, 709, 710, 735, 736, 737,
                   738, 762, 763, 764}
        s["map"] = {"width": 27, "height": 46, "cells": [
            {"cell": c, "terrain": t, "observed": True, "visible": c in visible, "effects": []}
            for c, t in terrain.items()]}
        s["objects"] = [{"name": "prison guard", "cell": 737,
                          "health_bar": [11, 16], "status_icons": []}]
        p = verified()
        p.update(s)
        return s, p

    def assert_separating_cover(self, s, p, decision):
        self.assertEqual({"type": "cell", "cell": 681}, decision.action)
        self.assertEqual(680, p.ranged_plan["goal"])
        paths = p.paths(s, {737})
        route = p.route(paths, p.ranged_plan["goal"])
        self.assertEqual([709, 681, 680], route)
        for c in route[1:]:
            self.assertEqual(0, exposure(p, s, s["objects"], c,
                                        distance, line_clear)["melee"])
        self.assertFalse(p.enemy_can_see(s, s["objects"][0], route[-1]))

    def test_new_cover_avoids_target_melee_transit(self):
        s, p = self.fixture()
        self.assert_separating_cover(s, p, choose(p, s, s["objects"]))

    def test_committed_cover_rechecks_target_melee_transit(self):
        s, p = self.fixture()
        # A copied plan-shaped input, not originally recorded memory.
        p.ranged_plan = dict(name="prison guard", goal=789, mode="cover",
                             steps=1, waits=0, hp=24, dot=True, harmful=[])
        self.assert_separating_cover(s, p, choose(p, s, s["objects"]))

    def test_blocked_alternative_does_not_admit_the_melee_route(self):
        s, p = self.fixture()
        p.tiles[681]["trap"] = "burning trap"
        p.tiles[682]["trap"] = "burning trap"
        # Probe only the escape selector; do not manufacture a fallback action.
        self.assertIsNone(choose(p, s, s["objects"], escape_only=True))
        self.assertIsNone(p.ranged_plan)


if __name__ == "__main__":
    unittest.main()
