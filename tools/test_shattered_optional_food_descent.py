"""Reduced gate fixture: run 000017, decision 3442's only target was food.

This isolates validation of an already selected descent, not its navigation
selection or a replay. The unreachable ration remains an unfinished obligation.
"""
import unittest
from unittest.mock import patch

from tools.loot_completion import required_loot
from tools.policy_decision import Decision, Finished, Intent
from tools.priority_resources import choose, targets
from tools.survival_policy import SurvivalPolicy
from tools.test_regular_feedback import arena


class OptionalFoodDescentTests(unittest.TestCase):
    def encounter(self, name='ration of food', strict=False):
        s, p = arena()
        s['hero'].update(hp=65, max_hp=65, buffs=[{'name': 'hungry'}])
        s['objects'] = []
        p.stop_on_incomplete_loot = strict
        p.tiles[41]['terrain'] = 8
        # A remembered ration beyond an admitted fire boundary, reduced from
        # cell 157 and boundaries 298..304 in the recorded veto at decision 3442.
        p.tiles[10].update(terrain=14, visible=False)
        p.fire_buffer.add(10)
        p.loot[10] = {'cell': 10, 'name': name,
                      'top_item': {'name': name, 'identified': True, 'quantity': 1}}
        return s, p

    def descend(self, s, p):
        decision = Decision({'type': 'cell', 'cell': 41}, 'stairs: selected descent', Intent.DESCEND)
        with patch.object(SurvivalPolicy, 'choose', return_value=decision):
            return p.choose(s)

    def test_unreachable_food_is_deferred_not_a_permanent_progression_veto(self):
        s, p = self.encounter()
        self.assertNotIn(10, p.paths(s))
        self.assertIn(10, targets(p))
        try:
            decision = self.descend(s, p)
        except Finished as blocked:
            self.fail('Optional food must reach normal unfinished-loot handling: ' + blocked.reason)
        self.assertEqual(Intent.DESCEND, decision.intent)
        self.assertIn(10, required_loot(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.descent_counts_as_clear())
        self.assertTrue(any(r['kind'] == 'incomplete-loot-at-descent'
                            for r in p.continuation_errors))
        self.assertTrue(p.deferred_obligations)
        self.assertIn(10, p.fire_buffer)

    def test_strict_loot_still_blocks_food(self):
        s, p = self.encounter(strict=True)
        with self.assertRaisesRegex(Finished, 'Observed loot incomplete'):
            self.descend(s, p)

    def test_upgrade_and_strength_still_mandatory(self):
        for name in ('scroll of upgrade', 'potion of strength'):
            with self.subTest(name=name):
                s, p = self.encounter(name)
                with self.assertRaisesRegex(Finished, 'upgrade/strength resource remains uncollected'):
                    self.descend(s, p)
                self.assertIn(10, required_loot(p))

    def test_matching_key_keeps_existing_gate(self):
        s, p = self.encounter('iron key')
        p.tiles[11]['terrain'] = 10
        with self.assertRaisesRegex(Finished, 'resource remains uncollected'):
            self.descend(s, p)

    def test_reachable_food_keeps_pickup_priority(self):
        s, p = self.encounter()
        p.fire_buffer.clear()
        decision = choose(p, s, [])
        self.assertIsNotNone(decision)
        self.assertEqual(Intent.LOOT, decision.intent)
        self.assertIn('food pickup', decision.reason)


if __name__ == '__main__':
    unittest.main()
