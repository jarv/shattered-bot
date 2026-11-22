"""Run 150 D3368: reduced public geometry, not recovered runtime memory.

The minion at 2492 visibly has adrenaline before retreat to 2439.
These are isolated risk probes, not a changed-policy replay.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.challenge_combat import exposure
from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, line_clear
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=8, branch=0)
    s["hero"].update(cell=2438, hp=4, max_hp=65)
    terrain = {
        2385: 4, 2386: 5, 2387: 4,
        2435: 4, 2436: 1, 2437: 1, 2438: 1, 2439: 1,
        2440: 29, 2441: 29, 2442: 4,
        2490: 4, 2491: 1, 2492: 1, 2493: 1, 2494: 29,
        2495: 29, 2496: 29, 2497: 4,
        2545: 4, 2546: 1, 2547: 1, 2548: 1, 2549: 29,
        2550: 29, 2551: 29, 2552: 4,
    }
    s["map"] = dict(width=55, height=60, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [
        dict(name="skeleton", cell=2437, health_bar=[6, 16], status_icons=[]),
        dict(name="necromancer's skeleton", cell=2492,
             status_icons=["adrenaline"]),
    ]
    p = MagePolicy()
    p.update(s)
    return p, s


class AdrenalineRetreatPressureTests(unittest.TestCase):
    def test_recorded_next_step_is_not_free_of_minion_pursuit(self):
        p, s = fixture()
        minion = s["objects"][1]
        self.assertEqual(2, distance(2439, minion["cell"], 55))
        risk = exposure(p, s, [minion], 2439, distance, line_clear)
        self.assertEqual(0, risk["melee"])  # Not a current adjacent attack.
        self.assertEqual(1, risk["fast_pursuit"])
        self.assertEqual(1, risk["exposure"])

    def test_recorded_farther_endpoint_includes_two_step_approach(self):
        p, s = fixture()
        self.assertEqual(3, distance(2440, 2492, 55))
        self.assertEqual(1, multi.approach_pressure(p, s, s["objects"], 2440))
        self.assertFalse(multi.can_attack(p, s, s["objects"][1], 2440))

    def test_no_speed_is_inferred_without_public_adrenaline(self):
        p, s = fixture()
        minion = s["objects"][1]
        minion["status_icons"] = []
        self.assertEqual(0, exposure(p, s, [minion], 2439, distance, line_clear)["exposure"])
        self.assertEqual(0, multi.approach_pressure(p, s, [minion], 2440))
        minion.pop("status_icons")
        self.assertEqual(0, multi.approach_pressure(p, s, [minion], 2440))

    def test_sleeping_buffed_minion_adds_no_pressure(self):
        p, s = fixture()
        minion = s["objects"][1]
        minion["sleeping"] = True
        self.assertEqual(0, exposure(p, s, [minion], 2439, distance, line_clear)["exposure"])
        self.assertEqual(0, multi.approach_pressure(p, s, [minion], 2440))

    def test_existing_description_speed_evidence_is_preserved(self):
        p, s = fixture()
        minion = s["objects"][1]
        minion["status_icons"] = []
        minion["description"] = "Moving at double speed."
        self.assertEqual(1, exposure(p, s, [minion], 2439, distance, line_clear)["fast_pursuit"])
        self.assertEqual(1, multi.approach_pressure(p, s, [minion], 2440))


if __name__ == "__main__":
    unittest.main()
