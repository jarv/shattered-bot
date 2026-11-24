"""Run 256 D366: opening the door must not reverse an admitted bank return.

Reduced public terrain and inventory; plan fields are reconstruction, not
recorded runtime memory. Independent input fixtures never dispatch movement.
"""
import copy
import unittest

from tools.descent_potions import advance, revisit_receipt, potion_inventory
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    groups = {
        (4, True): [169,170,171,172,173,174,175,176,179,211,221,253,260,267,
                    295,305,306,307,308,309,337,346,347,379],
        (1, True): [212,213,214,219,254,255,256,257,258,259,261,262,263,264,
                    265,296,297,298,299,300,301,338,340,341,342,380,381,382,383],
        (29, True): [216,217],
        (33, True): [215],
        (6, True): [218],
        (20, True): [266],
        (0, True): [177,178,220,303,304],
        (1, False): [105,106,107,146,147,148,149,150,188,189,190,191,192,
                     224,225,226,227,229,234,271,313,318],
        (33, False): [103,145,187,274,276,316],
        (20, False): [104,108],
        (5, False): [228],
        (29, False): [230,231,232,233,272,273,275,314,315,317],
    }
    # Observed walls enclose the eastern remembered bank.
    groups[(4, False)] = [
        60,61,62,63,64,65,66,67,102,109,134,144,151,181,182,183,184,185,
        186,193,222,223,235,268,269,270,277,278,279,280,302,312,322,323,
        324,344,345,354,361,362,366,386,396,397,398,399,400,401,402,403,
        404,405,406,408,409,410,411]
    s["map"] = dict(width=42, height=33, cells=[
        dict(cell=c, terrain=t, visible=v, observed=True)
        for (t,v), cells in groups.items() for c in cells])
    s["hero"].update(cell=218, hp=25, max_hp=25, strength=10, level=2,
                     buffs=[dict(name="hungry")])
    s["inventory"] = [
        dict(id="food", name="ration of food", quantity=2, identified=True,
             actions=["EAT","DROP","THROW"]),
        dict(id="potion", name="crimson potion", quantity=1, identified=False,
             actions=["DRINK","DROP","THROW"])]
    p = verified()
    p.update(s)
    p.descent_potion_plan = dict(depth=1, steps=9, waits=0, candidate=None,
                                 bank=None, pending=False, return_steps=9)
    receipt = (1, 0, 272, potion_inventory(s))
    p.descent_potion_bank_receipt = receipt
    p.descent_potion_bank_history = [receipt]
    # D365's accepted return targeted 272. This proposal establishes only
    # the same transit commitment, not fresh arrival or a consumption receipt.
    d = revisit_receipt(p, s, p.paths(s), receipt)
    assert d is not None and d.action == dict(type="cell", cell=219)
    return s, p


class DiscoveryReturnCommitmentTests(unittest.TestCase):
    def test_continue_admitted_return_instead_of_reversing_to_water(self):
        s,p = fixture()
        original = copy.deepcopy(s)
        d = advance(p,s)
        self.assertEqual(dict(type="cell",cell=219), d.action)
        self.assertTrue(d.descent_bank_return)
        self.assertEqual(272, d.objective_receipt["target"])
        self.assertEqual(original,s)
        self.assertEqual(9,p.descent_potion_plan["return_steps"])
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)

    def test_new_hazard_cannot_be_overridden_by_commitment(self):
        s,p = fixture()
        p.tiles[219]["trap"] = "burning trap"
        d = advance(p,s)
        self.assertFalse(d and d.action == dict(type="cell",cell=219))
        self.assertIsNone(p.puzzle_probe)

    def test_unobserved_arrival_does_not_authorize_drinking(self):
        s,p = fixture()
        s["hero"]["cell"] = 272
        p.update(s)
        d = advance(p,s)
        self.assertFalse(d and d.action.get("action") == "DRINK")
        self.assertIsNone(p.puzzle_probe)


if __name__ == "__main__":
    unittest.main()
