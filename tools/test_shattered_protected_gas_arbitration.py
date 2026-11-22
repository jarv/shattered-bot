"""Reduced public decision-241 geometry and observed protection from run 000106."""
import unittest

from tools.room_tactics import Journey
from tools.policy_geometry import neighbors
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.toxic_escape import escape


class ProtectedGasArbitrationTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["hero"].update(cell=776, hp=25, max_hp=25, buffs=[{
            "name": "purification barrier",
            "description": "Turns of immunity remaining: 15."}])
        route = [583, 621, 659, 698, 737, 776, 777, 816]
        s["map"] = {"width": 38, "height": 34, "cells": [
            dict(cell=c, terrain=6 if c == 776 else 29 if c == 698 else 1,
                 observed=True, visible=True,
                 effects=["cloud of toxic gas"] if c in {776, 777, 816} else [])
            for c in route]}
        s["objects"] = []
        p = verified()
        p.update(s)
        p.room_journey = Journey("gas", route, s["depth"], stage="outbound")
        return p, s

    def test_observed_protection_preserves_owned_journey_for_budget_checks(self):
        p, s = self.fixture()
        journey = p.room_journey
        self.assertIsNone(escape(p, s),
                          "Observed purity must not be discarded by unconditional gas escape")
        self.assertIs(p.room_journey, journey)
        decision = journey.advance(p, s, [], neighbors)
        self.assertEqual({"type": "cell", "cell": 777}, decision.action)
        self.assertFalse(p.completed_room_rewards)

    def test_expired_unknown_or_unowned_protection_still_escapes(self):
        for case in ("absent", "expired", "unknown", "unowned", "other-journey"):
            with self.subTest(case=case):
                p, s = self.fixture()
                if case == "absent": s["hero"]["buffs"] = []
                elif case == "expired": s["hero"]["buffs"][0]["description"] = "remaining: 0."
                elif case == "unknown": s["hero"]["buffs"][0]["description"] = ""
                elif case == "unowned": p.room_journey = None
                else: p.room_journey.kind = "flight"
                self.assertEqual({"type": "cell", "cell": 737}, escape(p, s).action)
                self.assertIsNone(p.room_journey)

    def test_short_protection_delegates_to_existing_return_budget(self):
        p, s = self.fixture()
        s["hero"]["buffs"][0]["description"] = "remaining: 8."
        self.assertIsNone(escape(p, s))
        decision = p.room_journey.advance(p, s, [], neighbors)
        self.assertEqual("return", p.room_journey.stage)
        self.assertEqual({"type": "cell", "cell": 737}, decision.action)


if __name__ == "__main__":
    unittest.main()
