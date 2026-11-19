import unittest

from tools.survival_bot import SurvivalPolicy, distance, neighbors
from tools.test_survival_bot import state
from tools.wand_tactics import choose_wand_probe, observe_wand_cast


class WandProbeTests(unittest.TestCase):
    def room(self, kind="corruption"):
        s = state()
        s["map"] = {"width": 15, "height": 15, "cells": [
            {"cell": y*15+x, "terrain": 1, "visible": True} for y in range(1, 14) for x in range(1, 14)]}
        s["hero"]["cell"] = 4*15+4
        item = {"id": "new-wand", "name": f"wand of {kind}", "actions": ["ZAP"],
                "identified": False, "curse_known": False, "known_cursed": False,
                "status": None, "description": "Typically deals _4-10 damage_."}
        s["inventory"].append(item)
        p = SurvivalPolicy()
        p.update(s)
        return s, p, item

    def probe(self, s, p):
        return choose_wand_probe(p, s, s["objects"], distance, neighbors)

    def test_tests_every_wand_effect_including_utility(self):
        for kind in ("magic missile", "frost", "disintegration", "prismatic light", "living earth",
                     "lightning", "blastwave", "corrosion", "fireblast", "transfusion", "regrowth",
                     "warding", "corruption"):
            with self.subTest(kind=kind):
                s, p, item = self.room(kind)
                d = self.probe(s, p)
                self.assertEqual("new-wand", d.action["id"])
                self.assertGreaterEqual(distance(s["hero"]["cell"], p.target, 15), 5)

    def test_known_uncursed_but_unidentified_level_is_not_retested(self):
        s, p, item = self.room()
        item["curse_known"] = True
        self.assertIsNone(self.probe(s, p))

    def test_known_cursed_or_empty_wand_is_not_tested(self):
        for field, value in (("known_cursed", True), ("status", "0/3")):
            s, p, item = self.room()
            item[field] = value
            self.assertIsNone(self.probe(s, p))

    def test_fizzle_is_not_a_successful_curse_test_but_has_backoff(self):
        s, p, item = self.room()
        self.assertIsNotNone(self.probe(s, p))
        self.assertIsNone(self.probe(s, p))
        p.unknown_magic_cooldowns.clear()
        self.assertIsNotNone(self.probe(s, p))
        item["curse_known"] = True
        p.unknown_magic_cooldowns.clear()
        self.assertIsNone(self.probe(s, p))

    def test_revealed_curse_excludes_normal_damage_selection(self):
        s, p, item = self.room("frost")
        self.assertIn(item, p.charged_magic(s))
        item.update(curse_known=True, known_cursed=True)
        self.assertNotIn(item, p.charged_magic(s))

    def test_different_copies_are_tested_separately(self):
        s, p, item = self.room()
        item["curse_known"] = True
        second = dict(item, id="second", curse_known=False)
        s["inventory"].append(second)
        self.assertEqual("second", self.probe(s, p).action["id"])

    def test_danger_low_health_and_magic_immunity_defer_testing(self):
        for scenario in ("warning", "low hp", "immune"):
            s, p, item = self.room()
            if scenario == "warning": s["danger_cells"] = [100]
            if scenario == "low hp": s["hero"]["hp"] = 5
            if scenario == "immune": s["hero"]["buffs"] = [{"name": "magic immunity"}]
            self.assertIsNone(self.probe(s, p))

    def test_direct_wand_gets_useful_first_test_against_distant_enemy(self):
        s, p, item = self.room("frost")
        s["objects"] = [{"name": "sewer crab", "cell": s["hero"]["cell"]+4}]
        self.assertEqual("new-wand", self.probe(s, p).action["id"])
        self.assertEqual(s["objects"][0]["cell"], p.target)

    def test_utility_wand_not_tested_during_active_fight(self):
        s, p, item = self.room()
        s["objects"] = [{"name": "sewer crab", "cell": s["hero"]["cell"]+4}]
        self.assertIsNone(self.probe(s, p))

    def test_normal_combat_uses_spare_wand_even_if_staff_is_empty(self):
        s, p, item = self.room("frost")
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        item.update(curse_known=True, status="2/3")
        enemy = {"name": "sewer crab", "cell": s["hero"]["cell"]+4}
        s["objects"] = [enemy]
        p.update(s)
        self.assertEqual("new-wand", p.best_attack(s, enemy).action["id"])

    def test_successful_probe_allows_immediate_reuse_without_level_id(self):
        s, p, item = self.room("frost")
        self.probe(s, p)
        self.assertGreater(p.unknown_magic_cooldowns[item["name"]], 0)
        item["curse_known"] = True
        observe_wand_cast(p, s)
        self.assertIn(item, p.charged_magic(s))
        self.assertIsNone(p.pending_wand_test)

    def test_empty_probe_does_not_clear_backoff(self):
        s, p, item = self.room("frost")
        self.probe(s, p)
        observe_wand_cast(p, s)
        self.assertNotIn(item, p.charged_magic(s))
