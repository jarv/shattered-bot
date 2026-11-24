"""Kill confirmation is independent of fire-confounded damage measurement."""
import copy
import unittest
from types import SimpleNamespace

from tools.mage_policy import MagePolicy
from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory
from tools.policy_nodes import dm100_door_escape


def receipt():
    # Reduced public decision 2841: burning open door 735, hero 774,
    # 8/21 health pixels, fresh defeat text after accepted melee.
    before = {
        "scene": "GameScene", "status": "ready", "modal": False,
        "depth": 7, "branch": 0, "danger_cells": [],
        "evaluation_stats": {"elapsed_turns": 2719, "experience": 35},
        "hero": {"cell": 774, "name": "mage", "hp": 52, "max_hp": 55,
                 "level": 8, "buffs": [{"name": "healing"}]},
        "inventory": [],
        "objects": [{"cell": 735, "name": "DM-100", "health_bar": [8, 21],
                     "status_icons": ["burning"]}],
        "ui": {"texts": ["Your wounds begin to close."], "buttons": []},
        "map": {"width": 40, "height": 40, "cells": [
            {"cell": c, "terrain": 6 if c == 735 else 1,
             "observed": True, "visible": True,
             "effects": ["A fire is raging here."] if c == 735 else []}
            for c in (735, 774, 814)]},
    }
    after = copy.deepcopy(before)
    after["objects"] = []
    after["hero"]["hp"] = 54
    after["evaluation_stats"].update(elapsed_turns=2720, experience=41)
    after["ui"]["texts"].append("You defeated DM-100.")
    p = MagePolicy()
    p.update(before)
    return before, p, after


class BurningDM100RetirementTests(unittest.TestCase):
    def accept(self, p, before, after):
        return observe_accepted_attack(p, before, p.cell(735, "combat: melee"), after)

    def test_fire_does_not_discard_confirmed_kill(self):
        before, p, after = receipt()
        self.accept(p, before, after)
        self.assertIsNone(p.dm100_threat,
                          "Fire must censor damage, not the fresh defeat receipt")
        self.assertFalse(p.damage_samples)
        self.assertTrue(next(t for t in after["map"]["cells"]
                             if t["cell"] == 735)["effects"])

    def test_retired_caster_cannot_block_later_lane_arbitration(self):
        before, p, after = receipt()
        self.accept(p, before, after)
        # Isolated geometry probe, not fabricated continuation of the recording.
        probe = copy.deepcopy(after)
        probe["hero"]["cell"] = 814
        self.assertFalse(exposed_memory(p, probe))
        context = SimpleNamespace(policy=p, state=probe, enemies=[], boss=False, hp=1)
        self.assertIsNone(dm100_door_escape(context))

    def test_uncertain_or_unrelated_receipts_keep_memory(self):
        for case in ("disappearance", "old-text", "other-kill", "other-cell",
                     "other-depth", "other-branch", "survivor"):
            with self.subTest(case=case):
                before, p, after = receipt()
                if case == "disappearance":
                    after["ui"]["texts"] = []
                elif case == "old-text":
                    before["ui"]["texts"].append("You defeated DM-100.")
                elif case == "other-kill":
                    after["ui"]["texts"] = ["You defeated prison guard."]
                elif case == "other-cell":
                    p.dm100_threat["cell"] = 697
                elif case == "other-depth":
                    after["depth"] = 8
                elif case == "other-branch":
                    after["branch"] = 1
                elif case == "survivor":
                    after["objects"] = copy.deepcopy(before["objects"])
                self.accept(p, before, after)
                self.assertIsNotNone(p.dm100_threat)
                self.assertFalse(p.damage_samples)


if __name__ == "__main__":
    unittest.main()
