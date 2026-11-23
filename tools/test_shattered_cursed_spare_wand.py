"""Reduced public D888 inventory/position from run 158; isolated selectors only.

No recorded runtime memory or changed-policy continuation is asserted.
The menu is a separate deterministic UI contract fixture.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_nodes import cleanse
from tools.policy_runtime import Context
from tools.consumable_tactics import discovery_menu
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=420, hp=30, max_hp=30, strength=10,
                     buffs=[{"name": "hungry"}])
    s["map"] = {"width": 34, "height": 39, "cells": [
        {"cell": 420, "terrain": 14, "visible": True, "observed": True,
         "effects": []}]}
    s["inventory"] = [
        {"id": "item-0", "name": "staff of magic missile +1", "equipped": True,
         "identified": True, "curse_known": True, "known_cursed": False,
         "status": "2/5", "actions": ["ZAP", "IMBUE"]},
        {"id": "item-7", "name": "wand of disintegration", "equipped": False,
         "identified": False, "curse_known": True, "known_cursed": True,
         "actions": ["DROP", "THROW", "ZAP"]},
        {"id": "item-9", "name": "scroll of remove curse", "identified": True,
         "actions": ["DROP", "THROW", "READ"]}]
    p = MagePolicy()
    p.update(s)
    return p, s, Context(p, s)


class CursedSpareWandTests(unittest.TestCase):
    def test_quiet_preparation_restores_known_cursed_spare_wand(self):
        p, s, c = fixture()
        self.assertNotIn(s["inventory"][1], p.charged_magic(s))
        d = cleanse(c)
        self.assertIsNotNone(d, "Known cursed spare wand was ignored despite a known cleanse")
        self.assertEqual({"type": "item", "id": "item-9", "action": "READ"}, d.action)
        self.assertEqual("discover-scroll", p.menu_plan)
        # Selecting preparation is not a cleanse receipt or a known charge.
        self.assertTrue(s["inventory"][1]["known_cursed"])
        self.assertNotIn(s["inventory"][1], p.charged_magic(s))
        self.assertFalse(p.loot_collection_receipts)

    def test_spare_cleanse_declines_unsafe_or_unproven_preparation(self):
        for case in ("enemy", "sleeping", "memory", "damage", "warning", "effect",
                     "blind", "unknown", "uncursed", "no-read", "unseen", "modal"):
            with self.subTest(case=case):
                p, s, c = fixture()
                if case in {"enemy", "sleeping"}:
                    c.enemies = [{"name": "gnoll scout", "cell": 421,
                                  "sleeping": case == "sleeping"}]
                if case == "memory": p.recent_threats[421] = {"name": "gnoll scout"}
                if case == "damage": p.unseen_damage_turns = 1
                if case == "warning": s["danger_cells"] = [421]
                if case == "effect": p.tiles[420]["effects"] = ["toxic gas"]
                if case == "blind": s["hero"]["buffs"] = [{"name": "blindness"}]
                if case == "unknown": s["inventory"][1]["curse_known"] = False
                if case == "uncursed": s["inventory"][1]["known_cursed"] = False
                if case == "no-read": s["inventory"][2]["actions"] = ["THROW"]
                if case == "unseen": p.tiles[420]["visible"] = False
                if case == "modal": s["modal"] = True
                self.assertIsNone(cleanse(c))
                self.assertIsNone(p.menu_plan)

    def test_menu_prioritizes_wand_over_unworn_curse_but_not_worn_curse(self):
        for equipped in (False, True):
            with self.subTest(equipped=equipped):
                p, s, c = fixture()
                armor = dict(id="armor", name="mail armor", equipped=equipped,
                             known_cursed=True, curse_known=True)
                s["inventory"].insert(0, armor)
                s["ui"] = {"texts": ["Cleanse an item"], "buttons": [
                    {"id": "armor-button", "label": "mail armor"},
                    {"id": "wand-button", "label": "wand of disintegration"}]}
                d = discovery_menu(p, s)
                self.assertEqual("armor-button" if equipped else "wand-button", d.action["id"])

    def test_existing_equipped_curse_priority_is_preserved(self):
        p, s, c = fixture()
        s["inventory"][0]["known_cursed"] = True
        c.enemies = [{"name": "gnoll scout", "cell": 421}]
        d = cleanse(c)
        self.assertIn("equipped item first", d.reason)

    def test_menu_opens_bag_instead_of_cleansing_uncursed_equipment(self):
        p, s, c = fixture()
        s["ui"] = {"texts": ["Cleanse an item"], "buttons": [
            {"id": "staff", "label": "staff of magic missile +1"},
            {"id": "holster", "label": "magical holster"}]}
        d = discovery_menu(p, s)
        self.assertEqual({"type": "button", "id": "holster"}, d.action)
        self.assertEqual("identify: open item bag", d.reason)
        self.assertTrue(s["inventory"][1]["known_cursed"])


if __name__ == "__main__":
    unittest.main()
