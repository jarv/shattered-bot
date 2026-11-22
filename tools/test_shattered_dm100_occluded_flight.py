"""Reduced public geometry from run 000131 decision 3609 (selection line 10391).

This is a selector fixture, not recovered runtime memory or a gameplay replay.
The original helper selects recorded step 964 with this reduction.
"""
import unittest

from tools.test_challenge_rules import verified
from tools.dm100_escape import choose, sees


def occluded_scene():
    walls = (868, 870, 916, 918, 966, 1013, 1014, 1015, 1016,
             1108, 1109, 1110, 1111, 1112)
    water = (725, 773, 821, 869, 917, 964, 965, 1012,
             1060, 1061, 1062, 1063, 1064)
    hidden = {677, 725, 868, 1014, 1015, 1016, 1063, 1064, 1111, 1112}
    cells = [dict(cell=c, terrain=terrain, visible=c not in hidden,
                  observed=True, effects=[])
             for terrain, group in ((4, walls), (29, water), (5, (677,)))
             for c in group]
    s = dict(scene='GameScene', status='ready', modal=False, depth=9, branch=0,
             danger_cells=[], map=dict(width=48, height=43, cells=cells),
             hero=dict(cell=1012, hp=19, max_hp=70, strength=13, level=11,
                       buffs=[dict(name='starving')], talents=[]),
             inventory=[], objects=[dict(name='DM-100', cell=1062)],
             ui=dict(texts=[], buttons=[]))
    p = verified()
    p.update(s)
    return s, p


class OccludedFlightTests(unittest.TestCase):
    def test_visible_but_wall_separated_caster_does_not_start_new_door_flight(self):
        s, p = occluded_scene()
        self.assertFalse(sees(p, s, 1062, 1012))
        self.assertIsNone(choose(p, s, s['objects']),
                          'Do not abandon existing cover solely because a caster is visible')
        self.assertIsNone(p.ranged_plan)
        self.assertEqual(0, p.ranged_cover_waits['dm-100'])
        self.assertFalse(p.loot_collection_receipts)

    def test_actual_lightning_exposure_still_admits_recorded_escape_route(self):
        s, p = occluded_scene()
        next(t for t in s['map']['cells'] if t['cell'] == 1013)['terrain'] = 29
        p.update(s)
        self.assertTrue(sees(p, s, 1062, 1012))
        action = choose(p, s, s['objects'])
        self.assertEqual(dict(type='cell', cell=964), action.action)

    def test_exposed_memory_still_prevents_unverified_cover_claim(self):
        s, p = occluded_scene()
        p.dm100_threat = dict(cell=869, age=0)
        self.assertTrue(sees(p, s, 869, 1012))
        action = choose(p, s, s['objects'])
        self.assertEqual(dict(type='cell', cell=964), action.action)


if __name__ == '__main__':
    unittest.main()
