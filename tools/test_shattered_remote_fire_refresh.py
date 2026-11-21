"""Reduced public run 000087 terminal geometry; not recorded policy memory.

Only a preparation input is probed. No subsequent observation is fabricated.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.priority_resources import choose, targets


def fixture():
    rows = (
        "~~.+~~~~,,....+..  ", "~~,####### ~  #..~~",
        "~~.#     #~~  #.~~~", "~~.#     #~   #####",
        "####     #,   #    ", "         #.   #    ",
        "       ###.########", "       #...#^~~Fppp",
        "       #.#.#.~~Fppp", "       #~..#^~~Fppp",
        "       ###~+~~~Fppp", "         ###~~~Fppp",
        "           #~~~Fppp", "           #~~~Fppp",
        "           ########",
    )
    terrain = {".": 1, "#": 4, "+": 5, "/": 6, ",": 20,
               "~": 29, "p": 14, "F": 14, "^": 18}
    cells = []
    for y, row in enumerate(rows, 23):
        for x, ch in enumerate(row, 18):
            if ch == " ":
                continue
            t = dict(cell=y*42+x, terrain=terrain[ch], observed=True,
                     visible=y == 23)
            if ch == "F":
                t["effects"] = ["magical fire"]
            if ch == "^":
                t["trap"] = "summoning trap"
            cells.append(t)
    s = dict(scene="GameScene", status="ready", modal=False, depth=1,
             branch=0, hero=dict(cell=989, hp=25, max_hp=25, strength=10,
                                 buffs=[], talents=[]),
             inventory=[dict(id="potion", name="turquoise potion", quantity=1,
                             identified=False, actions=["DROP", "THROW", "DRINK"])],
             objects=[dict(cell=1296, name="scroll of upgrade",
                           top_item=dict(name="scroll of upgrade"))],
             danger_cells=[], ui=dict(texts=[], buttons=[]),
             map=dict(width=42, height=39, cells=cells))
    p = MagePolicy()
    p.update(s)
    return p, s


class RemoteFireRefreshTests(unittest.TestCase):
    def test_required_reward_can_prepare_a_distant_remembered_barrier(self):
        p, s = fixture()
        self.assertNotIn(1296, p.paths(s))
        d = choose(p, s, [])
        self.assertIsNotNone(d, "Distant observed fire needs a bounded safe observation approach")
        self.assertEqual({"type": "cell", "cell": 990}, d.action)
        self.assertGreater(len(d.navigation_route), 13)
        self.assertTrue(all(c in p.paths(s) and c not in p.fire_buffer
                            for c in d.navigation_route))
        self.assertIn(1296, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)

    def test_unsafe_context_or_exhausted_travel_cannot_start_approach(self):
        for case in ("enemy", "memory", "warning", "poison", "low-health",
                     "budget", "blocked-route", "plant-route"):
            with self.subTest(case=case):
                p, s = fixture()
                enemies = []
                if case == "enemy":
                    enemies = [dict(cell=988, name="marsupial rat")]
                if case == "memory":
                    p.recent_threats[988] = dict(cell=988, name="marsupial rat")
                if case == "warning":
                    s["danger_cells"] = [990]
                if case == "poison":
                    s["hero"]["buffs"] = [dict(name="poison")]
                if case == "low-health":
                    s["hero"]["hp"] = 12
                if case == "budget":
                    p.puzzle_revisit_steps["frost"] = 48
                if case == "blocked-route":
                    p.blocked.add(994)
                if case == "plant-route":
                    p.tiles[994]["plant"] = "firebloom"
                self.assertIsNone(choose(p, s, enemies))
                self.assertIn(1296, targets(p))
                self.assertFalse(p.puzzle_drinks)


if __name__ == "__main__":
    unittest.main()
