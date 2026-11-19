"""Alchemy menus must tolerate absent inventory without inventing receipts."""
import unittest
from types import SimpleNamespace

try:
    from .alchemy_tactics import Brew, alchemy_menu
except ImportError:
    from alchemy_tactics import Brew, alchemy_menu


class Policy:
    def __init__(self, brew=None):
        brew = brew or Brew(('mystery meat',), 'stewed meat', 'cook food', 1)
        self.alchemy_plan = {
            'brew': brew, 'stage': 'bag', 'index': 0, 'steps': 0,
            'reserve': 0,
            'inventory_before': {brew.ingredients[0]: 2, brew.output: 0},
        }
        self.planner = SimpleNamespace(report={})

    def decision(self, action, reason):
        return action

    def stop_unsafe(self, reason):
        raise AssertionError(reason)


def scene(*labels, **extra):
    return dict({
        'scene': 'AlchemyScene', 'status': 'menu', 'modal': False,
        'hero': {},
        'ui': {
            'buttons': [{'id': str(n), 'label': label} for n, label in enumerate(labels)],
            'texts': ['Alchemy', 'Combine ingredients to create something new!', 'Energy: 1'],
            'energy_text': 'Energy: 1',
        },
    }, **extra)


class AlchemyOptionalInventoryTest(unittest.TestCase):
    def prepare_craft(self, policy):
        picker = scene('ration of food x2', 'mystery meat x2')
        picker['modal'] = True
        self.assertEqual(alchemy_menu(policy, picker), {'type': 'button', 'id': '1'})
        return alchemy_menu(policy, scene('Craft: stewed meat', 'Back'))

    def test_recorded_ingredient_transition_then_inventory_omitting_craft(self):
        policy = Policy()
        self.assertEqual(self.prepare_craft(policy), {'type': 'button', 'id': '0'})
        self.assertEqual(policy.alchemy_plan['before_counts'],
                         {'mystery meat': 2, 'stewed meat': 0})
        self.assertNotIn('alchemy_receipt', policy.planner.report)
        self.assertEqual(alchemy_menu(policy, scene('Back')), {'type': 'button', 'id': '0'})
        self.assertIsNone(policy.alchemy_plan)
        self.assertNotIn('alchemy_receipt', policy.planner.report)

    def test_public_inventory_still_verifies_real_differences(self):
        for inventory, increased, consumed in (
            ([{'name': 'mystery meat', 'quantity': 1}, {'name': 'stewed meat'}], True, True),
            ([{'name': 'mystery meat', 'quantity': 2}], False, False),
            ([], False, True),
        ):
            with self.subTest(inventory=inventory):
                policy = Policy()
                self.prepare_craft(policy)
                alchemy_menu(policy, scene('Back', inventory=inventory))
                receipt = policy.planner.report['alchemy_receipt']
                self.assertEqual(receipt['output_inventory_increased'], increased)
                self.assertEqual(receipt['ingredients_consumed'], consumed)

    def test_fallback_without_baseline_does_not_assume_zero(self):
        brew = Brew(('scroll of mirror image',), 'scroll of prismatic image',
                    'known recipe', 6, 'stone of flock')
        policy = Policy(brew)
        policy.alchemy_plan.update(stage='slot', index=1)
        action = alchemy_menu(policy, scene('Craft: stone of flock', 'Back'))
        self.assertEqual(action, {'type': 'button', 'id': '0'})
        self.assertNotIn('before_counts', policy.alchemy_plan)
        alchemy_menu(policy, scene('Back', inventory=[{'name': 'stone of flock'}]))
        self.assertNotIn('alchemy_receipt', policy.planner.report)


if __name__ == '__main__':
    unittest.main()
