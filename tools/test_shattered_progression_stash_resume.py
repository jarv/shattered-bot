"""Run 28: required fire-room loot must not preempt its own potion stash."""
import copy
import unittest

from tools.policy_decision import Finished
from tools.policy_geometry import distance
from tools.potion_stash import advance_stash
from tools.priority_resources import targets
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fire_room():
    # Public geometry reduction of decision 1203, log line 3542. Omitted
    # cells stay unknown. No potion identity is taken from the death screen.
    s = state()
    s['depth'] = 4
    s['hero'].update(cell=1307, hp=34, max_hp=35, level=4, strength=10)
    groups = {
        1: [1306,1307,1308,1310,1311,1346,1347,1348,1349,1350,1351,
            1386,1387,1388,1389,1390,1391],
        4: [1265,1266,1267,1269,1270,1271,1272,1305,1312,1345,1352,
            1385,1392,1425,1432,1465,1472,1505,1512,1545,1552,
            1585,1586,1587,1588,1589,1590,1591,1592],
        6: [1268],
        14: [1466,1467,1468,1469,1470,1471,1506,1507,1508,1509,
             1510,1511,1546,1547,1548,1549,1550,1551],
    }
    cells = [dict(cell=c, terrain=t, visible=True, observed=True)
             for t, cs in groups.items() for c in cs]
    cells.append(dict(cell=1309, terrain=18, visible=True, observed=True,
                      trap='shocking trap'))
    cells.extend(dict(cell=c, terrain=14, visible=True, observed=True,
                      effects=["A wall of dense bright green fire is here, seemingly caused by magic. "
                               "It's so dense that you can't move through it, and it ignites anything "
                               "that gets too close. It shows no signs of burning down naturally, "
                               "you'll need to use something to extinguish it."])
                 for c in range(1426,1432))
    s['map'] = dict(width=40, height=41, cells=cells)
    s['inventory'] += [
        dict(id='amber', name='amber potion', quantity=1, identified=False,
             actions=['DROP','THROW','DRINK']),
        dict(id='haste', name='potion of haste', quantity=1, identified=True,
             actions=['DROP','THROW','DRINK']),
        dict(id='azure', name='azure potion', quantity=1, identified=False,
             actions=['DROP','THROW','DRINK']),
    ]
    s['objects'] = [
        dict(cell=c, name=name, top_item=dict(name=name, identified=True))
        for c,name in [(1268,'gold x79'), (1471,'iron key'),
                       (1547,'scroll of upgrade'), (1551,'ration of food')]
    ]
    p = verified()
    return s,p


class ProgressionStashResumeTests(unittest.TestCase):
    def started_stash(self):
        s,p = fire_room()
        # These two inputs agree with recorded decisions 1203 and 1204.
        d = p.choose(s)
        self.assertEqual({'type':'cell','cell':1346}, d.action)
        s['hero']['cell'] = 1346
        d = p.choose(s)
        self.assertEqual({'type':'cell','cell':1307}, d.action)
        self.assertEqual((1346,1311,'drop'),
                         (p.potion_stash['bank'],p.potion_stash['cell'],
                          p.potion_stash['phase']))
        return s,p

    def test_resume_existing_stash_instead_of_restarting_fire_staging(self):
        s,p = self.started_stash()
        s['hero']['cell'] = 1307
        # Isolated selection at decision 1205: no dispatch or later recording
        # is fed to the changed policy after this first divergence.
        expected = advance_stash(copy.deepcopy(p), copy.deepcopy(s), [], distance)
        self.assertIsNotNone(expected)
        d = p.choose(s)
        self.assertEqual(expected.action, d.action,
                         'Pending progression must allow its started stash to advance')
        self.assertEqual('potion: approach remote safe stash', d.reason)
        self.assertIn(1547, targets(p))
        self.assertNotIn(1547, p.paths(s))
        self.assertEqual({}, p.potion_stash['dropped'])
        self.assertIsNone(p.potion_stash['pending'])
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.deferred_room_controllers)

    def test_stash_drop_still_needs_a_public_receipt(self):
        s,p = self.started_stash()
        # Separate fixture, not continuation after the changed selection.
        s['hero']['cell'] = 1311
        d = p.choose(s)
        self.assertEqual('DROP', d.action.get('action'))
        self.assertEqual('haste', d.action.get('id'))
        self.assertEqual({}, p.potion_stash['dropped'])
        with self.assertRaises(Finished):
            p.choose(s)  # Inventory unchanged: do not invent a successful drop.

    def test_warning_still_preempts_preparation(self):
        s,p = self.started_stash()
        s['danger_cells'] = [1346]
        before = copy.deepcopy(p.potion_stash)
        self.assertIsNone(p.preparation(s, []))
        self.assertEqual(before, p.potion_stash)
        self.assertIn(1547, targets(p))


if __name__ == '__main__':
    unittest.main()
