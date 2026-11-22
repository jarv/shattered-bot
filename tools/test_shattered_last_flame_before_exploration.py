"""Reduced public D138 geometry from recording 000135, not runtime memory.

The original isolated selector also selected THROW at shelf 409. Retain its
bounded fuel, throwing bank and observed route toward the unfinished frontier.
No changed decision is dispatched or followed by invented observations.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.test_survival_bot import state
from tools.test_wooden_barrier import wood_room
from tools.wooden_barrier import known_burn


def unfinished_library():
    s = state()
    s["hero"].update(cell=482, hp=20, max_hp=20, strength=10, buffs=[])
    cells = {373, 374, 375, 376, 377, 408, 409, 410, 411, 412,
             443, 444, 445, 446, 447, 448, 478, 479, 480, 481,
             482, 483, 516, 517, 518, 552, 588}
    s["map"] = dict(width=35, height=34, cells=[
        dict(cell=c, terrain=27 if c in {409, 410, 411, 444}
             else 11 if c == 482 else 14, observed=True,
             visible=c not in {373, 374, 375, 408})
        for c in sorted(cells)])
    s["objects"] = []
    s["inventory"].append(dict(potion("potion of liquid flame"), id="item-4"))
    p = verified()
    p.update(s)
    return s, p


class LastFlameBeforeExplorationTests(unittest.TestCase):
    def test_last_flame_survives_optional_shelves_before_unfinished_branch(self):
        s, p = unfinished_library()
        self.assertIn(588, p.exploration_report(s, p.paths(s))["unexplored_frontiers"])
        before = copy.deepcopy(s)
        self.assertIsNone(known_burn(p, s, []),
                          "Keep the last known flame for a possible real barricade")
        self.assertEqual(before, s)
        self.assertIsNone(p.wood_burn_plan)
        self.assertFalse(p.room_attempts)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.strength_identified)

    def test_surplus_flame_can_still_burn_admitted_shelves(self):
        s, p = unfinished_library()
        s["inventory"][-1]["quantity"] = 2
        action = known_burn(p, s, [])
        self.assertEqual("THROW", action.action["action"])
        self.assertEqual(409, p.target)

    def test_remote_known_barricade_also_reserves_last_dose(self):
        s, p = unfinished_library()
        # Negative safety variant: a remembered barricade is not permission
        # to spend its only dose on nearer optional shelves.
        p.tiles[1000] = dict(cell=1000, terrain=13, observed=True, visible=False)
        self.assertIsNone(known_burn(p, s, []))

    def test_real_barricade_still_gets_its_last_dose(self):
        s, p = wood_room()
        s["inventory"][-1] = potion("potion of liquid flame")
        s["hero"]["cell"] = 38
        action = known_burn(p, s, [])
        self.assertIsNotNone(action)
        self.assertEqual("THROW", action.action["action"])
        self.assertEqual(41, p.target)


if __name__ == "__main__":
    unittest.main()
