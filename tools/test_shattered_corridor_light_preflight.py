"""Reduced public geometry from decision 650, not recovered runtime memory.

The original helper selects step 790 towards tip 744 / wall 698. A hidden
confusion trap was revealed only AFTER that step. No trap is supplied here.
"""
import unittest

from tools.hidden_doors import seek_required_corridor_tip
from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state


def corridor():
    s = state()
    s['depth'] = 2
    s['hero'].update(cell=837, hp=30, max_hp=30, buffs=[{'name': 'hungry'}])
    walls = {697, 698, 699, 743, 745, 746, 789, 792, 836, 838, 882, 884}
    floors = {744, 790, 791, 837, 883}
    s['map'] = dict(width=46, height=28, cells=[
        dict(cell=c, terrain=4 if c in walls else 1, visible=c != 699, observed=True,
             effects=[]) for c in sorted(walls | floors)])
    s['objects'] = []
    s['inventory'] = [dict(id='item-5', name='wand of prismatic light',
                           identified=False, curse_known=True, known_cursed=False,
                           quantity=1, actions=['DROP', 'THROW', 'ZAP'])]
    p = MagePolicy()
    p.update(s)
    return s, p


def select(s, p):
    return seek_required_corridor_tip(p, s, [], distance)


class CorridorLightPreflightTests(unittest.TestCase):
    def test_public_uncursed_light_is_used_before_unsearched_tip_approach(self):
        s, p = corridor()
        d = select(s, p)
        self.assertEqual({'type': 'item', 'id': 'item-5', 'action': 'ZAP'}, d.action)
        self.assertEqual(698, p.target)
        self.assertFalse(p.searched_walls)
        self.assertEqual(0, p.searches)
        self.assertEqual(1, p.tiles[790]['terrain'])  # No imagined trap discovery.

    def test_attempt_is_bounded_without_claiming_a_successful_scan(self):
        s, p = corridor()
        self.assertEqual('item', select(s, p).action['type'])
        # Isolated repeated-input probe, NOT a fabricated post-cast observation.
        self.assertEqual({'type': 'cell', 'cell': 790}, select(s, p).action)
        self.assertFalse(p.searched_walls)

    def test_rejection_rollback_and_floor_reset_preserve_honest_attempts(self):
        s, p = corridor()
        tx = Transaction(p, p.planner)
        select(s, p)
        tx.rollback()
        self.assertEqual('item', select(s, p).action['type'])
        p.memory.reset_floor(3)
        self.assertFalse(p.corridor_light_attempts)

    def test_no_uncertain_curse_empty_cooldown_or_magic_immunity_cast(self):
        for case in ('unknown-curse', 'cursed', 'empty', 'reserve', 'cooldown', 'immune', 'veto'):
            with self.subTest(case=case):
                s, p = corridor()
                wand = s['inventory'][0]
                if case == 'unknown-curse': wand['curse_known'] = False
                if case == 'cursed': wand['known_cursed'] = True
                if case == 'empty': wand['status'] = '0/2'
                if case == 'reserve': wand['status'] = '1/2'
                if case == 'cooldown': p.unknown_magic_cooldowns[wand['name']] = 30
                if case == 'immune': s['hero']['buffs'].append({'name': 'magic immunity'})
                if case == 'veto': p.item_action_allowed = lambda *args: False
                self.assertEqual('cell', select(s, p).action['type'])

    def test_no_cast_through_actor_or_unseen_ray_or_from_hazard(self):
        for case in ('actor', 'unseen', 'hazard'):
            with self.subTest(case=case):
                s, p = corridor()
                if case == 'actor': s['objects'] = [{'cell': 791, 'name': 'sad ghost'}]
                if case == 'unseen': p.tiles[791]['visible'] = False
                if case == 'hazard': p.tiles[837]['plant'] = 'sungrass'
                self.assertNotEqual('item', select(s, p).action['type'])

    def test_known_active_trap_still_excludes_original_step(self):
        s, p = corridor()
        # Independent safety fixture; not a predicted result of the new cast.
        p.tiles[790].update(terrain=18, trap='confusion gas trap')
        d = select(s, p)
        if d and d.action['type'] == 'cell':
            self.assertNotEqual(790, d.action['cell'])
        self.assertFalse(p.searched_walls)


if __name__ == '__main__':
    unittest.main()
