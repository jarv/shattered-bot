"""Run 260 decision 1928: reduced public aquarium and enchanted missile staff.

This deterministic fixture is not a reconstruction of recorded runtime memory.
Only the visible water island, dry border, key, fish and exterior are retained.
"""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.priority_resources import choose


class EnchantedAquariumMissileTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        s.update(depth=6, branch=0)
        s["hero"].update(cell=320, hp=43, max_hp=45,
                         buffs=[{"name": "hungry"}, {"name": "wands empowered"}])
        rows = ((14, 14, 14, 14, 1, 4),
                (14, 29, 29, 14, 1, 4),
                (14, 29, 29, 14, 1, 4),
                (14, 14, 14, 14, 1, 4))
        s["map"] = {"width": 33, "height": 43, "cells": [
            {"cell": (y+6)*33+x+19, "terrain": terrain,
             "visible": True, "observed": True, "effects": []}
            for y, row in enumerate(rows) for x, terrain in enumerate(row)]}
        s["objects"] = [
            {"cell": 283, "name": "iron key",
             "top_item": {"name": "iron key", "identified": True, "quantity": 1}},
            {"cell": 285, "name": "giant piranha", "sleeping": True}]
        s["inventory"] = [
            {"id": "item-0", "name": "chilling staff of magic missile +3",
             "identified": True, "curse_known": True, "known_cursed": False,
             "status": "5/7", "actions": ["ZAP"], "quantity": 1}]
        p.update(s)
        return s, p

    def test_enchantment_does_not_hide_known_missile_preparation(self):
        s, p = self.fixture()
        self.assertEqual("aquarium", p.piranha_habitats[251]["profile"])
        self.assertIn(283, p.room_blocked)
        self.assertTrue(p.shot_clear(s, 285))
        before = copy.deepcopy(s)
        decision = choose(p, s, [])
        self.assertIsNotNone(decision, "Enchanted missile staff must retain aquarium clearance")
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"},
                         decision.action)
        self.assertEqual(285, p.target)
        self.assertEqual(before, s)
        self.assertIn(283, p.loot)
        self.assertIn(283, p.room_blocked)
        self.assertFalse(p.loot_collection_receipts)

    def test_identity_charge_and_safety_checks_remain_required(self):
        for case in ("other-imbue", "unknown", "cursed", "empty", "unknown-charge",
                     "hidden-border", "near", "hurt", "warning", "threat", "fish-hidden"):
            with self.subTest(case=case):
                s, p = self.fixture()
                staff = s["inventory"][0]
                if case == "other-imbue": staff["name"] = "chilling staff of frost +3"
                if case == "unknown": staff["identified"] = False
                if case == "cursed": staff["known_cursed"] = True
                if case == "empty": staff["status"] = "0/7"
                if case == "unknown-charge": staff["status"] = "?/7"
                if case == "hidden-border": p.tiles[217]["visible"] = False
                if case == "near": s["hero"]["cell"] = 286
                if case == "hurt": s["hero"]["hp"] = 20
                if case == "warning": s["danger_cells"] = [320]
                if case == "threat": p.recent_threats[221] = {"cell": 221, "name": "crazy thief"}
                if case == "fish-hidden": s["objects"] = s["objects"][:1]
                self.assertIsNone(choose(p, s, []))


if __name__ == "__main__":
    unittest.main()
