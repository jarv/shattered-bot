"""Run 000195 D582: failed purity hypothesis recovered away from its bank.

Reduced public geometry; RewardTrip fields are offline reconstruction pinned to
cbdf19ec8d0033af6100049fa4dfc693189f2281, matching recorded selections 0–581.
No continuation observations after a changed selection are supplied.
"""
import unittest

from tools.policy_decision import TacticalBlocked
from tools.policy_geometry import neighbors
from tools.protected_rewards import RewardTrip
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=595, hp=25, max_hp=25, strength=10, buffs=[])
    route = [666, 702, 738, 774, 811, 848]
    room = {774, 775, 776, 810, 811, 812, 813, 846, 847, 848, 849,
            850, 882, 883, 884, 886, 887, 918, 919, 920, 921, 922,
            923, 924, 954, 955, 956, 957, 958, 959, 960}
    s["map"] = {"width": 36, "height": 48, "cells": [
        dict(cell=c, terrain=5 if c == 738 else 29 if c in
             {702, 774, 811, 848, 884} else 1,
             visible=c in {559, 595, 630, 666, 702, 738},
             observed=True, effects=[])
        for c in sorted(room | set(route) | {559, 595, 630})]}
    s["objects"] = []
    p = verified()
    p.update(s)
    p.loot.update({c: {"cell": c, "name": name} for c, name in
                   [(848, "Chest"), (884, "Chest"), (924, "Skeletal remains")]})
    p.room_journey = RewardTrip("gas", route, 2, room, [848, 884, 924],
                               19, planned_count=2)
    p.puzzle_probe = {"depth": 2, "kind": "gas", "turns": 7}
    return p, s


class FailedGasTourHypothesisTests(unittest.TestCase):
    def test_recovered_failed_hypothesis_does_not_defer_owned_room(self):
        p, s = fixture()
        failure = None
        try:
            decision = p.escape_special_room(s)
        except TacticalBlocked as error:
            failure = error.reason
            decision = None
        self.assertIsNone(failure, "An unstarted failed hypothesis became a return obligation")
        self.assertIsNone(decision)  # Ordinary arbitration resumes, no gas step.
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.puzzle_probe)
        self.assertNotIn("room-journey", p.deferred_room_controllers)
        self.assertEqual({848, 884, 924}, set(p.loot))
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.loot_collection_receipts)

    def test_started_tour_without_protection_still_blocks(self):
        for stage in ("outbound", "return"):
            p, s = fixture()
            p.room_journey.stage = stage
            with self.assertRaises(TacticalBlocked):
                p.room_journey.advance(p, s, [], neighbors)

    def test_actual_protection_still_requires_verified_return(self):
        p, s = fixture()
        s["hero"]["buffs"] = [{"name": "purification barrier",
                             "description": "Turns of immunity remaining: 20."}]
        with self.assertRaises(TacticalBlocked):
            p.room_journey.advance(p, s, [], neighbors)

    def test_unprotected_route_or_interior_is_still_a_return_obligation(self):
        for cell in (702, 848, 884):
            p, s = fixture()
            s["hero"]["cell"] = cell
            with self.assertRaises(TacticalBlocked):
                p.room_journey.advance(p, s, [], neighbors)

    def test_cross_branch_hypothesis_is_not_silently_cancelled(self):
        p, s = fixture()
        s["branch"] = 1
        with self.assertRaises(TacticalBlocked):
            p.room_journey.advance(p, s, [], neighbors)


if __name__ == "__main__":
    unittest.main()
