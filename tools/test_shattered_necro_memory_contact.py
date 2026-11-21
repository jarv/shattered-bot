"""Reduced public decision 2555 geometry from run 000088, not runtime memory.

Probe only the selecting helper; no changed decision receives a later observation.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.necromancer_tactics import choose_necromancer
from tools.policy_geometry import distance, neighbors, line_clear


def fixture(hp=3):
    # Width 34: 682 -> 716 would remain beside the summon at 717.
    # 648 is already observed water, away from that visible summon.
    terrain = {648: 29, 682: 29, 716: 29, 717: 29, 718: 29,
               750: 29, 751: 29, 752: 29, 753: 2, 754: 1, 755: 1}
    s = dict(scene="GameScene", status="ready", modal=False, depth=8, branch=0,
             hero=dict(cell=682, hp=hp, max_hp=55, name="mage",
                       strength=13, buffs=[dict(name="hungry")], talents=[]),
             inventory=[dict(id="staff", name="staff of magic missile +3",
                             identified=True, equipped=True, status="2/7",
                             actions=["ZAP"])],
             objects=[dict(cell=717, name="necromancer's skeleton",
                           status_icons=["adrenaline"])],
             danger_cells=[], ui=dict(texts=[], buttons=[]),
             map=dict(width=34, height=32, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=c != 755)
                 for c, t in terrain.items()]))
    p = MagePolicy()
    p.update(s)
    # Publicly last seen at decision 2554; supplied as a fixture clue only.
    p.enemy_sightings[755] = dict(cell=755, name="necromancer",
                                health_bar=[16, 21])
    return p, s


class NecroMemoryContactTests(unittest.TestCase):
    def test_hidden_caster_clue_cannot_override_spacing(self):
        for hp in (3, 27):
            with self.subTest(hp=hp):
                p, s = fixture(hp)
                d = choose_necromancer(p, s, s["objects"],
                                      distance, neighbors, line_clear)
                self.assertEqual("necro: break contact with supported skeleton",
                                 d.reason)
                self.assertEqual(dict(type="cell", cell=648), d.action)
                self.assertGreater(distance(d.action["cell"], 717, 34), 1)
                self.assertIsNone(p.target)
                self.assertIn(755, p.enemy_sightings)

    def test_healthy_memory_navigation_keeps_existing_admission(self):
        p, s = fixture(55)
        d = choose_necromancer(p, s, s["objects"],
                              distance, neighbors, line_clear)
        self.assertEqual("necro: investigate last visible summoner position",
                         d.reason)
        self.assertEqual(dict(type="cell", cell=716), d.action)

    def test_memory_can_still_guide_a_contact_free_step(self):
        p, s = fixture()
        s["objects"][0]["cell"] = 648
        d = choose_necromancer(p, s, s["objects"],
                              distance, neighbors, line_clear)
        self.assertEqual("necro: investigate last visible summoner position",
                         d.reason)
        self.assertEqual("cell", d.action["type"])
        self.assertGreater(distance(d.action["cell"], 648, 34), 1)
        self.assertIsNone(p.target)


if __name__ == "__main__":
    unittest.main()
