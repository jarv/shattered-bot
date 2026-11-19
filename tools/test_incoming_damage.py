import copy
import unittest
from tools.incoming_damage import observe,priority,key
from tools.test_challenge_systems import ready
from tools.policy_nodes import ordinary_combat
from tools.policy_runtime import Context


class IncomingDamageTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['objects']=[{'name':'gnoll scout','cell':25}]
        s['evaluation_stats']={'elapsed_turns':1}
        after=copy.deepcopy(s);after['hero']['hp']-=4;after['evaluation_stats']['elapsed_turns']=2
        return s,p,after

    def test_single_source_samples_require_two_hits_before_priority(self):
        s,p,after=self.encounter();observe(p,s,after)
        foes=s['objects']+[{'name':'marsupial rat','cell':31}]
        self.assertEqual(0,priority(p,s,foes,foes[0]))
        observe(p,s,after)
        self.assertEqual(4,priority(p,s,foes,foes[0]))
        self.assertEqual(0,priority(p,s,foes,foes[1]))

    def test_mixed_damage_dot_unseen_memory_and_long_intervals_not_attributed(self):
        for case in ('mixed','poison','memory','long','zero-turn','floor'):
            s,p,after=self.encounter()
            if case=='mixed':
                for st in (s,after):st['objects'].append({'name':'marsupial rat','cell':31})
            if case=='poison':after['hero']['buffs']=[{'name':'poisoned'}]
            if case=='memory':p.recent_threats[20]={'name':'rat','cell':20}
            if case=='long':after['evaluation_stats']['elapsed_turns']=4
            if case=='zero-turn':after['evaluation_stats']['elapsed_turns']=1
            if case=='floor':after['depth']=2
            self.assertIsNone(observe(p,s,after),case)
            self.assertFalse(p.incoming_damage_samples,case)

    def test_ordinary_swarm_attack_prefers_measured_damaging_enemy(self):
        s,p,after=self.encounter()
        rat={'name':'marsupial rat','cell':31,'health_bar':[2,10]}
        s['objects'].append(rat)
        scout=s['objects'][0]
        p.incoming_damage_samples[key(scout)]={'count':2,'hp_loss':8}
        p.incoming_damage_samples[key(rat)]={'count':2,'hp_loss':2}
        action=ordinary_combat(Context(p,s,enemies=s['objects'],active=s['objects'],engage=s['objects']))
        self.assertIsNotNone(action)
        target=p.target if action.action.get('type')=='item' else action.action.get('cell')
        self.assertEqual(scout['cell'],target)

    def test_same_name_different_champion_does_not_share_samples(self):
        s,p,after=self.encounter();observe(p,s,after);observe(p,s,after)
        champion=dict(s['objects'][0],description='_Blazing Champion_')
        self.assertNotEqual(key(s['objects'][0]),key(champion))

    def test_no_splitting_attack_gate_is_not_overridden_by_damage_priority(self):
        s,p,after=self.encounter()
        s['inventory'][0]['status']='0/4'
        foes=[{'name':'swarm of flies','cell':25},{'name':'swarm of flies','cell':31}]
        s['objects']=foes;p.incoming_damage_samples[key(foes[0])]={'count':2,'hp_loss':20}
        self.assertEqual(0,priority(p,s,foes,foes[0]))
