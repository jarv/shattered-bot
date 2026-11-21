"""Reduced public decision-489 inputs: READ is listed but blindness forbids it.

These are isolated selector probes, not a reconstruction or gameplay replay.
"""
import copy
import unittest

from tools.consumable_tactics import (
    choose_consumable, identify_context, identify_retry_allowed,
)
from tools.policy_geometry import distance, neighbors
from tools.policy_nodes import preparation_and_recovery
from tools.policy_runtime import Context
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 3
    s["hero"].update(hp=30, max_hp=30, strength=11,
                     buffs=[{"name": name} for name in
                            ("hungry", "weakened", "blinded")])
    s["inventory"] += [
        {"id": "item-6", "name": "azure potion", "identified": False,
         "quantity": 1, "actions": ["DROP", "THROW", "DRINK"]},
        {"id": "item-7", "name": "bistre potion", "identified": False,
         "quantity": 1, "actions": ["DROP", "THROW", "DRINK"]},
        {"id": "item-8", "name": "scroll of identify", "identified": True,
         "quantity": 1, "actions": ["DROP", "THROW", "READ"]},
    ]
    p = verified()
    p.update(s)
    return s, p


class BlindIdentificationTests(unittest.TestCase):
    def test_both_recorded_selectors_defer_without_creating_menu_intent(self):
        for selector in (
            lambda p, s: preparation_and_recovery(Context(p, s)),
            lambda p, s: choose_consumable(p, s, [], distance, neighbors),
        ):
            with self.subTest(selector=selector):
                s, p = fixture()
                before = copy.deepcopy(s)
                menu = p.menu_plan
                failed = p.failed_identify_context
                self.assertIsNone(selector(p, s),
                                  "Blind identification must not issue a zero-turn READ")
                self.assertEqual(menu, p.menu_plan)
                self.assertEqual(failed, p.failed_identify_context)
                self.assertEqual(before, s)

    def test_fresh_sighted_input_still_admits_identification(self):
        for selector in (
            lambda p, s: preparation_and_recovery(Context(p, s)),
            lambda p, s: choose_consumable(p, s, [], distance, neighbors),
        ):
            s, p = fixture()
            s["hero"]["buffs"] = [{"name": "hungry"}, {"name": "weakened"}]
            p.update(s)
            d = selector(p, s)
            self.assertEqual({"type": "item", "id": "item-8", "action": "READ"},
                             d.action)
            self.assertEqual("discover-scroll", p.menu_plan)
            self.assertFalse(p.strength_identified)

    def test_temporary_blindness_does_not_erase_failed_inventory_context(self):
        s, p = fixture()
        p.failed_identify_context = identify_context(s)
        self.assertFalse(identify_retry_allowed(p, s))
        s["hero"]["buffs"] = []
        self.assertFalse(identify_retry_allowed(p, s))


if __name__ == "__main__":
    unittest.main()
