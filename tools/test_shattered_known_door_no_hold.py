"""Reduced public D1116 geometry from run 000192, not recovered runtime memory.

The isolated selector probe matches the recorded first step and door on the
original policy. No subsequent observations are fed after changed planning.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.multi_enemy_tactics import choose, doorway_route, single_file
from tools.policy_geometry import neighbors
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 4
    s["hero"].update(cell=344, hp=21, max_hp=35, strength=11,
                     buffs=[{"name": "starving"}, {"name": "barrier"}])
    # Observed northern portion of the recording's 42-column map. Other
    # terrain is omitted, never filled in as floor or as a wall.
    terrain = {
        4: (137,138,139,140,141,142,143,144,175,176,177,178,179,186,
            214,215,216,217,228,229,230,256,261,262,263,272,
            296,297,298,300,301,302,303,304,305,307,308,309,310,
            311,312,338,345,346,380,391,392,422,429,430,431),
        2: (180,181,182,183,184,185,218,219,220,222,223,224,225,226,
            227,260,264,265,266,267,268,269,271,344,381,383,425),
        5: (221,270,299,306),
        29: (257,258,259,342,343,347,348,349,384,385,388,389,390,
             426,427,432),
        15: (313,382,423),
        12: (314,),
        1: (339,340,341,386,428),
        10: (350,),
        6: (387,),
        7: (424,),
    }
    s["map"] = {"width": 42, "height": 38, "cells": [
        {"cell": c, "terrain": t, "observed": True, "visible": True,
         "effects": []} for t, cells in terrain.items() for c in cells]}
    s["objects"] = [{"cell": 387, "name": "swarm of flies"},
                    {"cell": 388, "name": "swarm of flies"}]
    p = MagePolicy()
    p.update(s)
    return s, p


class KnownDoorNoHoldTests(unittest.TestCase):
    def test_known_bypass_does_not_start_doomed_door_commitment(self):
        s, p = fixture()
        holds = [c for c in neighbors(299, 42, 38) if p.walkable(c)]
        self.assertTrue(holds)
        self.assertTrue(all(not single_file(p, s, s["objects"], c)
                            for c in holds))
        decision = choose(p, s, s["objects"])
        self.assertEqual({"type": "cell", "cell": 343}, decision.action)
        self.assertIsNone(p.multi_door_plan,
                          "Known non-choke door must not create a commitment")
        report = p.planner.report["multi_enemy_retreat"]
        self.assertEqual([344, 343], report["route"])
        self.assertEqual(0, report["attackers_next"])
        self.assertEqual(1, report["endpoint_approach_slots"])
        self.assertFalse(report["known_doorway_choke"])
        self.assertIsNone(p.doorway_hold)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_unknown_perimeter_keeps_observation_only_door_setup(self):
        s, p = fixture()
        # An independently reduced incomplete-view case, not a continuation.
        p.tiles.pop(256)
        decision = doorway_route(p, s, s["objects"], 2)
        self.assertEqual({"type": "cell", "cell": 343}, decision.action)
        self.assertEqual(299, p.multi_door_plan["door"])
        self.assertIsNone(p.doorway_hold)  # Arrival still must verify a hold.

    def test_ground_only_observation_first_behavior_is_unchanged(self):
        s, p = fixture()
        for enemy in s["objects"]:
            enemy["name"] = "gnoll scout"
        decision = doorway_route(p, s, s["objects"], 2)
        self.assertEqual({"type": "cell", "cell": 343}, decision.action)
        self.assertEqual(299, p.multi_door_plan["door"])
        self.assertIsNone(p.doorway_hold)


if __name__ == "__main__":
    unittest.main()
