"""Reduced public geometry from run 000070, decisions 628-629.

This is a deterministic helper fixture, not recovered runtime memory. The
intuition stone and unrelated floor work are omitted to isolate travel.
Only the first, unchanged input is followed by its recorded observation.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.priority_resources import targets
from tools.puzzle_supplies import prepare_supplies


def fixture():
    # Coordinates/terrain and visibility condensed from the two observations.
    rows = (
        ".#####.", ".+.....", "####t##", "   #t# ",
        "   #+# ", "  ~~~.#", " .~~~~#", "FFFFFF#", "PPPPPP#",
    )
    terrain = {".": 1, "#": 4, "+": 5, "~": 29, "F": 14, "P": 14,
               "t": 20}
    cells = []
    for y, row in enumerate(rows, 29):
        for x, ch in enumerate(row, 9):
            if ch == " ":
                continue
            c = y * 38 + x
            t = dict(cell=c, terrain=terrain[ch], observed=True,
                     visible=x in {12, 13, 14} and y <= 33)
            if ch == "F":
                t["effects"] = ["magical fire"]
            cells.append(t)
    # Mandatory matching-key obligation and publicly observed reward.
    cells.extend([dict(cell=528, terrain=10, observed=True, visible=False),
                  dict(cell=1494, terrain=14, observed=True, visible=False)])
    s = dict(scene="GameScene", status="ready", modal=False, depth=2, branch=0,
             hero=dict(cell=1229, hp=30, max_hp=30, strength=11, level=3,
                       buffs=[], talents=[]),
             inventory=[dict(id="indigo", name="indigo potion", quantity=1,
                             actions=["DROP", "THROW", "DRINK"]),
                        dict(id="ivory", name="ivory potion", quantity=1,
                             actions=["DROP", "THROW", "DRINK"])],
             objects=[dict(cell=1494, name="iron key",
                           top_item=dict(name="iron key"))],
             danger_cells=[], ui=dict(texts=[], buttons=[]),
             map=dict(width=38, height=42, cells=cells))
    p = MagePolicy()
    p.update(s)
    return p, s


def arrival(s):
    s = copy.deepcopy(s)
    s["hero"]["cell"] = 1267
    for t in s["map"]["cells"]:
        if 34 <= t["cell"] // 38 <= 37:
            t["visible"] = True
        if t["cell"] == 1267:
            t["terrain"] = 6
    return s


class FrostViewCommitmentTests(unittest.TestCase):
    def test_visible_fire_does_not_abandon_admitted_observation_route(self):
        p, s = fixture()
        first = prepare_supplies(p, s, [], distance, neighbors)
        self.assertEqual({"type": "cell", "cell": 1267}, first.action)
        self.assertEqual(1303, p.frost_view_plan["view"])
        s = arrival(s)
        p.update(s)
        d = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(d, "Visible fire must not interrupt committed observation travel")
        self.assertEqual({"type": "cell", "cell": 1304}, d.action)
        self.assertEqual((1267, 1304, 1303), d.navigation_route)
        self.assertTrue(all(c in p.paths(s) and c not in p.fire_buffer
                            for c in d.navigation_route))
        self.assertIn(1494, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        # No fabricated observation after this changed input.

    def test_existing_probe_safety_vetoes_still_preempt_travel(self):
        for case in ("enemy", "warning", "burning", "low-health", "probe"):
            with self.subTest(case=case):
                p, s = fixture()
                prepare_supplies(p, s, [], distance, neighbors)
                s = arrival(s)
                p.update(s)
                enemies = []
                if case == "enemy":
                    enemies = [dict(cell=1229, name="marsupial rat")]
                elif case == "warning":
                    s["danger_cells"] = [1304]
                elif case == "burning":
                    s["hero"]["buffs"] = [dict(name="burning")]
                elif case == "low-health":
                    s["hero"]["hp"] = 10
                else:
                    p.puzzle_probe = dict(depth=2, kind="frost", turns=0)
                self.assertIsNone(prepare_supplies(p, s, enemies, distance, neighbors))
                self.assertIn(1494, targets(p))


if __name__ == "__main__":
    unittest.main()
