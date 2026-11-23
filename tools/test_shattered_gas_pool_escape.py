"""Reduced public geometry from run 000191 decisions 1032-1033.

This is a deterministic selector fixture, not recovered runtime memory or a
gameplay replay. No observations are supplied after a changed selection.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Finished
from tools.test_survival_bot import state
from tools.toxic_escape import escape


GAS = "A greenish cloud of toxic gas is swirling here."


def fixture():
    s = state()
    s["depth"] = 3
    s["hero"].update(cell=451, hp=29, max_hp=30, strength=11)
    floors = {**dict.fromkeys(range(338, 344), 29),
              395: 14, 396: 14, 397: 14, 451: 6,
              503: 1, 504: 1, 505: 20, 557: 1, 558: 1, 559: 1, 560: 5}
    gas = {451, 503, 504, 505, 558, 559}
    s["map"] = dict(width=54, height=48, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True,
             effects=[GAS] if c in gas else []) for c, t in floors.items()])
    s["objects"] = [dict(cell=338, name="giant piranha")]
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    return s, p


class GasPoolEscapeTests(unittest.TestCase):
    def test_clear_pool_bank_is_not_an_escape_destination(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertIn(396, p.room_blocked)
        self.assertNotIn(557, p.room_blocked)
        d = p.choose(s)
        self.assertEqual({"type": "cell", "cell": 504}, d.action)
        self.assertEqual("toxic-gas-escape", d.controller)
        self.assertEqual(557, p.planner.report["toxic_gas_escape"]["target"])
        self.assertEqual(2, p.planner.report["toxic_gas_escape"]["route_steps"])
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_gas_crossing_still_requires_all_existing_step_checks(self):
        for obstruction in ("unknown", "trap", "warning", "fire", "blocked"):
            s, p = fixture()
            # Only the evidenced two-step alternate exit remains.
            p.tiles = {c: t for c, t in p.tiles.items()
                       if c in {451, 396, 504, 557}}
            t = p.tiles[504]
            if obstruction == "unknown":
                t["observed"] = False
            elif obstruction == "trap":
                t["trap"] = "burning trap"
            elif obstruction == "warning":
                s["danger_cells"] = [504]
            elif obstruction == "fire":
                t["effects"].append("A fire is raging here.")
            else:
                p.blocked.add(504)
            with self.subTest(obstruction=obstruction), self.assertRaises(Finished):
                escape(p, s)

    def test_unblocked_clear_door_is_still_a_valid_first_exit(self):
        s, p = fixture()
        s["hero"]["cell"] = 505
        for t in s["map"]["cells"]:
            if t["cell"] == 451:
                t.update(terrain=5, effects=[])
        p.update(s)
        self.assertEqual(451, escape(p, s).action["cell"])


if __name__ == "__main__":
    unittest.main()
