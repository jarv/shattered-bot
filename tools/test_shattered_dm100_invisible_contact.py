"""Reduced public contact geometry from recording 225, decision 3044.

This is a deterministic selector fixture, not reconstructed runtime memory or
a continuation of the recording. Only ordinary observed floor is retained.
"""
import unittest

from tools.policy_nodes import dm100_door_escape
from tools.policy_runtime import Context
from tools.policy_decision import Intent
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def contact():
    s = state()
    s.update(depth=8, branch=0)
    s["hero"].update(cell=552, hp=17, max_hp=60, strength=13,
                     buffs=[{"name": "starving"}, {"name": "invisible"}])
    s["map"] = dict(width=30, height=50, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
        for c in (400, 430, 460, 490, 520, 521, 522, 551, 552, 553,
                  580, 581, 582)])
    s["objects"] = [dict(name="DM-100", cell=581)]
    s["inventory"] = [dict(id="item-0", name="staff of magic missile +4",
                           status="2/8", equipped=True, identified=True,
                           known_cursed=False, actions=["ZAP", "UNEQUIP"])]
    p = verified()
    p.update(s)
    return p, s


class InvisibleDM100ContactTests(unittest.TestCase):
    def test_early_caster_leaf_yields_to_protected_withdrawal(self):
        for buff in ("invisible", "cloaked"):
            with self.subTest(buff=buff):
                p, s = contact()
                s["hero"]["buffs"][-1]["name"] = buff
                c = Context(p, s, enemies=s["objects"], active=s["objects"])
                self.assertIsNone(dm100_door_escape(c),
                                  "Caster contact must not bypass low-HP protection")
                self.assertIsNone(p.target)

    def test_full_selector_uses_existing_bounded_withdrawal(self):
        p, s = contact()
        d = p.choose(s)
        self.assertEqual("invisible-withdrawal", d.controller)
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual("cell", d.action["type"])
        self.assertNotEqual(581, d.action["cell"])
        self.assertIsNone(p.target)
        self.assertFalse(p.loot_collection_receipts)

    def test_unprotected_or_healthy_contact_keeps_existing_attack(self):
        for hp, buffs in ((17, []), (30, [{"name": "invisible"}])):
            with self.subTest(hp=hp, buffs=buffs):
                p, s = contact()
                s["hero"].update(hp=hp, buffs=buffs)
                c = Context(p, s, enemies=s["objects"], active=s["objects"])
                self.assertEqual("ZAP", dm100_door_escape(c).action["action"])


if __name__ == "__main__":
    unittest.main()
