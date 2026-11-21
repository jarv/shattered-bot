import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.policy_decision import NoSafeAction,Finished,Decision,Intent
from tools.policy_runner import run
from tools.survival_policy import SurvivalPolicy
from tools.player_api import PlayerAPIError
from tools.test_survival_bot import state,fully_known
from tools.test_challenge_rules import verified


class NoEscapePolicy(MagePolicy):
    def choose(self,s):
        if s['hero']['hp']<=0:raise Finished('dead','Hero died')
        self.stop_no_safe_action('Test danger: no verified escape')


class DamageAPI:
    def __init__(self):
        self.observation=fully_known(state());self.observation['hero']['hp']=3
        for tile in self.observation['map']['cells']:
            if tile['cell']!=24:tile['terrain']=4
        self.actions=[]

    def step(self,action):
        self.actions.append(action)
        self.observation=copy.deepcopy(self.observation)
        self.observation['hero']['hp']-=1
        if self.observation['hero']['hp']<=0:self.observation['status']='dead'
        return self.observation


class ContinuationTests(unittest.TestCase):
    def test_default_ends_exhausted_planning_without_waiting_for_death(self):
        api=DamageAPI();p=NoEscapePolicy()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'decisions.jsonl';result=run(api,p,10,0,path)
            log=path.read_text()
        self.assertEqual('stuck-planner',result['outcome'])
        self.assertFalse(api.actions)
        self.assertEqual(1,result['continuation_errors'][0]['occurrences'])
        self.assertIn('planner_failure',log)
        self.assertIn('Test danger',result['planner_failure']['reason'])
        self.assertEqual('stuck planner (bot unable to proceed)',result['death_reason'])
        self.assertFalse(result['stop_policy']['stop_on_no_safe_action'])

    def test_strict_opt_in_preserves_no_escape_stop(self):
        api=DamageAPI();p=NoEscapePolicy(stop_on_no_safe_action=True)
        with tempfile.TemporaryDirectory() as temp:result=run(api,p,10,0,Path(temp)/'log.jsonl',bounded=True)
        self.assertEqual('blocked',result['outcome']);self.assertFalse(api.actions)

    def test_startup_verification_is_not_a_no_escape_failure(self):
        api=DamageAPI();p=MagePolicy()
        with tempfile.TemporaryDirectory() as temp:result=run(api,p,10,0,Path(temp)/'log.jsonl')
        self.assertEqual('blocked',result['outcome']);self.assertFalse(api.actions)
        self.assertFalse(result['continuation_errors'])

    def test_ambiguous_execution_is_not_retried(self):
        api=DamageAPI();p=NoEscapePolicy()
        def fail(action):
            api.actions.append(action);raise PlayerAPIError(500,'execution state unknown')
        api.step=fail
        with tempfile.TemporaryDirectory() as temp, patch('tools.until_death.best_effort',
                return_value=Decision({'type':'cell','cell':25},'admitted retreat')):
            with self.assertRaises(PlayerAPIError):run(api,p,10,0,Path(temp)/'log.jsonl')
        self.assertEqual(1,len(api.actions))

    def test_known_healing_is_tried_instead_of_unnecessary_damage(self):
        s=fully_known(state());s['hero']['hp']=3
        s['inventory'].append({'id':'heal','name':'potion of healing','actions':['DRINK']})
        p=MagePolicy()
        a=p.recover_no_safe_action(s,NoSafeAction('No rescue route'))
        self.assertEqual('heal',a.action['id']);self.assertEqual('DRINK',a.action['action'])

    def test_incomplete_loot_logs_error_and_allows_descent_without_clear_credit(self):
        s=fully_known(state());p=verified();p.update(s)
        p.loot[26]={'cell':26,'name':'Tomb'}
        with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'cell','cell':25},'descend',Intent.DESCEND)):
            action=p.choose(s)
        self.assertEqual(Intent.DESCEND,action.intent)
        self.assertIn('continuing descent',action.reason)
        self.assertFalse(p.descent_counts_as_clear())
        self.assertEqual('incomplete-loot-at-descent',p.continuation_errors[0]['kind'])
        self.assertEqual([{'cell':26,'name':'Tomb'}],p.continuation_errors[0]['detail']['items'])
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.missed_loot)  # A proposed descent is not proof of permanent loss.
        self.assertTrue(p.deferred_obligations)

    def test_strict_loot_opt_in_keeps_old_gate(self):
        s=fully_known(state());p=verified();p.stop_on_incomplete_loot=True;p.update(s)
        p.loot[26]={'cell':26,'name':'Tomb'}
        with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'cell','cell':25},'descend',Intent.DESCEND)):
            with self.assertRaisesRegex(Finished,'Observed loot incomplete'):p.choose(s)

    def test_no_safe_action_is_not_general_finished_or_tactical_decline(self):
        p=MagePolicy()
        with self.assertRaises(NoSafeAction):p.stop_no_safe_action('hazard')
        with self.assertRaises(Finished) as stopped:p.stop_unsafe('unverified seed')
        self.assertNotIsInstance(stopped.exception,NoSafeAction)
