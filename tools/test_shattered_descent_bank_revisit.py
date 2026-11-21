"""Run 64 decisions 247-249: a closed door hides a previously admitted bank.

Reduced public map and potion actions; no gameplay replay or inferred effects.
The alternative is evaluated only at the terminal input, never dispatched.
"""
import copy
import unittest

from tools.descent_potions import begin, observe
from tools.policy_decision import Decision, Intent, PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    groups = {
        (4, True): [895,999,1000,1030,1034,1064,1066,1068,1102,1134,1136,
                    1168,1202,1203,1204,1309,1310],
        (1, True): [896,930,964,998,1033,1067,1101,1135,1169],
        (1, False): [897,903,931,937,965,966,967,968,970],
        (4, False): [898,902,904,929,932,933,934,935,936,938,963,972,996,
                     1001,1002,1003,1004,1005,1006,1037,1038,1039,1073,
                     1098,1107,1132,1133,1141,1175,1209,1243,1277,1311],
        (20, False): [969,971], (12, False): [997],
        (29, True): [1031,1032,1065,1099,1100],
        (0, False): [1070,1071,1072,1103,1106,1137,1140,1174,1208,1242],
        (14, False): [1104,1105,1138,1139,1172,1173,1207],
        (6, True): [1170], (14, True): [1171,1206,1240,1241],
        (0, True): [1205,1239,1274,1275,1276],
    }
    s["map"] = dict(width=34, height=40, cells=[
        dict(cell=c, terrain=t, visible=v, observed=True)
        for (t,v), cells in groups.items() for c in cells])
    s["hero"].update(cell=1135, hp=20, max_hp=20, strength=10, buffs=[])
    s["objects"] = []
    s["inventory"] = [
        dict(id=str(n), name=name+" potion", quantity=1, identified=False,
             actions=["DROP","THROW","DRINK"])
        for n,name in enumerate(("amber","azure","turquoise"))]
    p = verified()
    p.update(s)
    d = Decision(dict(type="cell", cell=1170), "explore: frontier", Intent.EXPLORE)
    after = copy.deepcopy(s)
    after["hero"]["cell"] = 1170
    observe(p, s, d, after)  # Accepted input, not a bank arrival/collection claim.
    terminal = copy.deepcopy(s)
    terminal["hero"]["cell"] = 1171
    visible = {1034,1037,1038,1039,1068,1073,1102,1107,1136,1141,1175,
               1204,1209,1243,1277,1309,1310,1311,1070,1071,1072,1103,
               1106,1137,1140,1174,1205,1208,1239,1242,1274,1275,1276,
               1104,1105,1138,1139,1171,1172,1173,1206,1207,1240,1241,1170}
    for t in terminal["map"]["cells"]:
        t["visible"] = t["cell"] in visible
        if t["cell"] == 1170: t["terrain"] = 5
    p.update(terminal)
    return terminal, p


class DescentBankRevisitTests(unittest.TestCase):
    def test_closed_door_admits_reobservation_not_a_blind_drink(self):
        s,p = fixture()
        before = copy.deepcopy(s)
        try:
            d = begin(p,s)
        except PlannerStuck as error:
            self.fail("Previously verified bank must admit bounded reobservation: "+error.blocker)
        self.assertEqual(dict(type="cell",cell=1170), d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.descent_potion_tests)
        self.assertFalse(p.strength_identified)
        self.assertEqual(before,s)

    def test_no_receipt_or_new_route_hazard_still_blocks(self):
        for kind in ("no-receipt","trap","effect","plant","room","blocked",
                     "threat","danger","wounded","no-drop","budget","floor"):
            s,p = fixture()
            if kind == "no-receipt": p.descent_potion_bank_receipt = None
            elif kind in {"trap","effect","plant"}:
                p.tiles[1170][{"effect":"effects"}.get(kind,kind)] = (
                    ["fire"] if kind=="effect" else "poison")
            elif kind=="room": p.room_blocked.add(1170)
            elif kind=="blocked": p.blocked.add(1170)
            elif kind=="threat": p.recent_threats[1170] = dict(cell=1170,name="rat")
            elif kind=="danger": s["danger_cells"] = [1170]
            elif kind=="wounded": s["hero"]["hp"] = 10
            elif kind=="no-drop":
                for item in s["inventory"]: item["actions"].remove("DROP")
            elif kind=="budget":
                p.descent_potion_plan = dict(depth=1,steps=0,waits=0,candidate=None,
                                             bank=None,pending=False,return_steps=64)
            elif kind=="floor": s["depth"] = 2
            with self.assertRaises(PlannerStuck,msg=kind):
                begin(p,s)

    def test_proposal_does_not_spend_return_budget(self):
        s,p = fixture()
        try: d = begin(p,s)
        except PlannerStuck as error: self.fail(error.blocker)
        self.assertEqual(0,p.descent_potion_plan.get("return_steps",0))
        observe(p,s,d,copy.deepcopy(s))  # Opening a door may leave the hero in place.
        self.assertEqual(1,p.descent_potion_plan["return_steps"])

    def test_arrival_still_requires_fresh_drink_and_stash_admission(self):
        s,p = fixture()
        # Isolated adverse arrival fixture, not an observation after dispatch.
        s["hero"]["cell"] = 1135
        p.update(s)
        with self.assertRaises(PlannerStuck):
            begin(p,s)  # Memory never substitutes for current visible surroundings.
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)


if __name__ == "__main__":
    unittest.main()
