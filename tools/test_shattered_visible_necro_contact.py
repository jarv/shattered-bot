"""Reduced public run 000171 decisions 3490/3492, not recorded memory.

Only the observed bypass corridor, summon and clean withdrawal are retained.
Fresh helper bookkeeping is explicit; probes dispatch no input and do not
continue with later recorded observations after a changed choice.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.necromancer_tactics import choose_necromancer
from tools.policy_geometry import distance, neighbors, line_clear


def fixture(hp=21):
    terrain = {511: 19, 556: 2, 557: 1, 603: 19, 559: 19,
               605: 19, 606: 6, 602: 19}
    s = dict(scene="GameScene", status="ready", modal=False, depth=9, branch=0,
             hero=dict(cell=556, hp=hp, max_hp=70, name="mage",
                       strength=12, buffs=[], talents=[]),
             inventory=[], danger_cells=[], ui=dict(texts=[], buttons=[]),
             objects=[dict(cell=602, name="necromancer's skeleton",
                           health_bar=[9, 16], status_icons=["adrenaline"]),
                      dict(cell=606, name="necromancer", status_icons=[])],
             map=dict(width=45, height=32, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=True,
                      effects=[], **({"trap": "burning trap"} if t == 19 else {}))
                 for c, t in terrain.items()]))
    p = MagePolicy()
    p.update(s)
    return p, s


def select(p, s):
    return choose_necromancer(p, s, s["objects"], distance, neighbors, line_clear)


class VisibleNecroContactTests(unittest.TestCase):
    def test_wounded_visible_caster_approach_preserves_available_spacing(self):
        for hp in (21, 17):
            with self.subTest(hp=hp):
                p, s = fixture(hp)
                before = copy.deepcopy(s)
                d = select(p, s)
                self.assertEqual("necro: break contact with supported skeleton", d.reason)
                self.assertEqual(dict(type="cell", cell=511), d.action)
                self.assertGreater(distance(d.action["cell"], 602, 45), 1)
                self.assertEqual(before, s)
                self.assertIsNone(p.target)
                self.assertFalse(p.loot_collection_receipts)

    def test_healthy_visible_summoner_bypass_is_unchanged(self):
        p, s = fixture(70)
        d = select(p, s)
        self.assertEqual("necro: bypass minion toward summoner", d.reason)
        self.assertEqual(dict(type="cell", cell=557), d.action)

    def test_contact_free_visible_approach_remains_available_when_wounded(self):
        p, s = fixture()
        s["objects"][0]["cell"] = 647
        d = select(p, s)
        self.assertEqual("necro: bypass minion toward summoner", d.reason)
        self.assertGreater(distance(d.action["cell"], 647, 45), 1)

    def test_known_escape_still_precedes_approach(self):
        p, s = fixture()
        s["inventory"].append(dict(id="escape", name="potion of invisibility",
                                   actions=["DRINK"], identified=True))
        d = select(p, s)
        self.assertEqual(dict(type="item", id="escape", action="DRINK"), d.action)


if __name__ == "__main__":
    unittest.main()
