"""Reduced public D2980 receipt: a second identical defeat line is appended.

This is a deterministic receipt fixture, not recovered policy memory.
"""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory


class RepeatedCasterDefeatTests(unittest.TestCase):
    def fixture(self):
        before, p = arena()
        before["hero"].update(cell=40, level=9)
        before["objects"] = [{"name": "DM-100", "cell": 31,
                              "health_bar": [10, 21]}]
        before["ui"]["texts"] = [
            "You defeated DM-100.", "You picked up: indigo potion.",
            "You feel uneasy.", "You are starving!"]
        before["evaluation_stats"] = dict(experience=48, experience_to_level=50,
                                           elapsed_turns=2904)
        p.update(before)
        after = copy.deepcopy(before)
        after["objects"] = []
        after["hero"]["level"] = 10
        after["evaluation_stats"] = dict(experience=4, experience_to_level=55,
                                          elapsed_turns=2905)
        after["ui"]["texts"] = [
            "You picked up: indigo potion.", "You feel uneasy.",
            "You are starving!", "Level up! +Accuracy, +Evasion, +5 HP!",
            "+1 Talent Point!", "You defeated DM-100."]
        return before, p, after

    def test_appended_duplicate_retires_only_matching_caster_memory(self):
        before, p, after = self.fixture()
        p.ranged_plan = {"name": "dm-100", "mode": "door-flight"}
        observe_accepted_attack(p, before, p.cell(31, "combat: melee"), after)
        self.assertIsNone(p.dm100_threat,
                          "An appended repeat kill must not trigger another door flight")
        self.assertIsNone(p.ranged_plan)
        self.assertFalse(exposed_memory(p, after))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_ambiguous_or_stale_duplicate_does_not_retire_memory(self):
        for mode in ("unchanged", "missing-anchor", "duplicate-anchor",
                     "survivor", "other-caster", "modal"):
            with self.subTest(mode=mode):
                before, p, after = self.fixture()
                if mode == "unchanged":
                    after["ui"]["texts"] = before["ui"]["texts"][:]
                elif mode == "missing-anchor":
                    after["ui"]["texts"] = ["You defeated DM-100."]
                elif mode == "duplicate-anchor":
                    before["ui"]["texts"].append("You picked up: indigo potion.")
                elif mode == "survivor":
                    after["objects"] = copy.deepcopy(before["objects"])
                elif mode == "other-caster":
                    p.dm100_threat = {"cell": 13, "age": 0}
                else:
                    after["modal"] = True
                observe_accepted_attack(p, before, p.cell(31, "combat: melee"), after)
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
