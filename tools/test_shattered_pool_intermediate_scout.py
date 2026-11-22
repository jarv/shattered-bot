"""Reduced public geometry from run 000133 decisions 1626–1628.

An observation-only scout must finish its safe multi-step approach. This fixture
is not recovered runtime memory or a replay.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import neighbors, distance
from tools.puzzle_supplies import Demand, revisit_pool, prepare_supplies


def fixture():
    s = state()
    s['depth'] = 4
    s['hero'].update(cell=711, hp=43, max_hp=45, strength=11, buffs=[])
    groups = {
        4: [659,684,703,704,705,706,707,708,709,710,712,713,714,
            728,738,753,763,778,788,803,813,814,828,838,853,878,
            888,903,913,928,938],
        1: [660,685,686,687,729,730,731,732,733,734,735,812,837,
            862,864,887,912,937],
        29: [661,662,663,664,754,779,781,782,783,784,785,804,806,
             807,808,809,810,829,831,832,833,834,835,854,856,857,
             858,859,860,879,881,882,883,884,885,904,906,907,908,
             909,910,914,929],
        2: [688,689,736,737,762,787], 6: [711],
        14: [755,756,757,758,759,760,761,780,786,805,811,830,836,
             855,861,880,886,905,911,930,931,932,933,934,935,936],
        20: [839], 5: [863], 25: [889],
    }
    s['map'] = dict(width=25, height=49, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for t, cells in groups.items() for c in cells])
    s['objects'] = [dict(cell=782, name='giant piranha', sleeping=True),
                    dict(cell=834, name='giant piranha', sleeping=True),
                    dict(cell=911, name='Chest')]
    p = verified()
    p.update(s)
    return s, p


class PoolIntermediateScoutTests(unittest.TestCase):
    demand = Demand('pool', 'potion of invisibility', 782)

    def start(self):
        s, p = fixture()
        d = revisit_pool(p, s, self.demand, neighbors)
        self.assertEqual({'type': 'cell', 'cell': 735}, d.action)
        self.assertEqual((4, 0, 782, 734), p.pool_approach_pending)
        p.last_decision = d
        return s, p

    def test_actual_intermediate_step_preserves_observation_destination(self):
        s, p = self.start()
        arrived = copy.deepcopy(s)
        arrived['hero']['cell'] = 735
        arrived['inventory'].append(dict(id='crimson', name='crimson potion',
            identified=False, quantity=1, actions=['DRINK']))
        p.update(arrived)
        self.assertFalse(p.pool_approach_receipts)
        self.assertEqual((4, 0, 782, 734), p.pool_approach_pending)
        d = prepare_supplies(p, arrived, [], distance, neighbors)
        self.assertEqual({'type': 'cell', 'cell': 734}, d.action)
        p.last_decision = d
        finished = copy.deepcopy(arrived)
        finished['hero']['cell'] = 734
        p.update(finished)
        self.assertIn((4, 0, 782, 734), p.pool_approach_receipts)
        # Isolated return probe, not a claimed changed-policy trajectory.
        p.update(s)
        self.assertIsNone(revisit_pool(p, s, self.demand, neighbors))
        self.assertEqual(2, p.puzzle_revisit_steps['pool'])
        self.assertFalse(p.room_journey)
        self.assertFalse(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.piranha_rooms[911]['collected'])

    def test_invalid_or_unexecuted_intermediate_is_not_a_receipt(self):
        for blocker in ('no-move', 'unseen', 'hazard', 'branch', 'wrong-action'):
            with self.subTest(blocker=blocker):
                s, p = self.start()
                arrived = copy.deepcopy(s)
                arrived['hero']['cell'] = 735
                tile = next(t for t in arrived['map']['cells'] if t['cell']==735)
                if blocker == 'no-move':
                    arrived['hero']['cell'] = 711
                elif blocker == 'unseen':
                    tile['visible'] = False
                elif blocker == 'hazard':
                    tile['effects'] = ['cloud of toxic gas']
                elif blocker == 'branch':
                    arrived['branch'] = 1
                else:
                    p.last_decision.action = {'type': 'wait'}
                p.update(arrived)
                self.assertFalse(p.pool_approach_receipts)

    def test_new_hazard_at_destination_cancels_commitment(self):
        s, p = self.start()
        arrived = copy.deepcopy(s)
        arrived['hero']['cell'] = 735
        next(t for t in arrived['map']['cells']
             if t['cell']==734)['effects'] = ['cloud of toxic gas']
        p.update(arrived)
        d = revisit_pool(p, arrived, self.demand, neighbors)
        self.assertNotEqual((4, 0, 782, 734), p.pool_approach_pending)
        self.assertFalse(p.pool_approach_receipts)
        self.assertTrue(d is None or d.action != {'type':'cell', 'cell':734})


if __name__ == '__main__':
    unittest.main()
