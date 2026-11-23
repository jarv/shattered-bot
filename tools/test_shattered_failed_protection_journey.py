"""Reduced public run 159 D730-D733 contract, not recorded runtime memory.

The dry-run flight route from the D730 public snapshot is [887, 917, 949].
A frost result moves the hero to 855 before an enemy interrupts probe recovery.
No changed-policy continuation or successful pickup is simulated.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import TacticalBlocked
from tools.policy_geometry import neighbors
from tools.room_tactics import Journey
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=855, hp=30, max_hp=30, strength=11,
                     buffs=[{"name": "chilled"}])
    s["inventory"] = []
    s["map"] = {"width": 31, "height": 34, "cells": [
        {"cell": c, "terrain": t, "visible": True, "observed": True,
         "effects": [], **({"trap": "shocking trap"} if c == 949 else {})}
        for c, t in [(855, 1), (887, 29), (917, 29), (949, 18), (795, 1)]]}
    s["objects"] = [
        {"cell": 949, "name": "scroll of upgrade",
         "top_item": {"name": "scroll of upgrade", "identified": True}},
        {"cell": 795, "name": "gnoll scout"}]
    p = MagePolicy()
    p.update(s)
    p.room_journey = Journey("flight", [887, 917, 949], 2)
    p.puzzle_probe = {"depth": 2, "kind": "flight", "turns": 2}
    return p, s


class FailedProtectionJourneyTests(unittest.TestCase):
    def test_enemy_interrupting_failed_potion_recovery_does_not_defer_room(self):
        p, s = fixture()
        failure = None
        decision = None
        try:
            decision = p.escape_special_room(s)
        except TacticalBlocked as error:
            failure = error.reason
        self.assertIsNone(failure, "A failed protection hypothesis became a displaced journey")
        self.assertIsNone(decision)  # Let ordinary combat arbitration continue.
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.room_journey)
        self.assertNotIn("room-journey", p.deferred_room_controllers)
        self.assertIn(949, p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.loot_collection_receipts)
        self.assertEqual(18, p.tiles[949]["terrain"])
        self.assertNotIn(949, p.paths(s))

    def test_actual_protection_still_rejects_displacement(self):
        p, s = fixture()
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 20."}]
        with self.assertRaises(TacticalBlocked):
            p.room_journey.advance(p, s, [], neighbors)

    def test_started_journeys_still_reject_displacement_even_after_buff_expires(self):
        for stage in ("outbound", "return"):
            with self.subTest(stage=stage):
                p, s = fixture()
                p.room_journey.stage = stage
                with self.assertRaises(TacticalBlocked):
                    p.room_journey.advance(p, s, [], neighbors)

    def test_on_route_failed_protection_still_never_steps_onto_trap(self):
        p, s = fixture()
        s["hero"]["cell"] = 887
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)


if __name__ == "__main__":
    unittest.main()
