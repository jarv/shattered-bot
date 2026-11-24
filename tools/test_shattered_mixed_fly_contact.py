"""Run 000233 D764 public reduction, not reconstructed runtime memory.

Only stationary selection is tested; omitted geometry is not an escape proof.
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
    s["hero"].update(cell=758, hp=15, max_hp=30, strength=11, buffs=[])
    terrain = {718: 29, 719: 4, 720: 12, 757: 1, 758: 6,
               759: 29, 796: 4, 797: 4, 798: 29, 799: 29}
    s["map"] = dict(width=39, height=37, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [dict(id="item-0", name="staff of magic missile +1",
        status="0/5", equipped=True, identified=True, curse_known=True,
        known_cursed=False, actions=["DROP", "THROW", "UNEQUIP", "IMBUE"],
        description="This _tier-1_ melee weapon deals _2-8 damage_ and "
                    "requires _9 strength_. Each bolt deals _3-10 damage_.")]
    s["objects"] = [
        dict(cell=718, name="gnoll scout", status_icons=[]),
        dict(cell=759, name="swarm of flies", health_bar=[8, 21],
             description="Every non-magical attack will split it into two "
                         "smaller but equally dangerous swarms.", status_icons=[]),
        dict(cell=759, name="Chest"),
        dict(cell=799, name="sewer crab", status_icons=[])]
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    return s, p


def enemies(s):
    return [o for o in s["objects"] if o["name"] != "Chest"]


class MixedFlyContactTests(unittest.TestCase):
    def test_empty_staff_attacks_admitted_contact_without_splitting_fly(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        d = choose(p, s, enemies(s))
        self.assertIsNotNone(d, "Do not hand mixed contact back to fly melee")
        self.assertEqual(dict(type="cell", cell=718), d.action)
        self.assertEqual(718, p.planner.report["unit_target"])
        self.assertEqual("gnoll scout",
                         p.planner.report["unit_strategy_selection"]["name"])
        self.assertEqual(before, s)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.cleared_floors)
        self.assertIsNone(p.fly_attack_override)

    def test_available_non_splitting_magic_keeps_fly_priority(self):
        s, p = fixture()
        s["inventory"][0].update(status="1/5", actions=["ZAP", "IMBUE"])
        d = choose(p, s, enemies(s))
        self.assertEqual("ZAP", d.action.get("action"))
        self.assertEqual(759, p.target)

    def test_no_promotion_of_sleeping_distant_or_protected_contact(self):
        for change in ("sleeping", "distant", "protected", "champion"):
            with self.subTest(change=change):
                s, p = fixture()
                contact = s["objects"][0]
                if change == "sleeping":
                    contact["sleeping"] = True
                elif change == "distant":
                    contact["cell"] = 716
                elif change == "protected":
                    contact["name"] = "skeleton"
                else:
                    contact["description"] = "_Blazing Champion_"
                choose(p, s, enemies(s))
                self.assertNotEqual(718, p.planner.report.get("unit_target"))

    def test_rejected_melee_does_not_become_direct_cell_attack(self):
        s, p = fixture()
        original = p.attack_kind_allowed
        p.attack_kind_allowed = lambda st, e, k: (
            False if e["cell"] == 718 else original(st, e, k))
        choose(p, s, enemies(s))
        self.assertNotEqual(718, p.planner.report.get("unit_target"))

    def test_existing_fly_escape_still_precedes_contact_attack(self):
        s, p = fixture()
        escape = p.cell(757, "isolated admitted escape")
        with patch("tools.unit_strategies.fly_escape", return_value=escape):
            self.assertIs(escape, choose(p, s, enemies(s)))

    def test_lone_fly_keeps_ordinary_fallback(self):
        s, p = fixture()
        s["objects"] = [s["objects"][1]]
        with patch("tools.unit_strategies.doorway_first", return_value=None):
            self.assertIsNone(choose(p, s, enemies(s)))
        self.assertEqual(759, p.planner.report["unit_target"])

    def test_existing_control_still_precedes_contact_attack(self):
        s, p = fixture()
        control = p.decision(dict(type="item", id="stone", action="THROW"),
                             "isolated admitted control")
        with patch("tools.unit_strategies.choose_runestone", return_value=control):
            self.assertIs(control, choose(p, s, enemies(s)))


if __name__ == "__main__":
    unittest.main()
