"""Reduced decision-846 public inputs, not a reconstruction or game replay."""
import copy
import unittest

from tools.policy_nodes import preparation_and_recovery
from tools.policy_runtime import Context
from tools.test_survival_bot import state
from tools.test_challenge_rules import verified


def fixture():
    s = state()
    s["depth"] = 3
    s["hero"].update(hp=34, max_hp=35, strength=11, level=4,
                     buffs=[{"name": "barrier"}, {"name": "Shuriken Cooldown"},
                            {"name": "blinded"}])
    s["inventory"][0].update(name="staff of magic missile +2",
                              identified=True, upgradable=True, status="1/6")
    s["inventory"].append(
        {"id": "item-11", "name": "scroll of upgrade", "identified": True,
         "quantity": 1, "actions": ["DROP", "THROW", "READ"]})
    p = verified()
    p.update(s)
    return s, p


class BlindUpgradeTests(unittest.TestCase):
    def test_blind_upgrade_declines_without_changing_intent_or_input(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        intent = (p.menu_plan, p.upgrade_target)
        self.assertIsNone(preparation_and_recovery(Context(p, s)),
                          "Blindness must defer the zero-turn upgrade READ")
        self.assertEqual(intent, (p.menu_plan, p.upgrade_target))
        self.assertEqual(before, s)

    def test_sighted_upgrade_still_uses_the_allocated_staff(self):
        s, p = fixture()
        s["hero"]["buffs"].pop()
        d = preparation_and_recovery(Context(p, s))
        self.assertEqual({"type": "item", "id": "item-11", "action": "READ"},
                         d.action)
        self.assertEqual("upgrade-select", p.menu_plan)
        self.assertEqual("staff of magic missile +2", p.upgrade_target)

    def test_blindness_does_not_prevent_known_strength_preparation(self):
        s, p = fixture()
        s["inventory"].append(
            {"id": "strength", "name": "potion of strength",
             "actions": ["DRINK"], "identified": True})
        d = preparation_and_recovery(Context(p, s))
        self.assertEqual({"type": "item", "id": "strength", "action": "DRINK"},
                         d.action)
        self.assertIsNone(p.menu_plan)

    def test_active_enemy_still_prevents_upgrade_preparation(self):
        s, p = fixture()
        s["hero"]["buffs"] = []
        self.assertIsNone(preparation_and_recovery(
            Context(p, s, active=[{"name": "marsupial rat", "cell": 25}])))
        self.assertIsNone(p.menu_plan)


if __name__ == "__main__":
    unittest.main()
