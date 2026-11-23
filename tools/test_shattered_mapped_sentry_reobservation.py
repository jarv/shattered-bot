"""Run 000199 decision 263: mapped terrain is not a surveyed enclosure.

Reduced public entrance/sentry geometry, with the recorded unseen interior
1313 and perimeter flags. No reward or potion effect is invented.
"""
import copy
import unittest

from tools.descent_potions import begin
from tools.policy_decision import Intent, PlannerStuck
from tools.policy_runtime import Transaction
from tools.preparation_prerequisites import sentry_reobservation
from tools.room_tactics import sentry_geometry
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def entrance():
    s = state()
    s["hero"].update(cell=1121, hp=25, max_hp=25, strength=10, level=2)
    s["map"] = {"width": 39, "height": 36, "cells": []}
    unseen = {1199, 1309, 1313, 1348, 1351, 1352, 1353, 1354, 1355}
    not_visible = unseen | {1237, 1238, 1275, 1276, 1277, 1314, 1315, 1316}
    for y in range(26, 35):
        for x in range(22, 30):
            c = y * 39 + x
            t = 4 if x in {22, 29} or y in {26, 34} else 14
            if x == 28 and 27 <= y <= 33:
                t = 1
            if y in {31, 32, 33} and x == 27:
                t = 1
            t = {1121: 6, 1193: 11, 1195: 26, 1196: 26,
                 1197: 26, 1198: 25, 1276: 11}.get(c, t)
            s["map"]["cells"].append(dict(cell=c, terrain=t, mapped=True,
                observed=c not in unseen, visible=c not in not_visible))
    s["objects"] = [dict(cell=1193, name="red sentry")]
    s["inventory"] += [
        dict(id="turquoise", name="turquoise potion x2", quantity=2,
             identified=False, actions=["DROP", "THROW", "DRINK"]),
        dict(id="indigo", name="indigo potion", quantity=1,
             identified=False, actions=["DROP", "THROW", "DRINK"])]
    p = verified()
    p.update(s)
    return s, p


class MappedSentryReobservationTests(unittest.TestCase):
    def test_mapped_enclosure_does_not_suppress_safe_reobservation(self):
        s, p = entrance()
        before = copy.deepcopy(s)
        try:
            action = begin(p, s)
        except PlannerStuck:
            action = None
        self.assertIsNotNone(action, "Survey the ordinary entry pocket before exhausting discovery")
        self.assertEqual((set(), 0), sentry_geometry(p, s),
                         "Mapped but unobserved cells cannot complete a sentry survey")
        self.assertEqual({"type": "cell", "cell": 1159}, action.action)
        self.assertEqual(Intent.REPOSITION, action.intent)
        self.assertEqual((1121, 1159), action.navigation_route)
        self.assertEqual(before, s)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.completed_room_rewards)
        self.assertEqual(0, p.preparation_scout["accepted"])

    def test_observed_not_currently_visible_geometry_remains_complete(self):
        s, p = entrance()
        for tile in p.tiles.values():
            tile.update(observed=True, visible=False)
        region, delay = sentry_geometry(p, s)
        self.assertIn(1313, region)
        self.assertAlmostEqual(2.1, delay)
        self.assertIsNone(sentry_reobservation(p, s))

    def test_missing_boundary_observation_also_keeps_survey_incomplete(self):
        s, p = entrance()
        for tile in p.tiles.values():
            tile["observed"] = True
        p.tiles[1199].update(observed=False, visible=False)
        self.assertEqual((set(), 0), sentry_geometry(p, s))

    def test_reobservation_keeps_hazard_and_transaction_gates(self):
        for bad in ("trap", "fire", "unobserved", "carpet", "enemy", "danger",
                    "wounded", "budget"):
            with self.subTest(bad=bad):
                s, p = entrance()
                if bad == "trap": p.tiles[1159]["trap"] = "dart trap"
                elif bad == "fire": p.tiles[1159]["effects"] = ["fire"]
                elif bad == "unobserved": p.tiles[1159]["observed"] = False
                elif bad == "carpet": p.tiles[1159]["terrain"] = 14
                elif bad == "enemy": s["objects"].append(dict(cell=1120, name="marsupial rat"))
                elif bad == "danger": s["danger_cells"] = [1121]
                elif bad == "wounded": s["hero"]["hp"] = 5
                else:
                    p.preparation_scout = dict(depth=1, branch=0, target=None,
                        visited=[], accepted=48, stalled=0, status="planning")
                d = sentry_reobservation(p, s)
                if bad in {"trap", "fire", "unobserved", "carpet"}:
                    self.assertTrue(d is None or 1159 not in d.navigation_route)
                else:
                    self.assertIsNone(d)
        s, p = entrance()
        tx = Transaction(p)
        self.assertIsNotNone(sentry_reobservation(p, s))
        tx.rollback()
        self.assertIsNone(getattr(p, "preparation_scout", None))
        self.assertIsNotNone(sentry_reobservation(p, s))


if __name__ == "__main__":
    unittest.main()
