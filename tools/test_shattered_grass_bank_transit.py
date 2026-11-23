"""Run 162: reduced public D814 return corridor, not a gameplay replay.

The receipt is reconstructed from validated accepted inputs, not logged memory.
Only transit is tested: unseen bank surroundings cannot authorize a drink.
"""
import copy
import unittest

from tools.descent_potions import begin, potion_inventory
from tools.policy_decision import Intent, PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 2
    s["hero"].update(cell=365, hp=30, max_hp=30, buffs=[])
    s["inventory"] = [
        dict(id=str(n), name=name + " potion", quantity=1, identified=False,
             actions=["DROP", "THROW", "DRINK"])
        for n, name in enumerate(("ivory", "crimson", "charcoal"))]
    s["map"] = dict(width=34, height=49, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c != 362)
        for c, t in ((365, 1), (364, 2), (329, 29), (362, 29))])
    p = verified()
    p.update(s)
    receipt = (2, 0, 362, potion_inventory(s))
    p.descent_potion_bank_receipt = receipt
    p.descent_potion_bank_history = [receipt]
    return s, p


class GrassBankTransitTests(unittest.TestCase):
    def test_plain_grass_is_transit_not_a_drink_bank(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        try:
            d = begin(p, s)
        except PlannerStuck:
            d = None
        self.assertIsNotNone(d, "Plain observed grass must not disconnect the witnessed bank")
        self.assertEqual(dict(type="cell", cell=364), d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertTrue(d.descent_bank_return)
        self.assertEqual(original, s)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)

    def test_grass_does_not_bypass_hazard_visibility_or_return_budget(self):
        for kind in ("effect", "plant", "trap", "unobserved", "invisible", "budget"):
            s, p = fixture()
            if kind in ("effect", "plant", "trap"):
                p.tiles[364][{"effect": "effects"}.get(kind, kind)] = (
                    ["fire"] if kind == "effect" else "poison")
            elif kind == "unobserved":
                p.tiles[364]["observed"] = False
            elif kind == "invisible":
                p.tiles[364]["visible"] = False
            else:
                p.descent_potion_plan = dict(depth=2, steps=0, waits=0,
                    candidate=None, bank=None, pending=False, return_steps=64)
            with self.assertRaises(PlannerStuck, msg=kind):
                begin(p, s)
            self.assertIsNone(p.puzzle_probe)
            self.assertIsNone(p.potion_stash)


if __name__ == "__main__":
    unittest.main()
