import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.policy_decision import Finished, TacticalBlocked
from tools.policy_runner import run
from tools.survival_policy import SurvivalPolicy
from tools.test_challenge_systems import ready
from tools.test_survival_bot import state


class TacticalRecoveryTests(unittest.TestCase):
    def test_exhausted_fallback_prefers_hittable_adjacent_rat_to_evasive_snake(self):
        from tools.policy_decision import TacticalBlocked
        s,p=ready()
        s['inventory']=[]
        s['objects']=[{'name':'sewer snake','cell':25},{'name':'marsupial rat','cell':23}]
        p.walkable=lambda *a,**k:False
        p.charged_magic=lambda *a:[]
        p.best_attack=lambda state,e:p.cell(e['cell'],'attack observed target')
        action=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','no safe retreat'))
        self.assertEqual(23,action.action['cell'])

    def test_unresolved_room_deferral_is_logged_and_returned_without_fake_completion(self):
        from unittest.mock import patch
        from tools.policy_decision import Decision, Intent
        s,p=ready()
        for tile in s["map"]["cells"]:
            if tile["cell"]==17:tile["terrain"]=8
            if tile["cell"]==26:tile["effects"]=["A wall of dense bright green fire, caused by magic; extinguish it."]
        p.update(s)
        class API:
            observation=s
            def step(self,action):return self.observation
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"run.jsonl"
            with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":17},"descend",Intent.DESCEND)):
                result=run(API(),p,1,0,path,bounded=True)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(1,result["actions"])
        self.assertTrue(any("nonfatal_obligations" in row for row in rows))
        self.assertEqual("deferred-unfinished",result["deferred_obligations"][0]["status"])

    def test_unavailable_frost_staging_is_deferred_without_unsafe_drinking_or_ending(self):
        from tools.test_challenge_systems import item
        from tools.potion_stash import protect_potions
        from tools.puzzle_supplies import prepare_supplies
        from tools.policy_geometry import distance, neighbors
        s,p=ready()
        candidate=dict(item("crimson potion","DRINK"),quantity=2)
        s["inventory"].append(candidate)
        with self.assertRaises(TacticalBlocked) as caught:
            protect_potions(p,s,candidate,distance,neighbors,lambda *a,**k:False)
        action=p.recover_tactical_block(s,caught.exception)
        self.assertIsNotNone(action)
        self.assertNotEqual("DRINK",action.action.get("action"))
        from tools.objective_planning import preparation_allowed
        self.assertFalse(preparation_allowed(p,s))
        self.assertTrue(p.deferred_obligations)
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))

    def test_runner_logs_multiple_soft_failures_and_continues_to_actual_outcome(self):
        class Policy(SurvivalPolicy):
            def choose(self,observation):
                if observation["status"]=="dead":raise Finished("dead","Hero died")
                self.stop_tactical("test-stall","unexpected tactical condition")
            def recover_tactical_block(self,observation,blocked):
                self.update(observation)
                self.soft_failures[blocked.code]+=1
                return self.decision({"type":"wait"},"continue")
        class API:
            observation=state()
            calls=0
            def step(self,action):
                self.calls+=1
                self.observation=copy.deepcopy(self.observation)
                if self.calls==2:
                    self.observation["status"]="dead"
                    self.observation["hero"]["hp"]=0
                return self.observation
        policy,api=Policy(),API()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"run.jsonl"
            result=run(api,policy,4,0,path,bounded=True)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual("dead",result["outcome"])
        self.assertEqual(2,result["actions"])
        self.assertEqual(2,sum("soft_failure" in row for row in rows))
        self.assertEqual(2,policy.soft_failures["test-stall"])

    def test_hard_gate_is_not_softened(self):
        class Policy(SurvivalPolicy):
            def choose(self,observation):raise Finished("blocked","seed verification missing")
            def recover_tactical_block(self,*args):raise AssertionError("must not recover a hard gate")
        class API:
            observation=state()
        with tempfile.TemporaryDirectory() as directory:
            result=run(API(),Policy(),1,0,Path(directory)/"run.jsonl")
        self.assertEqual("blocked",result["outcome"])
        self.assertEqual(0,result["actions"])

    def test_recovery_never_attacks_last_seen_enemy_or_enters_forbidden_ground(self):
        s,p=ready()
        p.recent_threats[25]={"name":"gnoll scout","cell":25}
        p.walkable=lambda *a,**k:False
        p.best_attack=lambda *a,**k:(_ for _ in ()).throw(AssertionError("no visible enemy to attack"))
        action=p.recover_tactical_block(s,TacticalBlocked("recent-pursuit","arbitrary prose"))
        self.assertEqual("wait",action.action["type"])
        self.assertEqual("tactical-recovery",action.controller)
