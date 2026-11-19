import unittest

from tools.test_challenge_systems import ready


class PursuitCrabPriorityTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['hero'].update(hp=12,max_hp=20)
        s['objects']=[{'name':'marsupial rat','cell':25},{'name':'sewer crab','cell':31}]
        p.challenge_combat.stalled_withdrawals=2;p.pursuit_retreat_moves=4
        return s,p

    def test_failing_accepted_pursuit_prefers_healthy_crab_over_healthy_rat(self):
        s,p=self.encounter();a=p.challenge_withdrawal(s,s['objects'])
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(31,p.target)
        self.assertTrue(p.planner.report['failing_withdrawal_target']['fast_crab_priority'])

    def test_visibly_weak_finish_remains_ahead_of_healthy_crab(self):
        s,p=self.encounter();s['objects'][0]['health_bar']=[2,10]
        a=p.challenge_withdrawal(s,s['objects'])
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(25,p.target)

    def test_without_accepted_retreats_existing_tie_break_is_unchanged(self):
        s,p=self.encounter();p.pursuit_retreat_moves=0
        a=p.challenge_withdrawal(s,s['objects'])
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(25,p.target)


if __name__=='__main__':unittest.main()
