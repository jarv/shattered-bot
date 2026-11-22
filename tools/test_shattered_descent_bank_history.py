"""Run 84 D242/D289/D331: retain an earlier admitted preparation area.

Reduced public geometry and potion actions, not a gameplay replay. The southern
bank's only retained route crosses grass; the older bank has admitted transit.
Returning for fresh observation is not permission to drink or a success receipt.
"""
import copy
import unittest

from tools.descent_potions import begin, remember_bank, potion_inventory
from tools.policy_decision import Intent, PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    groups = {
        4: [444,477,478,481,482,483,561,600,990,991,994,1029,1030,1033,
            1068,1069,1072,1107,1111,1150],
        12: [479,480,1108], 15: [516,556,598],
        29: [517,518,519,557,558,596,597,1109,1110,1146,1147,1148,1149],
        1: [520,521,559,560,562,599,601,640,680,685,720,721,722,723,725,
            766,767,807,847,887,911,912,913,914,915,952,953,954,992,993,
            1031,1032,1070,1071,967,1005],
        5: [522,756,765,871,927], 2: [555,755,793], 20: [831], 14: [1004],
    }
    s = state()
    s["hero"].update(cell=1004, hp=25, max_hp=25, strength=10,
                     buffs=[{"name": "hungry"}])
    s["objects"] = []
    s["inventory"] = [dict(id=str(n), name=name+" potion", quantity=1,
                            identified=False, actions=["DROP","THROW","DRINK"])
                       for n,name in enumerate(("indigo","crimson"))]
    s["map"] = dict(width=39, height=33, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c in {1004,1005,967})
        for t,cells in groups.items() for c in cells])
    p = verified()
    # Only these local surroundings were visible at the earlier public inputs.
    for bank,visible in [
        (520, {477,478,479,480,481,482,483,516,517,518,519,520,521,522,
               555,556,557,558,559,560,561,596,597,598,599,600}),
        (1070, {913,914,915,952,953,954,991,992,993,994,1030,1031,1032,
                1033,1069,1070,1071,1072,1108,1109,1110,1111,1147,
                1148,1149,1150}),
    ]:
        earlier = copy.deepcopy(s)
        earlier["hero"].update(cell=bank, buffs=[])
        for t in earlier["map"]["cells"]:
            t["visible"] = t["cell"] in visible
        p.update(earlier)
        remember_bank(p, earlier)
        assert p.descent_potion_bank_receipt == (1,0,bank,potion_inventory(s))
    p.update(s)
    return s,p


class DescentBankHistoryTests(unittest.TestCase):
    def test_inaccessible_new_bank_does_not_erase_admitted_older_bank(self):
        s,p = fixture()
        before = copy.deepcopy(s)
        try:
            d = begin(p,s)
        except PlannerStuck as error:
            self.fail("Retain earlier verified bank when latest transit is excluded: "+error.blocker)
        self.assertEqual({"type":"cell", "cell":1005}, d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertEqual(520, d.navigation_route[-1])
        self.assertNotIn(755, d.navigation_route)
        self.assertNotIn(793, d.navigation_route)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)
        self.assertEqual(0,p.descent_potion_plan.get("return_steps",0))
        self.assertEqual(before,s)

    def test_history_never_bypasses_transit_inventory_or_survival_gates(self):
        for kind in ("trap","plant","effects","blocked","room","inventory",
                     "depth","branch","budget","threat","wounded"):
            s,p = fixture()
            if kind in {"trap","plant","effects"}:
                p.tiles[1005][kind] = ["fire"] if kind == "effects" else "poison"
            elif kind == "blocked": p.blocked.add(1005)
            elif kind == "room": p.room_blocked.add(1005)
            elif kind == "inventory":
                # Changed quantities may now be replanned; unsupported storage
                # still cannot borrow the old inventory's admission.
                for item in s["inventory"]:
                    item["actions"].remove("DROP")
            elif kind == "depth": s["depth"] = 2
            elif kind == "branch": s["branch"] = 1
            elif kind == "budget":
                p.descent_potion_plan = dict(depth=1,steps=0,waits=0,candidate=None,
                                            bank=None,pending=False,return_steps=64)
            elif kind == "threat": p.recent_threats[1005] = dict(cell=1005,name="rat")
            elif kind == "wounded": s["hero"]["hp"] = 10
            with self.assertRaises(PlannerStuck,msg=kind): begin(p,s)

    def test_retained_bank_still_needs_fresh_visible_drink_admission(self):
        s,p = fixture()
        s["hero"]["cell"] = 520
        p.update(s)
        with self.assertRaises(PlannerStuck): begin(p,s)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)


if __name__ == "__main__":
    unittest.main()
