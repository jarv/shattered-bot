"""Reduced public frost room from run 000139, decision 267.

This is an isolated helper fixture, not recovered runtime memory. The retained
unknown potion was publicly retrieved; the earlier drink and unrelated floor
work are omitted. No observation is supplied after an alternative selection.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies


def fixture():
    rows = (
        "##W#W+####",
        "#.~~~~~..#",
        "#~~~~~t..#",
        "#FFFFFFFF#",
        "#........#",
        "#........#",
        "#........#",
        "##########",
    )
    terrain = {"#": 4, "W": 12, "+": 5, ".": 14, "~": 29,
               "t": 18, "F": 14}
    cells = []
    for y, row in enumerate(rows, 29):
        for x, ch in enumerate(row, 14):
            t = dict(cell=y * 35 + x, terrain=terrain[ch],
                     observed=True, visible=True)
            if ch == "F":
                t["effects"] = ["A wall of magical fire"]
            if ch == "t":
                t["trap"] = "worn dart trap"
            # Ordinary approach floor, distinct from the room's special floor.
            if ch == "." and y <= 31:
                t["terrain"] = 1
            cells.append(t)
    s = dict(
        scene="GameScene", status="ready", modal=False, depth=1, branch=0,
        danger_cells=[], ui=dict(texts=[], buttons=[]),
        hero=dict(name="mage", cell=1070, hp=25, max_hp=25, strength=10,
                  level=2, buffs=[]),
        inventory=[dict(id="bistre", name="bistre potion", quantity=1,
                        actions=["DROP", "THROW", "DRINK"])],
        objects=[dict(cell=c, name="ration of food",
                      top_item=dict(name="ration of food", quantity=1))
                 for c in (1172, 1243, 1245)],
        map=dict(width=35, height=38, cells=cells))
    p = MagePolicy()
    p.update(s)
    return p, s


class FrostBankCorridorTests(unittest.TestCase):
    def test_return_uses_observed_corridor_not_occluding_door_shortcut(self):
        p, s = fixture()
        d = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 1069}, d.action)
        self.assertEqual((1070, 1069, 1068, 1067), d.navigation_route)
        self.assertIn("stage frost hypothesis", d.reason)
        self.assertTrue(all(c not in p.fire_buffer for c in d.navigation_route))
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.loot_collection_receipts)
        self.assertTrue(all(c in p.loot for c in (1172, 1243, 1245)))

    def test_unsafe_corridor_does_not_fall_back_to_door(self):
        p, s = fixture()
        p.blocked.add(1069)
        d = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNone(d)
        self.assertFalse(p.puzzle_drinks)
        self.assertTrue(all(c in p.loot for c in (1172, 1243, 1245)))

    def test_existing_safety_gates_still_preempt(self):
        for case in ("enemy", "warning", "burning", "low-health"):
            with self.subTest(case=case):
                p, s = fixture()
                enemies = []
                if case == "enemy":
                    enemies = [dict(cell=1069, name="marsupial rat")]
                elif case == "warning":
                    s["danger_cells"] = [1069]
                elif case == "burning":
                    s["hero"]["buffs"] = [dict(name="burning")]
                else:
                    s["hero"]["hp"] = 10
                self.assertIsNone(prepare_supplies(p, s, enemies, distance, neighbors))
                self.assertFalse(p.puzzle_drinks)


if __name__ == "__main__":
    unittest.main()
