"""Public-geometry reduction of recording 000250, decisions 1095–1099.

This is an isolated selector fixture, not reconstructed runtime memory.
No seed trigger, enemy movement, collection or successful descent is assumed.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.seed_strategies import choose
from tools.test_survival_bot import state


def approach():
    s = state()
    s["depth"] = 3
    s["hero"].update(cell=1099, hp=35, max_hp=35, level=4, buffs=[])
    s["evaluation_stats"] = {"elapsed_turns": 1069.25}
    # Recorded return path to the publicly mapped exit, plus the corridor's
    # parallel square 991. Only 1027 cuts that return; 991 has bypass 990.
    route = [1099, 1063, 1027, 990, 954, 919, 883, 847, 811, 776,
             741, 705, 670, 635, 636, 637, 602, 566, 531, 496, 461, 426]
    tiles = {c: dict(cell=c, terrain=14, visible=True, observed=True)
             for c in route + [991, 955]}
    for c in (956, 992, 1026, 1028, 1062, 1064):
        tiles[c] = dict(cell=c, terrain=0, visible=True, observed=True)
    tiles[1099]["terrain"] = 6
    tiles[426].update(terrain=8, visible=False, mapped=True)
    s["map"] = dict(width=36, height=40, cells=list(tiles.values()))
    s["objects"] = [dict(name="sewer crab", cell=919, health_bar=[8, 21],
                        status_icons=[])]
    s["inventory"] = [
        dict(id="staff", name="staff of magic missile +2", equipped=True,
             identified=True, curse_known=True, known_cursed=False,
             status="4/6", actions=["ZAP"]),
        dict(id="icecap", name="seed of icecap", quantity=1,
             actions=["THROW", "PLANT"])]
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    return s, p


class SeedExitCutTests(unittest.TestCase):
    def test_seed_uses_bypassable_approach_instead_of_sealing_exit(self):
        s, p = approach()
        before = copy.deepcopy(s)
        self.assertIn(426, p.paths(s))
        d = choose(p, s, s["objects"])
        self.assertIsNotNone(d)
        self.assertEqual("THROW", d.action["action"])
        self.assertEqual(991, p.target,
                         "Do not plant icecap on sole exit connector 1027")
        self.assertEqual(before, s)
        # A topology probe only: do not pretend the proposal was executed.
        p.blocked.add(p.target)
        self.assertIn(426, p.paths(s))
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.cleared_floors)

    def test_declines_when_every_plant_would_seal_known_exit(self):
        s, p = approach()
        p.tiles[990]["terrain"] = 0
        p.tiles[954]["terrain"] = 0
        self.assertIn(426, p.paths(s))
        self.assertIsNone(choose(p, s, s["objects"]))
        self.assertIsNone(p.seed_pending)
        self.assertFalse(p.seed_attempts)

    def test_existing_collateral_gate_still_excludes_alternate(self):
        s, p = approach()
        p.loot[955] = dict(name="jade potion", top_item=dict(name="jade potion"))
        self.assertIsNone(choose(p, s, s["objects"]))
        self.assertIsNone(p.seed_pending)


if __name__ == "__main__":
    unittest.main()
