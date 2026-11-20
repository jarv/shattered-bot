"""Known invisibility is not an unknown-potion experiment.

Reduced public geometry from decision 174: the ordinary approach has water at
410, a closed entrance at 449, and the remembered pool chest at 646. These are
independent selector fixtures, not a replay or a claim of successful retrieval.
"""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.piranha_tactics import choose, pending
from tools.puzzle_supplies import safe_test_bank


def approach(pos=369, visible=False, known=True):
    s, _ = arena()
    s['hero'].update(cell=pos, hp=25, max_hp=25, strength=11, buffs=[])
    groups = {
        4: [493,532,571,610,649,688,376,415,454,337,333,335,374,
            411,412,413,331,409,448,485,486,487,332,450,526,565,
            604,643,682,683,684,685,686,687],
        20: [334], 1: [372,641], 2: [373,446,563,602],
        33: [329,330,408,447],
        29: [368,369,407,371,410,527,528,529,530,566,567,568,569,
             570,605,606,607,608,609,644,645,647,648],
        5: [370,449], 14: [488,489,490], 11: [646],
        0: [524,525,564,603,642,680,681],
    }
    s['map'] = dict(width=39, height=32, cells=[
        dict(cell=c, terrain=t, visible=visible, observed=True)
        for t,cells in groups.items() for c in cells])
    s['objects'] = []
    s['inventory'].append(dict(id='invis', name='potion of invisibility' if known else 'bistre potion',
                               identified=known, quantity=1, actions=['DROP','THROW','DRINK']))
    p = verified()
    p.update(s)
    # Remembered public habitat and chest, not a fabricated current fish location.
    water=set(groups[29])-{368,369,407,371,410}
    p.piranha_rooms[646] = dict(water=water, collected=False)
    p.loot[646] = dict(cell=646, name='Chest')
    from tools.piranha_tactics import observe
    observe(p,s)
    return s,p


class KnownPoolStagingTests(unittest.TestCase):
    def test_known_supply_revisits_ordinary_water_without_drinking_remotely(self):
        s,p=approach()
        before=copy.deepcopy(s)
        d=choose(p,s,[])
        self.assertIsNotNone(d, 'Known supply must not require an unknown-test bank')
        self.assertEqual({'type':'cell','cell':370},d.action)
        self.assertTrue(d.navigation)
        self.assertEqual(410,p.planner.report['piranha_room']['bank'])
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        self.assertIn(646,pending(p))
        self.assertEqual(before,s)

    def test_visible_known_bank_opens_entrance_before_any_drink(self):
        s,p=approach(410,True)
        d=choose(p,s,[])
        self.assertIsNotNone(d)
        self.assertEqual({'type':'cell','cell':449},d.action)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        self.assertIn(646,pending(p))

    def test_unknown_water_test_and_hazard_exclusions_are_unchanged(self):
        s,p=approach(410,True,False)
        self.assertFalse(safe_test_bank(p,s,410,distance,neighbors,allow_dry=True,pool_bank=True))
        self.assertIsNone(choose(p,s,[]))
        s,p=approach(410,True)
        p.room_blocked.update({371,410,372,449,370})
        self.assertIsNone(choose(p,s,[]))
        self.assertIsNone(p.room_journey)
        self.assertIn(646,pending(p))

    def test_water_arrival_requires_visibility_and_no_trap(self):
        for visible,trap in ((False,False),(True,True)):
            with self.subTest(visible=visible,trap=trap):
                s,p=approach(410,visible)
                if trap:
                    p.tiles[410]['trap']='poison dart trap'
                self.assertIsNone(choose(p,s,[]))
                self.assertIsNone(p.room_journey)
                self.assertIn(646,pending(p))


if __name__ == '__main__':
    unittest.main()
