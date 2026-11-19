import copy
import unittest
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.corruption_tactics import choose,observe
from tools.survival_policy import is_hostile
from tools.policy_runtime import Transaction
from tools.policy_decision import Decision


def corruption_case():
    s,p=arena();s['evaluation_stats']={'elapsed_turns':10}
    s['inventory'].append({'id':'corruption','name':'wand of corruption','identified':True,
        'curse_known':True,'known_cursed':False,'status':'3/3','actions':['ZAP']})
    weak=enemy('gnoll scout',34);weak['health_bar']=[3,10]
    other=enemy('marsupial rat',24);other['health_bar']=[10,10]
    s['objects']=[weak,other];p.update(s)
    return s,p,weak,other


class CorruptionUtilityTests(unittest.TestCase):
    def test_weakened_target_near_other_hostiles_earns_control_cast(self):
        s,p,weak,other=corruption_case();a=choose(p,s,s['objects'])
        self.assertEqual('corruption',a.action['id']);self.assertEqual(34,p.target)
        self.assertIn('utility control',a.reason)
        self.assertIn('not direct damage',p.planner.report['corruption_utility']['qualification'])

    def test_full_health_fishing_lone_finisher_adjacent_pressure_and_protected_foes_decline(self):
        for mode in ('full','lone','adjacent','boss','quest','doom','curse','empty'):
            s,p,weak,other=corruption_case()
            if mode=='full':weak['health_bar']=[10,10]
            if mode=='lone':s['objects']=[weak]
            if mode=='adjacent':other['cell']=41
            if mode=='boss':weak['name']='goo'
            if mode=='quest':weak['name']='gnoll trickster'
            if mode=='doom':weak['status_icons']=['Doom']
            if mode=='curse':s['inventory'][-1]['known_cursed']=True
            if mode=='empty':s['inventory'][-1]['status']='0/3'
            self.assertIsNone(choose(p,s,s['objects']),mode)

    def test_observed_negative_statuses_can_support_utility_but_not_guarantee_conversion(self):
        s,p,weak,other=corruption_case();weak['health_bar']=[10,10]
        weak['status_icons']=['Weakness','Hex']
        self.assertIsNotNone(choose(p,s,s['objects']))

    def test_wraith_can_be_control_target_with_no_direct_magic(self):
        s,p,weak,other=corruption_case();s['inventory'][0]['status']='0/4'
        weak['name']='wraith';weak.pop('health_bar');s['objects']=[weak]
        self.assertIsNotNone(choose(p,s,s['objects']))

    def test_accepted_cast_counts_only_target_input_and_reads_real_public_icons(self):
        s,p,weak,other=corruption_case();a=choose(p,s,s['objects'])
        self.assertIsNone(observe(p,s,a,copy.deepcopy(s)))
        self.assertFalse(p.corruption_attempts)
        before=copy.deepcopy(s);before['status']='targeting'
        after=copy.deepcopy(s);after['objects'][0]['status_icons']=['Corrupted']
        after['objects'][0]['health_bar']=[10,10]
        r=observe(p,before,Decision({'type':'cell','cell':34},'target'),after)
        self.assertTrue(r['corruption_visible_at_cast_cell'])
        self.assertEqual(1,p.corruption_attempts['total'])
        self.assertFalse(is_hostile(after['objects'][0]))
        self.assertTrue(is_hostile(after['objects'][1]))

    def test_disappearance_is_not_corruption_or_kill_evidence(self):
        s,p,weak,other=corruption_case();choose(p,s,s['objects']);s['status']='targeting'
        after=copy.deepcopy(s);after['status']='ready';after['objects']=[other]
        r=observe(p,s,Decision({'type':'cell','cell':34},'target'),after)
        self.assertFalse(r['corruption_visible_at_cast_cell'])

    def test_confirmed_corrupt_actor_is_excluded_but_amok_is_not_assumed_friendly(self):
        s,p,weak,other=corruption_case();weak['status_icons']=['Corruption']
        self.assertFalse(is_hostile(weak))
        weak['status_icons']=['Amok'];self.assertTrue(is_hostile(weak))

    def test_rejection_rolls_back_pending_and_cooldown_uses_elapsed_turns(self):
        s,p,weak,other=corruption_case();tx=Transaction(p,p.planner)
        choose(p,s,s['objects']);tx.rollback()
        self.assertIsNone(p.corruption_pending);self.assertFalse(p.corruption_attempts)
        p.corruption_ready_at['gnoll scout']=12
        self.assertIsNone(choose(p,s,s['objects']))
        s['evaluation_stats']['elapsed_turns']=12
        self.assertIsNotNone(choose(p,s,s['objects']))


if __name__=='__main__':unittest.main()
