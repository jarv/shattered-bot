"""Confirmed defeat receipts retire only the matching remembered caster."""
import copy
import unittest
from types import SimpleNamespace

from tools.test_regular_feedback import arena
from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory
from tools.policy_nodes import dm100_door_escape


class ConfirmedDM100RetirementTests(unittest.TestCase):
    def receipt(self):
        # Reduced public shape of decision 3287: adjacent DM-100, 8/21 bar,
        # accepted melee, disappearance and a newly displayed defeat message.
        before, policy = arena()
        before['objects'] = [{'name': 'DM-100', 'cell': 31,
                              'health_bar': [8, 21]}]
        before['ui'] = {'texts': []}
        policy.update(before)
        after = copy.deepcopy(before)
        after['objects'] = []
        after['ui']['texts'] = ['You defeated DM-100.']
        return before, policy, after

    def accept(self, policy, before, after):
        return observe_accepted_attack(policy, before,
                                       policy.cell(31, 'combat: melee'), after)

    def test_confirmed_caster_cannot_preempt_guard_after_pull(self):
        before, policy, after = self.receipt()
        feedback = self.accept(policy, before, after)
        self.assertTrue(feedback['censored'])
        self.assertIsNone(policy.dm100_threat)
        # Isolated alternative probe, not a continuation/replay of the run.
        pulled = copy.deepcopy(after)
        pulled['hero']['cell'] = 22
        guard = {'name': 'prison guard', 'cell': 23}
        pulled['objects'] = [guard]
        policy.update(pulled)
        self.assertFalse(exposed_memory(policy, pulled))
        context = SimpleNamespace(policy=policy, state=pulled, enemies=[guard],
                                  boss=False, hp=0.8)
        self.assertIsNone(dm100_door_escape(context))

    def test_disappearance_or_old_message_does_not_retire_threat(self):
        for mode in ('disappearance', 'old-message', 'other-kill'):
            before, policy, after = self.receipt()
            if mode == 'disappearance':
                after['ui']['texts'] = []
            elif mode == 'old-message':
                before['ui']['texts'] = list(after['ui']['texts'])
            else:
                after['ui']['texts'] = ['You defeated prison guard.']
            self.accept(policy, before, after)
            self.assertEqual(policy.dm100_threat['cell'], 31, mode)

    def test_different_remembered_caster_and_guard_plan_survive(self):
        before, policy, after = self.receipt()
        policy.dm100_threat = {'cell': 13, 'age': 0, 'turn': 1}
        policy.ranged_plan = {'name': 'prison guard', 'mode': 'cover'}
        self.accept(policy, before, after)
        self.assertEqual(policy.dm100_threat['cell'], 13)
        self.assertEqual(policy.ranged_plan['name'], 'prison guard')

    def test_matching_plan_retires_but_other_visible_caster_is_observed(self):
        before, policy, after = self.receipt()
        policy.ranged_plan = {'name': 'dm-100', 'mode': 'cover', 'goal': 40}
        self.accept(policy, before, after)
        self.assertIsNone(policy.ranged_plan)
        after['objects'] = [{'name': 'DM-100', 'cell': 13}]
        policy.update(after)
        self.assertEqual(policy.dm100_threat['cell'], 13)


if __name__ == '__main__':
    unittest.main()
