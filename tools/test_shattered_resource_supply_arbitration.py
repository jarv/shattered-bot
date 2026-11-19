"""Regression for inaccessible progression loot suppressing puzzle supplies."""
import unittest
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools import priority_resources, puzzle_supplies


class ResourceSupplyArbitrationTest(unittest.TestCase):
    def setUp(self):
        self.state = {
            'status': 'ready', 'modal': False, 'depth': 2,
            'hero': {'cell': 630, 'hp': 30, 'max_hp': 30,
                     'buffs': [{'name': 'hungry'}]},
            'map': {'width': 47, 'height': 41},
            'inventory': [
                {'id': 'item-7', 'name': 'ration of food', 'actions': ['EAT']},
                {'id': 'item-9', 'name': 'turquoise potion',
                 'identified': False, 'actions': ['DRINK']},
            ],
        }
        self.policy = SimpleNamespace(
            loot={1272: {'name': 'scroll of upgrade',
                         'top_item': {'name': 'scroll of upgrade'}}},
            recent_threats={}, paths=Mock(return_value={630: None}),
            failed_moves=defaultdict(int), blocked=set(), room_blocked=set(),
            tiles={1272: {'terrain': 14}}, inventory_pressure=False,
            effects_block_movement=lambda tile: False,
            route=Mock(return_value=[630, 1272]), toward=Mock(),
        )

    def test_inaccessible_resource_allows_existing_puzzle_meal(self):
        meal = {'type': 'item', 'id': 'item-7', 'action': 'EAT'}
        with patch.object(puzzle_supplies, 'prepare_supplies', return_value=meal) as prepare:
            self.assertEqual(priority_resources.choose(self.policy, self.state, []), meal)
            self.assertEqual(prepare.call_args.args[:3], (self.policy, self.state, []))
        self.policy.toward.assert_not_called()
        self.assertIn(1272, self.policy.loot)

    def test_reachable_pickup_precedes_puzzle_supplies(self):
        self.policy.paths.return_value = {630: None, 1272: 630}
        with patch.object(puzzle_supplies, 'prepare_supplies') as prepare:
            result = priority_resources.choose(self.policy, self.state, [])
            self.assertIs(result, self.policy.toward.return_value)
            prepare.assert_not_called()

    def test_no_resource_does_not_claim_puzzle_preparation(self):
        self.policy.loot.clear()
        with patch.object(puzzle_supplies, 'prepare_supplies') as prepare:
            self.assertIsNone(priority_resources.choose(self.policy, self.state, []))
            prepare.assert_not_called()

    def test_recent_threat_preserves_safety_gate(self):
        self.policy.recent_threats = {677: {'name': 'marsupial rat'}}
        with patch.object(puzzle_supplies, 'prepare_supplies') as prepare:
            self.assertIsNone(priority_resources.choose(self.policy, self.state, []))
            prepare.assert_not_called()


if __name__ == '__main__':
    unittest.main()
