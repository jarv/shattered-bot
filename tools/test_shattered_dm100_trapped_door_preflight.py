"""Reduced public run 000170 decision 2729 (selection log line 8144).

Only the selected route and its destination neighborhood are retained.
The exhausted-door set is explicit reconstructed helper bookkeeping, not
recorded memory. No alternative input is dispatched or continued.
"""
import copy
import unittest

from tools.dm100_escape import choose
from tools.test_challenge_rules import verified


def trapped_door():
    terrain = {1021: 29, 1022: 29, 977: 29, 978: 29, 1025: 29,
               1072: 5, 1027: 14, 981: 5,
               934: 4, 935: 18, 936: 18, 980: 4, 982: 4,
               1026: 4, 1028: 0}
    s = dict(scene="GameScene", status="ready", modal=False, depth=7, branch=0,
             danger_cells=[], hero=dict(cell=1021, hp=29, max_hp=55,
             level=8, strength=12, buffs=[dict(name="hungry")], talents=[]),
             inventory=[], objects=[dict(name="DM-100", cell=834),
                                    dict(name="skeleton", cell=928)],
             map=dict(width=46, height=33, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=c in
                      {1021, 1022, 977, 978, 1025, 1072, 934, 980, 1026},
                      **({"trap": "explosive trap"} if t == 18 else {}))
                 for c, t in terrain.items()]),
             ui=dict(texts=[], buttons=[]))
    p = verified()
    p.update(s)
    # The recording exhausted the 1072 bank at decisions 2717-2722,
    # then selected another door at 2729. This is not full memory recovery.
    p.dm100_failed_doors.add(1072)
    return s, p


class TrappedDoorPreflightTests(unittest.TestCase):
    def test_known_trap_room_is_not_a_door_flight_destination(self):
        s, p = trapped_door()
        before = copy.deepcopy(s)
        d = choose(p, s, s["objects"])
        self.assertIsNone(d, "Do not start the recorded seven-step flight to a door with no admissible far bank")
        self.assertIsNone(p.ranged_plan)
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)

    def test_preflight_does_not_ban_unknown_door_scouting(self):
        s, p = trapped_door()
        del p.tiles[935]
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=1022), d.action)
        self.assertEqual(981, p.ranged_plan["door"])

    def test_clean_far_bank_retains_existing_door_flight(self):
        s, p = trapped_door()
        p.tiles[935].update(terrain=14)
        p.tiles[935].pop("trap")
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=1022), d.action)
        self.assertEqual(981, p.ranged_plan["door"])

    def test_bank_preflight_preserves_existing_hazard_and_occupancy_vetoes(self):
        for hazard in ("plant", "effect", "loot", "occupied"):
            with self.subTest(hazard=hazard):
                s, p = trapped_door()
                p.tiles[935].update(terrain=14)
                p.tiles[935].pop("trap")
                enemies = list(s["objects"])
                if hazard == "plant":
                    p.tiles[935]["plant"] = "firebloom"
                elif hazard == "effect":
                    p.tiles[935]["effects"] = ["A fire is raging here."]
                elif hazard == "loot":
                    p.loot[935] = dict(name="scroll of upgrade", cell=935)
                else:
                    enemies.append(dict(name="skeleton", cell=935))
                self.assertIsNone(choose(p, s, enemies))
                self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
