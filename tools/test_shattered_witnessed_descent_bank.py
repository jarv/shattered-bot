"""Run 111 D264: a visible, feasible bank need not be under the hero.

Reduced public terrain/actions, with fresh terminal transit geometry. This
tests preparation selection, not a drink, stash receipt or puzzle success.
"""
import copy
import unittest

from tools.descent_potions import remember_bank, begin
from tools.policy_decision import Intent, PlannerStuck
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import safe_test_bank
from tools.potion_stash import can_protect_potions
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    groups = {
        4: [418,419,420,421,423,424,425,426,451,458,483,490,515,522,
            547,554,555,556,579,588,611,618,620,643,644,645,646,647,
            649,650,652,682,684,714,741,742,743,745,746,747,748],
        5: [422,586],
        1: [452,453,454,455,456,580,581,582,583,584,585,587,612,613,
            614,615,616,678,680,709,710,711,712,713,715,716],
        20: [457,679],
        29: [484,485,486,487,489,516,517,518,519,521,548,549,550,551,553],
        14: [488,520,552], 2: [617,619,651,683], 6: [648], 15: [681],
        31: [744],
    }
    s = state()
    s["hero"].update(cell=648, hp=25, max_hp=25, strength=10, buffs=[])
    s["objects"] = []
    s["inventory"] = [
        dict(id=str(n), name=color+" potion", quantity=1, identified=False,
             actions=["DROP","THROW","DRINK"])
        for n,color in enumerate(("crimson","jade"))]
    visible = {c for c in sum(list(groups.values()), [])
               if c not in {418,547,555,556,579,580,587,588,611,612,613,
                            619,620,643,644,645,646,650,651,652,682,683,
                            684,714,715,716,741,746,747,748}}
    s["map"] = dict(width=32, height=37, cells=[
        dict(cell=c,terrain=t,observed=True,visible=c in visible)
        for t,cells in groups.items() for c in cells])
    p = verified()
    p.update(s)
    return s,p


class WitnessedDescentBankTests(unittest.TestCase):
    def test_nearby_witness_survives_departure_and_selects_only_reobservation(self):
        s,p = fixture()
        staged = dict(s,hero=dict(s["hero"],cell=583))
        self.assertTrue(safe_test_bank(p,s,583,distance,neighbors,allow_dry=True))
        self.assertTrue(can_protect_potions(p,staged,s["inventory"][0],
                                          distance,neighbors,safe_test_bank,isolated_stack=True))
        before = copy.deepcopy(s)
        remember_bank(p,s)
        self.assertEqual(before,s)
        self.assertIn(583,[r[2] for r in getattr(p,"descent_potion_bank_history",())])
        # D270 collection really opened the crystal door and reached 808.
        # No future state is dispatched; this is an isolated transit probe.
        later = copy.deepcopy(s)
        later["hero"]["cell"] = 808
        for t in later["map"]["cells"]:
            t["visible"] = t["cell"] in {679,680,711,712,713,742,743,744,745}
            if t["cell"] == 648: t["terrain"] = 5
            if t["cell"] == 744: t["terrain"] = 1
        later["map"]["cells"].extend([
            dict(cell=c,terrain=t,observed=True,visible=True)
            for t,cells in {4:[774,778,806,810,838,842,870,871,872],
                            14:[775,776,777,807,808,809,839,840,841]}.items()
            for c in cells])
        p.update(later)
        d = begin(p,later)
        self.assertEqual({"type":"cell","cell":775},d.action)
        self.assertEqual(Intent.REPOSITION,d.intent)
        self.assertIn(d.navigation_route[-1],[r[2] for r in p.descent_potion_bank_history])
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)

    def test_unseen_or_unsafe_surroundings_do_not_create_a_bank_receipt(self):
        for hazard in ("visible","effects","plant"):
            s,p = fixture()
            for t in p.tiles.values():
                if hazard == "visible": t["visible"] = False
                else: t[hazard] = ["fire"] if hazard == "effects" else "firebloom"
            remember_bank(p,s)
            self.assertFalse(getattr(p,"descent_potion_bank_history",()))


if __name__ == "__main__":
    unittest.main()
