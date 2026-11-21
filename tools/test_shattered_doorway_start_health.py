"""Run 000037 D3552: do not start a lure already below its continuation floor.

Condensed public-input fixture, not reconstructed runtime memory. The recorded
route and terrain are retained; omitted tiles are unknown, not invented walls.
No input is dispatched and no later observation is synthesized.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.test_multi_enemy_and_fly_feedback import choke


def recorded_route(hp=13):
    s = state()
    s.update(depth=8, branch=0)
    s["hero"].update(cell=380, hp=hp, max_hp=65)
    terrain = {213: 5, 216: 1, 243: 1, 246: 1, 278: 29,
               279: 29, 312: 29, 346: 29, 380: 29, 413: 29}
    s["map"] = {"width": 34, "height": 41, "cells": [
        {"cell": c, "terrain": t, "observed": True, "visible": c != 213}
        for c, t in terrain.items()]}
    s["objects"] = [
        {"name": "prison guard", "cell": 216, "status_icons": ["terrified"]},
        {"name": "prison guard", "cell": 243},
        {"name": "DM-100", "cell": 278},
        {"name": "skeleton", "cell": 413},
    ]
    p = verified()
    p.update(s)
    return s, p


class DoorwayStartHealthTests(unittest.TestCase):
    def test_recorded_critical_health_cannot_start_unverified_setup(self):
        s, p = recorded_route()
        self.assertIsNone(multi.doorway_route(p, s, s["objects"], 2))
        self.assertIsNone(p.multi_door_plan)
        self.assertFalse(p.multi_door_attempts)
        self.assertIsNone(p.multi_retreat_pending)
        self.assertIsNone(p.doorway_hold)

    def test_start_uses_existing_continuation_health_floor(self):
        for hp, allowed in ((22, False), (23, True)):
            with self.subTest(hp=hp):
                s, p = recorded_route(hp)
                d = multi.doorway_route(p, s, s["objects"], 2)
                self.assertEqual(allowed, d is not None)
                if allowed:
                    self.assertEqual({"type": "cell", "cell": 346}, d.action)
                    self.assertEqual([380, 346, 312, 279, 246, 213],
                                     p.planner.report["multi_enemy_doorway"]["route"])
                    self.assertIsNone(p.doorway_hold)

    def test_healthy_start_still_rejects_hazardous_route(self):
        s, p = recorded_route(40)
        p.tiles[346]["trap"] = "burning trap"
        self.assertIsNone(multi.doorway_route(p, s, s["objects"], 2))
        self.assertIsNone(p.multi_door_plan)

    def test_critical_health_does_not_disable_verified_choke_retreat(self):
        s, p, foes = choke()
        s["hero"].update(hp=13, max_hp=65)
        d = multi.choose(p, s, foes)
        self.assertIsNotNone(d)
        self.assertTrue(p.planner.report["multi_enemy_retreat"]["known_doorway_choke"])
        self.assertIsNone(p.multi_door_plan)


if __name__ == "__main__":
    unittest.main()
