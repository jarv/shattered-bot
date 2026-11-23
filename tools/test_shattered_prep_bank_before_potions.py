"""Run 161: remember witnessed preparation ground before the first potion.

Reduced D223 visible terrain and D358 ordinary return corridor. This is an
offline selection fixture, not a replay or evidence of arrival/drinking.
"""
import copy
import unittest

from tools.descent_potions import begin, remember_bank
from tools.policy_decision import Intent, PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture(witness_visible=True):
    groups = {
        4: [44,45,46,47,83,89,122,128,161,167,200,206,239,245,
            278,317,319,320,321],
        1: [84,85,86,88,123,279],
        2: [124,125,127,165,166,281],
        8: [126],
        29: [162,163,201,202,204,205,240,241,243,244],
        15: [164,282], 14: [203,242], 20: [280], 5: [318],
    }
    s = state()
    s["hero"].update(cell=279, hp=20, max_hp=20, buffs=[])
    s["inventory"] = []
    s["objects"] = []
    s["map"] = dict(width=39, height=33, cells=[
        dict(cell=c, terrain=t, observed=True, visible=witness_visible)
        for t, cells in groups.items() for c in cells])
    p = verified()
    p.update(s)
    remember_bank(p, s)
    later = copy.deepcopy(s)
    later["hero"].update(cell=670, hp=25, max_hp=25)
    later["inventory"] = [
        dict(id="haste", name="potion of haste", identified=True, quantity=1,
             actions=["DROP", "THROW", "DRINK"]),
        dict(id="magenta", name="magenta potion", identified=False, quantity=1,
             actions=["DROP", "THROW", "DRINK"])]
    for t in later["map"]["cells"]:
        t["visible"] = False
        if t["cell"] == 318:
            t["terrain"] = 5  # Recorded high grass was trampled earlier.
    later["map"]["cells"].extend(
        dict(cell=c, terrain=t, observed=True, visible=c in {670,630,590})
        for c,t in [(357,1),(395,1),(434,1),(473,5),(511,1),
                    (551,20),(590,1),(630,1),(670,14)])
    p.update(later)
    return later, p


class PreparationBeforePotionsTests(unittest.TestCase):
    def test_empty_inventory_does_not_authorize_unseen_bank_witnesses(self):
        _,p = fixture(witness_visible=False)
        self.assertFalse(getattr(p, "descent_potion_bank_history", []))

    def test_empty_inventory_preserves_witness_for_protected_reobservation(self):
        s,p = fixture()
        self.assertIn(240, [r[2] for r in getattr(p, "descent_potion_bank_history", [])])
        before = copy.deepcopy(s)
        d = begin(p,s)
        self.assertEqual({"type":"cell", "cell":630}, d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertEqual(before,s)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)

    def test_new_inventory_and_transit_still_need_admission(self):
        for condition in ("drop", "trap", "budget", "stale-arrival"):
            s,p = fixture()
            if condition == "drop":
                for i in s["inventory"]:
                    i["actions"].remove("DROP")
            elif condition == "trap":
                p.tiles[630]["trap"] = "poison"
            elif condition == "budget":
                p.descent_potion_plan = dict(depth=1, steps=0, waits=0,
                    candidate=None, bank=None, pending=False, return_steps=64)
            else:
                s["hero"]["cell"] = 240
                p.update(s)
            with self.assertRaises(PlannerStuck, msg=condition):
                begin(p,s)
            self.assertIsNone(p.potion_stash)
            self.assertIsNone(p.puzzle_probe)


if __name__ == "__main__":
    unittest.main()
