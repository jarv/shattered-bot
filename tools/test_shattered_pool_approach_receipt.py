"""Reduced public corridor/pool geometry from recording 000045, decisions 470–472."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import neighbors
from tools.puzzle_supplies import Demand, revisit_pool


def approach():
    s = state()
    s['depth'] = 2
    s['hero'].update(cell=636, hp=25, max_hp=25, strength=11, buffs=[])
    groups = {
        1: [637,638,646,647,697,797,847,896,897],
        4: [585,586,587,588,589,590,591,592,593,595,596,597,598,648,
            685,686,687,688,689,690,691,698,735,741,748,791,798,834,
            835,841,848,891,898,940,941,942,944,945,946,947,948],
        5: [635,641,785,943], 12: [594,734],
        14: [693,694,695,696,743,746,793,796,843,844,845,846],
        20: [636,639,640,747],
        29: [584,634,642,643,644,645,684,692,742,744,745,784,792,
             794,795,842,892,893,894,895],
    }
    s['map'] = dict(width=50, height=37, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True)
        for t, cells in groups.items() for c in cells])
    s['objects'] = [
        dict(cell=744, name='giant piranha', sleeping=True),
        dict(cell=694, name='turquoise potion',
             top_item=dict(name='turquoise potion', identified=False, quantity=1)),
    ]
    p = verified()
    p.update(s)
    return s, p


class PoolApproachReceiptTests(unittest.TestCase):
    demand = Demand('pool', 'potion of invisibility', 744)

    def select(self, p, s):
        d = revisit_pool(p, s, self.demand, neighbors)
        p.last_decision = d
        return d

    def test_arrival_does_not_restart_scout_after_other_work_leaves_bank(self):
        s, p = approach()
        self.assertEqual({'type':'cell', 'cell':637}, self.select(p, s).action)
        arrived = copy.deepcopy(s)
        arrived['hero']['cell'] = 637
        p.update(arrived)
        self.assertIsNone(self.select(p, arrived))
        # Independent selector probe after other work leaves the observed bank.
        p.update(s)
        self.assertIsNone(self.select(p, s),
                          'A completed approach scout must not preempt other floor work again')
        self.assertEqual(1, p.puzzle_revisit_steps['pool'])
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.completed_room_rewards)
        self.assertIn(694, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_selection_without_observed_arrival_is_not_a_receipt(self):
        s, p = approach()
        self.select(p, s)
        p.update(s)
        self.assertEqual({'type':'cell', 'cell':637}, self.select(p, s).action)

    def test_receipt_is_floor_local(self):
        s, p = approach()
        self.select(p, s)
        arrived = copy.deepcopy(s)
        arrived['hero']['cell'] = 637
        p.update(arrived)
        p.memory.reset_floor(636)
        p.update(s)
        self.assertEqual({'type':'cell', 'cell':637}, self.select(p, s).action)

    def test_unseen_or_cross_branch_arrival_does_not_count(self):
        for cross_branch in (False, True):
            with self.subTest(cross_branch=cross_branch):
                s, p = approach()
                self.select(p, s)
                arrived = copy.deepcopy(s)
                arrived['hero']['cell'] = 637
                if cross_branch:
                    arrived['branch'] = 1
                else:
                    next(t for t in arrived['map']['cells']
                         if t['cell']==637)['visible'] = False
                p.update(arrived)
                self.assertFalse(getattr(p, 'pool_approach_receipts', set()))


if __name__ == '__main__':
    unittest.main()
