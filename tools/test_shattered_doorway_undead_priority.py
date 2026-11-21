"""Run 82 D2266: condensed public inputs and an explicit established hold.

The hold is fixture setup, not originally recorded memory. No game is run and
no observations after a changed selection are supplied.
"""
import copy
import unittest

from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=6, branch=0)
    s["hero"].update(cell=1955, hp=43, max_hp=50, strength=12)
    s["map"] = dict(width=38, height=64, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in ((1955, 1), (1956, 6), (1957, 1))])
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +2", status="6/6",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["ZAP", "THROW", "UNEQUIP", "IMBUE"],
        description="This _tier-1_ melee weapon deals _3-10 damage_ and "
                    "requires _9 strength_ to use properly. Because of your "
                    "excess strength, you will deal _0-3 bonus damage_ with "
                    "this weapon. Each bolt from this wand deals _4-12 damage_.")]
    s["objects"] = [
        dict(name="skeleton", cell=1956, health_bar=[13, 16]),
        dict(name="skeleton", cell=1957)]
    p = verified()
    p.update(s)
    p.previous_position = 1955
    p.doorway_hold = dict(depth=6, door=1956, hide=1955,
                          inputs=1, quiet=0, waits=0)
    return s, p


def choose(s, p):
    return hold_doorway(p, s, s["objects"], distance, neighbors, line_clear)


class DoorwayUndeadPriorityTests(unittest.TestCase):
    def test_established_hold_retains_admitted_undead_ranged_priority(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        d = choose(s, p)
        self.assertEqual("ZAP", d.action.get("action"),
                         "An established hold must not bypass undead ranged priority")
        self.assertEqual(1956, p.target)
        self.assertEqual(original, s)
        self.assertFalse(p.cleared_floors)

    def test_no_new_wait_or_movement_when_no_ranged_attack_is_available(self):
        s, p = fixture()
        s["inventory"][0].update(status="0/6", actions=["THROW", "IMBUE"])
        d = choose(s, p)
        self.assertEqual({"type": "cell", "cell": 1956}, d.action)

    def test_flanked_hold_still_declines(self):
        s, p = fixture()
        s["objects"].append(dict(name="skeleton", cell=1917))
        self.assertIsNone(choose(s, p))
        self.assertIsNone(p.doorway_hold)

    def test_ordinary_enemy_retains_existing_attack_scoring(self):
        s, p = fixture()
        s["objects"] = [dict(name="gnoll scout", cell=1956)]
        expected = copy.deepcopy(p).best_attack(s, s["objects"][0])
        self.assertEqual(expected.action, choose(s, p).action)


if __name__ == "__main__":
    unittest.main()
