"""Reduced public corridor from run 000125 decision 596; not runtime memory."""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.priority_resources import choose, targets


class KnownFrostReturnTests(unittest.TestCase):
    def fixture(self):
        route = [684, 635, 586, 537, 488, 439, 490, 441]
        terrains = {684: 6, 586: 29, 488: 29, 490: 5, 441: 29}
        barriers = [444, 494, 544, 594, 644, 694]
        s = {
            "scene": "GameScene", "status": "ready", "modal": False,
            "depth": 2, "branch": 0, "danger_cells": [],
            "hero": {"name": "mage", "cell": 684, "hp": 30, "max_hp": 30,
                     "strength": 11, "buffs": []},
            "inventory": [{"id": "item-5", "name": "potion of frost",
                           "identified": True, "quantity": 1,
                           "actions": ["DROP", "THROW", "DRINK"]}],
            "objects": [], "ui": {"texts": [], "buttons": []},
            "map": {"width": 50, "height": 36, "cells": [
                {"cell": c, "terrain": terrains.get(c, 1) if c in route
                 else 14 if c in barriers + [646] else 4,
                 "visible": c in [684, 635, 586, 537], "observed": True,
                 "effects": []}
                for c in range(50 * 36)]},
        }
        p = MagePolicy()
        p.update(s)
        # Reconstructed cached public sightings, not new visibility or clearance.
        for c in barriers:
            p.tiles[c]["effects"] = ["A wall of magical fire"]
        p.loot[646] = {"cell": 646, "name": "scroll of upgrade",
                       "top_item": {"name": "scroll of upgrade", "identified": True}}
        # Reconstructed source-pinned bookkeeping: the pending unknown-frost
        # return was stranded when intuition identified the carried potion.
        p.frost_view_plan = {"barrier": 444, "view": 441, "steps": 2,
                             "remote": True, "budget": 35}
        p.puzzle_revisit_steps["frost"] = 2
        p.room_attempts.add((2, "puzzle-meal"))
        return s, p

    def test_identification_keeps_guarded_observation_return_actionable(self):
        s, p = self.fixture()
        action = choose(p, s, [])
        self.assertIsNotNone(action, "Known frost must not strand its admitted observation return")
        self.assertEqual({"type": "cell", "cell": 635}, action.action)
        self.assertEqual("explore", action.intent)
        self.assertEqual(3, p.puzzle_revisit_steps["frost"])
        self.assertEqual(441, p.frost_view_plan["view"])
        self.assertIn(646, targets(p))
        self.assertIn(646, p.loot)
        self.assertFalse(p.cleared_floors)
        self.assertIsNone(p.target)
        self.assertNotIn((2, "extinguish", 444), p.room_attempts)
        self.assertEqual("potion of frost", s["inventory"][0]["name"])

    def test_threats_impairment_and_active_work_still_preempt(self):
        for kind in ("enemy", "recent", "danger", "burn", "probe", "stash", "journey"):
            with self.subTest(kind=kind):
                s, p = self.fixture()
                enemies = []
                if kind == "enemy": enemies = [{"name": "rat", "cell": 635}]
                if kind == "recent": p.recent_threats[635] = {"name": "rat", "cell": 635}
                if kind == "danger": s["danger_cells"] = [635]
                if kind == "burn": s["hero"]["buffs"] = [{"name": "burning"}]
                if kind == "probe": p.puzzle_probe = {"kind": "frost"}
                if kind == "stash": p.potion_stash = {"phase": "retrieve"}
                if kind == "journey": p.room_journey = object()
                self.assertIsNone(choose(p, s, enemies))
                self.assertIn(646, p.loot)

    def test_no_bypass_for_unsafe_route_or_exhausted_return(self):
        for changes in ({"trap": "confusion gas trap", "terrain": 18},
                        {"plant": "sorrowmoss"},
                        {"effects": ["A cloud of toxic gas"]},
                        {"terrain": 8}, {"blocked": True}, {"exhausted": True}):
            with self.subTest(changes=changes):
                s, p = self.fixture()
                if changes.get("blocked"): p.blocked.add(635)
                elif changes.get("exhausted"): p.puzzle_revisit_steps["frost"] = 48
                else: p.tiles[635].update(changes)
                self.assertIsNone(choose(p, s, []))
                self.assertIn(646, p.loot)


if __name__ == "__main__":
    unittest.main()
