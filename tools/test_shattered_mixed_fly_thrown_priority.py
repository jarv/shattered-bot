"""Run 253 D1120 public reduction; no original runtime memory or replay.

Stationary engagement selection only. Omitted terrain is not an escape proof.
"""
import copy
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.test_survival_bot import state
from tools.unit_strategies import choose


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=1173, hp=27, max_hp=35, strength=11)
    terrain = {
        1089:29, 1090:1, 1091:1, 1092:1, 1093:4,
        1130:29, 1131:1, 1132:8, 1133:1, 1134:4,
        1171:29, 1172:1, 1173:1, 1174:1, 1175:4,
        1212:29, 1213:29, 1214:1, 1215:1, 1216:4,
        1253:14, 1254:14, 1255:1, 1256:1, 1257:4}
    s["map"] = dict(width=41, height=38, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [
        dict(id="item-0", name="staff of magic missile +1", status="0/5",
             equipped=True, identified=True, curse_known=True, known_cursed=False,
             actions=["DROP", "THROW", "UNEQUIP", "IMBUE"],
             description="This _tier-1_ melee weapon deals _2-8 damage_ and "
                         "requires _9 strength_. Each bolt deals _3-10 damage_."),
        dict(id="item-6", name="throwing club x2", quantity=2, status="2",
             actions=["DROP", "THROW"], curse_known=True, known_cursed=False,
             description="Typically this set of _tier-2_ thrown weapons deals "
                         "_4-8 damage_ and requires _11 strength_ to use.")]
    s["objects"] = [
        dict(cell=1172, name="gnoll scout", status_icons=[], health_bar=[8, 16]),
        dict(cell=1213, name="swarm of flies", status_icons=[],
             description="Every non-magical attack will split it into two "
                         "smaller but equally dangerous swarms."),
        dict(cell=1295, name="sewer snake", status_icons=[])]
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    return s, p


class MixedFlyThrownPriorityTests(unittest.TestCase):
    def test_carried_club_does_not_preempt_admitted_non_splitting_contact(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertIsNotNone(p.best_attack(s, s["objects"][0], allowed_kinds={"melee"}))
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=1172), d.action,
                         "A carried club must not bypass ordinary-contact arbitration")
        self.assertEqual(1172, p.planner.report["unit_target"])
        self.assertEqual(before, s)
        self.assertIsNone(p.fly_fallback_pending)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.cleared_floors)

    def test_known_magic_still_precedes_contact(self):
        s, p = fixture()
        s["inventory"][0].update(status="1/5", actions=["ZAP", "IMBUE"])
        d = choose(p, s, s["objects"])
        self.assertEqual("ZAP", d.action.get("action"))
        self.assertEqual(1213, p.target)

    def test_no_admitted_ordinary_contact_preserves_existing_throw(self):
        for case in ("sleeping", "distant", "protected", "champion", "rejected"):
            with self.subTest(case=case):
                s, p = fixture()
                contact = s["objects"][0]
                if case == "sleeping":
                    contact["sleeping"] = True
                elif case == "distant":
                    contact["cell"] = 1255
                elif case == "protected":
                    contact["name"] = "skeleton"
                elif case == "champion":
                    contact["description"] = "_Blazing Champion_"
                else:
                    original = p.attack_kind_allowed
                    p.attack_kind_allowed = lambda st, e, k: (
                        False if e["cell"] == 1172 else original(st, e, k))
                d = choose(p, s, s["objects"])
                self.assertEqual("THROW", d.action.get("action"))
                self.assertEqual(1213, p.target)

    def test_existing_control_and_escape_still_precede_contact(self):
        for helper in ("fly_escape", "choose_runestone"):
            with self.subTest(helper=helper):
                s, p = fixture()
                admitted = p.cell(1131, "isolated admitted higher-priority action")
                with patch("tools.unit_strategies." + helper, return_value=admitted):
                    self.assertIs(admitted, choose(p, s, s["objects"]))


if __name__ == "__main__":
    unittest.main()
