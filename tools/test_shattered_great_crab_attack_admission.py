"""Reduced public fixture from run 000009, decision 1329 (log line 3825).

This tests shared attack admission, not reconstructed runtime memory or a
successful replacement tactic. Doorway surprise remains a separate workflow.
"""
"""Reduced fixture from run 000009 decision 1329, not runtime reconstruction.

Coordinates, health, empty staff and awake crab are public recorded inputs.
Charged/sleeping/invisible variants are isolated admission probes, not replay.
No replacement action, survival, quest success or safe route is asserted.
"""
import unittest

from tools.mage_policy import MagePolicy


class GreatCrabAttackAdmissionTests(unittest.TestCase):
    def fixture(self, charged=False):
        # The recorded hero is below an open door occupied by an awake crab.
        # Only the local cells needed by these selector probes are retained.
        s = {
            "scene": "GameScene", "status": "ready", "modal": False,
            "depth": 4, "branch": 0, "danger_cells": [],
            "hero": {"name": "mage", "cell": 1182, "hp": 39,
                     "max_hp": 40, "strength": 10, "buffs": []},
            "inventory": [{
                "id": "item-0", "name": "staff of magic missile +3",
                "description": "This _tier-1_ melee weapon deals _4-12 damage_ "
                               "and requires _8 strength_ to use properly.",
                "status": "1/7" if charged else "0/7",
                "equipped": True, "identified": True,
                "curse_known": True, "known_cursed": False,
                "actions": ["IMBUE", "ZAP"] if charged else ["IMBUE"],
            }],
            "map": {"width": 35, "height": 49, "cells": [
                {"cell": c, "terrain": t, "visible": True,
                 "observed": True, "effects": []}
                for c, t in ((1147, 6), (1182, 14), (1183, 14))]},
            "objects": [{"cell": 1147, "name": "great crab",
                         "status_icons": []}],
            "ui": {"texts": [], "buttons": []},
        }
        p = MagePolicy()
        p.update(s)
        return s, p, s["objects"][0]

    def test_shared_fallback_cannot_melee_awake_guarding_crab(self):
        s, p, crab = self.fixture()
        self.assertIsNone(p.best_attack(s, crab))

    def test_recharged_staff_is_not_a_direct_damage_solution(self):
        s, p, crab = self.fixture(charged=True)
        self.assertIsNone(p.best_attack(s, crab, allowed_kinds={"magic"}))

    def test_no_shared_attack_kind_or_nearby_foe_proves_surprise(self):
        s, p, crab = self.fixture()
        s["objects"].append({"cell": 1183, "name": "slime"})
        for kind in ("melee", "magic", "thrown"):
            self.assertFalse(p.attack_kind_allowed(s, crab, kind))

    def test_existing_public_surprise_exceptions_remain(self):
        for mode in ("sleeping", "invisible"):
            with self.subTest(mode=mode):
                s, p, crab = self.fixture(charged=True)
                if mode == "sleeping":
                    crab["sleeping"] = True
                else:
                    s["hero"]["buffs"] = [{"name": "invisibility"}]
                self.assertIsNotNone(p.best_attack(s, crab))

    def test_existing_doorway_workflow_remains_separate(self):
        s, p, crab = self.fixture()
        p.previous_position = 1147
        p.ambush_plan = {"kind": "great-crab", "door": 1147,
                         "hide": 1182, "last_enemy": 1113, "waits": 0}
        action = p.door_ambush(s, [crab], [crab], kind="great-crab")
        self.assertEqual({"type": "cell", "cell": 1147}, action.action)
        self.assertIn("doorway surprise", action.reason)

    def test_ordinary_foe_is_not_excluded(self):
        s, p, crab = self.fixture()
        crab["name"] = "slime"
        self.assertIsNotNone(p.best_attack(s, crab))


if __name__ == "__main__":
    unittest.main()
