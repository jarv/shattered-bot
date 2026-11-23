"""Reduced public decision-4220 geometry: a necromancer blocks waypoint 481."""
import unittest

from tools.policy_decision import Finished
from tools.policy_geometry import neighbors
from tools.room_tactics import Journey
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class GasReturnDetourTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["depth"] = 9
        s["hero"].update(cell=439, hp=75, max_hp=75, buffs=[{
            "name": "purification barrier",
            "description": "Turns of immunity remaining: 7."}])
        route = [563, 522, 481, 439, 396, 353, 310, 309]
        s["map"] = {"width": 42, "height": 42, "cells": [
            dict(cell=c, terrain=6 if c == 439 else 1,
                 visible=True, observed=True,
                 effects=["A greenish cloud of toxic gas is swirling here."]
                 if c in {439, 396, 353, 310, 309} else [])
            for c in route + [482, 523]]}
        s["objects"] = [{"cell": 481, "name": "necromancer"}]
        s["danger_cells"] = []
        p = verified()
        p.update(s)
        p.room_journey = Journey("gas", route, 9, stage="return")
        return p, s

    def test_blocked_return_uses_budgeted_observed_dry_detour(self):
        p, s = self.fixture()
        try:
            decision = p.room_journey.advance(p, s, s["objects"], neighbors)
        except Finished:
            decision = None
        self.assertIsNotNone(decision, "A blocked waypoint must not exclude the verified dry return detour")
        self.assertEqual({"type": "cell", "cell": 482}, decision.action)
        self.assertEqual([563, 522, 523, 482, 439], p.room_journey.route[:5])
        self.assertEqual(309, p.room_journey.route[-1])
        self.assertEqual("return", p.room_journey.stage)
        self.assertFalse(p.completed_room_rewards)

    def test_unsafe_or_unbudgeted_detours_remain_blocked(self):
        for case in ("occupied", "unseen", "unobserved", "trap", "plant",
                     "gas", "warning", "blocked", "room", "fire-buffer", "short"):
            with self.subTest(case=case):
                p, s = self.fixture()
                tile = p.tiles[482]
                if case == "occupied": s["objects"].append({"cell": 482, "name": "skeleton"})
                elif case == "unseen": tile["visible"] = False
                elif case == "unobserved": tile["observed"] = False
                elif case == "trap": tile["trap"] = "gripping trap"
                elif case == "plant": tile["plant"] = "sorrowmoss"
                elif case == "gas": tile["effects"] = ["cloud of toxic gas"]
                elif case == "warning": s["danger_cells"] = [482]
                elif case == "blocked": p.blocked.add(482)
                elif case == "room": p.room_blocked.add(482)
                elif case == "fire-buffer": p.fire_buffer.add(482)
                else: s["hero"]["buffs"][0]["description"] = "remaining: 5."
                with self.assertRaises(Finished):
                    p.room_journey.advance(p, s, s["objects"], neighbors)

    def test_no_detour_for_other_protection_kinds(self):
        p, s = self.fixture()
        p.room_journey.kind = "flight"
        s["hero"]["buffs"][0]["name"] = "levitating"
        with self.assertRaises(Finished):
            p.room_journey.advance(p, s, s["objects"], neighbors)


if __name__ == "__main__":
    unittest.main()
