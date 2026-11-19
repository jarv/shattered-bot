import copy
import unittest
from tools.test_regular_feedback import arena
from tools.policy_decision import Decision,Intent
from tools.pursuit_budget import observe_accepted
from tools.escape_commitment import reverses


class QuietEscapeReleaseTests(unittest.TestCase):
    def setup_plan(self):
        s,p=arena();p.escape_commitment={'edges':[(41,40)],'hp':s['hero']['hp'],'charges':0,'age':0}
        # Keep resources unchanged so only verified quiet-input accounting can release it.
        s['inventory'][0]['status']='0/3'
        p.pursuit_retreat_moves=1
        return s,p

    def test_three_accepted_quiet_inputs_release_route_for_onward_exploration(self):
        s,p=self.setup_plan();wait=Decision({'type':'wait'},'quiet hold',Intent.RECOVER)
        self.assertTrue(reverses(p,s,41))
        for _ in range(2):observe_accepted(p,s,wait,copy.deepcopy(s))
        self.assertIsNotNone(p.escape_commitment)
        observe_accepted(p,s,wait,copy.deepcopy(s))
        self.assertIsNone(p.escape_commitment);self.assertFalse(reverses(p,s,41))

    def test_recent_ranged_threat_or_harmful_status_keeps_escape_protection(self):
        for case in ('recent','poison','unseen'):
            s,p=self.setup_plan()
            if case=='recent':p.recent_threats[43]={'name':'gnoll trickster','cell':43}
            if case=='poison':s['hero']['buffs']=[{'name':'poisoned'}]
            if case=='unseen':p.unseen_damage_turns=1
            for _ in range(3):observe_accepted(p,s,Decision({'type':'wait'},'quiet hold'),copy.deepcopy(s))
            self.assertIsNotNone(p.escape_commitment,case)

    def test_visible_following_enemy_does_not_count_as_quiet(self):
        s,p=self.setup_plan();s['objects']=[{'name':'gnoll scout','cell':43}]
        for _ in range(3):observe_accepted(p,s,Decision({'type':'wait'},'observe enemy'),copy.deepcopy(s))
        self.assertIsNotNone(p.escape_commitment);self.assertEqual(0,p.pursuit_quiet_moves)


if __name__=='__main__':unittest.main()
