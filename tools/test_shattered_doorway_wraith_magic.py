"""Run 149 D1457: reduced public inputs, not recovered runtime memory.

The established hold is explicit fixture setup supported by the preceding
retreat/strike and the recorded hold report. No observations after a changed
decision are supplied, and no game input is dispatched.
"""
import copy
import unittest

from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=1267, hp=36, max_hp=40, strength=12)
    terrain = {1217: 4, 1218: 4, 1219: 2, 1266: 29, 1267: 29,
               1268: 6, 1269: 2, 1270: 2, 1317: 4, 1318: 4, 1319: 2}
    s["map"] = dict(width=50, height=43, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +2", status="4/6",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE", "ZAP"],
        description="This _tier-1_ melee weapon deals _3-10 damage_ and "
                    "requires _9 strength_ to use properly. Because of your "
                    "excess strength, you will deal _0-3 bonus damage_ with "
                    "this weapon. Each bolt from this wand deals _4-12 damage_.")]
    s["objects"] = [dict(name="wraith", cell=c) for c in (1268, 1270, 1319)]
    p = verified()
    p.update(s)
    p.previous_position = 1267
    p.doorway_hold = dict(depth=4, door=1268, hide=1267,
                          inputs=1, quiet=0, waits=0)
    return s, p


def choose(s, p):
    return hold_doorway(p, s, s["objects"], distance, neighbors, line_clear)


class DoorwayWraithMagicTests(unittest.TestCase):
    def test_stocked_established_hold_uses_magic_against_evasive_wraith(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        d = choose(s, p)
        self.assertEqual("ZAP", d.action.get("action"),
                         "An established hold must not bypass wraith magic priority")
        self.assertEqual(1268, p.target)
        self.assertEqual(original, s)
        self.assertFalse(p.cleared_floors)
        self.assertEqual(2, p.doorway_hold["inputs"])

    def test_tormented_spirit_shares_the_wraith_strategy(self):
        s, p = fixture()
        s["objects"][0]["name"] = "tormented spirit"
        self.assertEqual("ZAP", choose(s, p).action.get("action"))

    def test_empty_staff_does_not_invent_magic_or_new_movement(self):
        s, p = fixture()
        s["inventory"][0].update(status="0/6", actions=["THROW", "IMBUE"])
        self.assertEqual(dict(type="cell", cell=1268), choose(s, p).action)

    def test_flanked_hold_still_declines(self):
        s, p = fixture()
        s["objects"].append(dict(name="wraith", cell=1216))
        self.assertIsNone(choose(s, p))
        self.assertIsNone(p.doorway_hold)

    def test_initial_doorway_surprise_attempt_is_preserved(self):
        s, p = fixture()
        p.previous_position = 1268
        self.assertEqual(dict(type="cell", cell=1268), choose(s, p).action)

    def test_ordinary_enemy_keeps_existing_scoring(self):
        s, p = fixture()
        s["objects"] = [dict(name="gnoll scout", cell=1268)]
        expected = copy.deepcopy(p).best_attack(s, s["objects"][0])
        self.assertEqual(expected.action, choose(s, p).action)


if __name__ == "__main__":
    unittest.main()
