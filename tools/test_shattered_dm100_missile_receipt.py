"""Reduced public inputs from run 000048, decisions 2907-2909.

The fixture reconstructs only targeting/receipt bookkeeping, not run memory.
No actions are dispatched or observations generated after an alternative.
"""
import copy
import unittest

from tools.combat_observation import observe_accepted_attack
from tools.policy_nodes import dm100_door_escape
from tools.policy_runtime import Context
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class DM100MissileReceiptTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s.update(depth=8, branch=0)
        s['hero'].update(cell=458, hp=13, max_hp=60, level=9)
        s['evaluation_stats'] = dict(experience=21, elapsed_turns=2866)
        s['inventory'][0].update(name='unstable staff of magic missile +3',
                                 status='5/7', identified=True,
                                 curse_known=True, known_cursed=False)
        terrain = {378: 1, 418: 1, 419: 4, 420: 29, 458: 29,
                   459: 6, 460: 1, 498: 4, 499: 4, 500: 1}
        s['map'] = dict(width=40, height=32, cells=[
            dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
            for c, t in terrain.items()])
        s['objects'] = [dict(name='DM-100', cell=459, health_bar=[8, 21],
                             status_icons=[])]
        s['ui']['texts'] = ['13', 'dodged']
        p = verified()
        p.update(s)
        targeting = copy.deepcopy(s)
        targeting['status'] = 'targeting'
        observe_accepted_attack(p, s, p.use(s['inventory'][0], 'ZAP', 'cast', target=459),
                                targeting)
        after = copy.deepcopy(s)
        after['objects'] = []
        after['hero']['hp'] = 14
        after['evaluation_stats'].update(experience=27, elapsed_turns=2867)
        after['inventory'][0]['status'] = '4/7'
        after['ui']['texts'] += ['7', '6', 'Magic Charge']
        return p, targeting, after

    def accept(self, p, targeting, after):
        return observe_accepted_attack(p, targeting, p.cell(459, 'target'), after)

    def test_visible_single_target_missile_xp_receipt_retires_matching_memory(self):
        p, targeting, after = self.fixture()
        self.assertIsNotNone(p.damage_pending)
        self.accept(p, targeting, after)
        self.assertIsNone(p.dm100_threat)
        # XP is a threat-retirement receipt, not an exact damage measurement.
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)

    def test_receipt_cannot_preempt_later_frontier_with_a_phantom_lane(self):
        p, targeting, after = self.fixture()
        self.accept(p, targeting, after)
        # Isolated geometry probe on a copy, not a gameplay continuation.
        probe = copy.deepcopy(after)
        probe['hero']['cell'] = 378
        self.assertIsNone(dm100_door_escape(Context(p, probe)))

    def test_ambiguous_or_unavailable_receipts_keep_the_memory(self):
        for mode in ('no-xp', 'wrong-xp', 'long-interval', 'level-change',
                     'floor-change', 'branch-change', 'unseen-neighbor',
                     'missing-neighbor', 'effects', 'survivor', 'other-enemy',
                     'other-memory', 'unknown-wand', 'cursed', 'status'):
            with self.subTest(mode=mode):
                p, before, after = self.fixture()
                if mode == 'no-xp': after['evaluation_stats']['experience'] = 21
                elif mode == 'wrong-xp': after['evaluation_stats']['experience'] = 28
                elif mode == 'long-interval': after['evaluation_stats']['elapsed_turns'] = 2869
                elif mode == 'level-change': after['hero']['level'] = 10
                elif mode == 'floor-change': after['depth'] = 9
                elif mode == 'branch-change': after['branch'] = 1
                elif mode == 'unseen-neighbor': after['map']['cells'][-1]['visible'] = False
                elif mode == 'missing-neighbor': after['map']['cells'].pop()
                elif mode == 'effects': after['map']['cells'][-1]['effects'] = ['fire']
                elif mode == 'survivor': after['objects'] = copy.deepcopy(before['objects'])
                elif mode == 'other-enemy': before['objects'].append(dict(name='skeleton', cell=460))
                elif mode == 'other-memory': p.dm100_threat['cell'] = 460
                elif mode == 'unknown-wand': before['inventory'][0]['identified'] = False
                elif mode == 'cursed': before['inventory'][0]['known_cursed'] = True
                elif mode == 'status': before['objects'][0]['status_icons'] = ['hasted']
                self.accept(p, before, after)
                self.assertIsNotNone(p.dm100_threat)


if __name__ == '__main__':
    unittest.main()
