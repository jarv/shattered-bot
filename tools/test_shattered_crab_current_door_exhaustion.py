"""Reduced run 154 D1721 public geometry, not recorded runtime memory.

The exhaustion flag is reconstructed from accepted retreat bookkeeping. No
future crab entry, surprise, damage, or quest completion is asserted here.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.great_crab_tactics import choose, escape_route, guard_movement
from tools.policy_decision import TacticalBlocked


def fixture():
    terrain = {394: 1, 441: 1, 442: 4, 443: 4, 446: 4, 447: 4,
               448: 1, 484: 1, 485: 6, 486: 1, 487: 1, 488: 1,
               489: 1, 490: 5, 491: 1, 527: 4, 528: 4, 529: 4,
               532: 4, 533: 4, 534: 1}
    s = dict(scene="GameScene", status="ready", modal=False, depth=4,
             branch=0, danger_cells=[],
             hero=dict(cell=485, hp=45, max_hp=45, strength=12,
                       buffs=[dict(name="hungry")]),
             inventory=[], objects=[dict(name="great crab", cell=394)],
             ui=dict(texts=[], buttons=[]),
             map=dict(width=43, height=34, cells=[
                 dict(cell=c, terrain=t, observed=True,
                      visible=c not in {448, 491, 534}, effects=[])
                 for c, t in terrain.items()]))
    p = MagePolicy()
    p.update(s)
    p.pursuit_lure_exhausted = True
    return s, p


class CrabCurrentDoorExhaustionTests(unittest.TestCase):
    def test_current_verified_sight_break_is_not_new_lure_travel(self):
        s, p = fixture()
        self.assertEqual([486, 487, 488, 489, 490],
                         escape_route(p, s, 486, 485, {394}))
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=486), d.action)
        self.assertIsNotNone(p.great_crab_plan,
                             "Exhaustion must retain an immediate verified doorway sight break")
        self.assertEqual(485, p.great_crab_plan["door"])
        self.assertTrue(p.great_crab_plan["departing"])
        self.assertFalse(p.great_crab_plan["armed"])
        self.assertTrue(p.pursuit_lure_exhausted)
        guard_movement(p, s, d)
        self.assertNotIn(p.ghost_quest["stage"], {"reward", "done"})

    def test_exhaustion_still_forbids_travel_to_a_new_setup(self):
        s, p = fixture()
        s["hero"]["cell"] = 484
        p.update(s)
        try:
            choose(p, s, s["objects"])
        except TacticalBlocked:
            pass
        self.assertIsNone(p.great_crab_plan)

    def test_existing_admission_and_attempt_limits_remain(self):
        for mode in ("trap", "unknown", "danger", "attempts", "health", "other", "sight"):
            with self.subTest(mode=mode):
                s, p = fixture()
                if mode == "trap": p.tiles[486]["trap"] = "burning trap"
                elif mode == "unknown": p.tiles[490]["observed"] = False
                elif mode == "danger": s["danger_cells"] = [486]
                elif mode == "attempts": p.great_crab_attempts[485] = 3
                elif mode == "health": s["hero"]["hp"] = 20
                elif mode == "other": s["objects"].append(dict(name="slime", cell=484))
                else: s["objects"][0]["cell"] = 487
                try:
                    choose(p, s, s["objects"])
                except TacticalBlocked:
                    pass
                self.assertIsNone(p.great_crab_plan)


if __name__ == "__main__":
    unittest.main()
