"""Reduced public D4564 facts from 000216, not recorded policy memory.

No game replay or observation following a changed action is used.
"""
import copy
import unittest

from tools.boss_strategies import BossEscapeBlocked, TenguStrategy
from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.test_survival_bot import state


def encounter():
    s = state()
    s.update(depth=10, boss_health_text="68/200", danger_cells=[])
    s["hero"].update(cell=200, hp=75, max_hp=75, strength=14,
                     buffs=[dict(name="hungry"), dict(name="floor is locked")])
    s["inventory"] = []
    s["map"] = dict(width=32, height=32, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=(
            ["Electrical energy is building here, anything standing on this tile "
             "will be shocked next turn!"] if c in (199, 232) else []))
        for c in (167, 168, 169, 199, 200, 201, 231, 232, 233)])
    s["objects"] = [
        dict(cell=231, name="Shocker",
             description="Tengu has thrown a curious machine here, which seems "
                         "to be made of DM-100 parts."),
        dict(cell=389, name="Tengu")]
    p = MagePolicy()
    p.update(s)
    return s, p, TenguStrategy()


class TenguShockerEscapeTests(unittest.TestCase):
    def test_empty_current_effect_does_not_make_rotating_shocker_safe(self):
        s, p, boss = encounter()
        before = copy.deepcopy(s)
        d = boss.evade(p, s, [s["objects"][1]], distance, neighbors)
        self.assertIsNotNone(d)
        self.assertEqual("cell", d.action["type"])
        self.assertGreater(distance(d.action["cell"], 231, 32), 1)
        self.assertIn(d.action["cell"], (167, 168, 169, 201))
        self.assertTrue(p.walkable(d.action["cell"]))
        self.assertEqual(before, s)
        self.assertIn(200, boss.avoid_cells)
        self.assertIn(232, boss.avoid_cells)

    def test_no_observed_shocker_does_not_invent_a_hazard(self):
        s, p, boss = encounter()
        s["objects"] = s["objects"][1:]
        self.assertIsNone(boss.evade(p, s, s["objects"], distance, neighbors))

    def test_bomb_countdown_never_funds_transit_through_electricity(self):
        s, p, boss = encounter()
        # A conservative synthetic refusal case: every immediate exit is in
        # the shocker's footprint. A smoke-bomb timer is not an electric timer.
        s["objects"][0]["cell"] = 200
        s["objects"].append(dict(cell=200, name="Smoke Bomb",
                                  description="Tengu has thrown a smoke bomb here."))
        s["ui"]["texts"] = ["3..."]
        s["map"]["cells"] = [
            dict(cell=y*32+x, terrain=1, visible=True, observed=True, effects=[])
            for y in range(2, 11) for x in range(4, 13)]
        p = MagePolicy()
        p.update(s)
        with self.assertRaises(BossEscapeBlocked):
            boss.evade(p, s, [s["objects"][1]], distance, neighbors)

    def test_existing_warning_and_tile_effect_checks_still_apply(self):
        s, p, boss = encounter()
        s["danger_cells"] = [167, 168]
        d = boss.evade(p, s, [s["objects"][1]], distance, neighbors)
        self.assertIsNotNone(d)
        self.assertNotIn(d.action["cell"], s["danger_cells"])
        self.assertGreater(distance(d.action["cell"], 231, 32), 1)


if __name__ == "__main__":
    unittest.main()
