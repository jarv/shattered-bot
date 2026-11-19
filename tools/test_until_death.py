import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch,MagicMock
from tools.mage_policy import MagePolicy
from tools.policy_decision import Finished,GameplayBlocked
from tools.policy_runner import run
from tools.player_api import PlayerAPIError
from tools.test_continuation import DamageAPI
from tools.until_death import ClockDeadlock
from tools.survival_bot import configured_policy,main


class StalledPolicy(MagePolicy):
    def __init__(self):
        super().__init__()

    def choose(self,state):
        if state['hero']['hp']<=0:raise Finished('dead','Hero died')
        raise GameplayBlocked('Exploration exhausted without a safe route')


class UntilDeathTests(unittest.TestCase):
    def execute(self,api,policy,budget=1):
        with TemporaryDirectory() as temp:return run(api,policy,budget,0,Path(temp)/'trace.jsonl')

    def test_gameplay_block_and_action_budget_do_not_end_live_run(self):
        api=DamageAPI();r=self.execute(api,StalledPolicy())
        self.assertEqual('dead',r['outcome']);self.assertEqual(3,r['actions'])
        self.assertTrue(r['until_death']);self.assertEqual(3,len(api.actions))

    def test_long_hp_plateau_is_not_proof_of_immortality(self):
        api=DamageAPI();api.observation['evaluation_stats']={'elapsed_turns':0}
        steps=[0]
        def step(action):
            steps[0]+=1;api.observation=copy.deepcopy(api.observation)
            api.observation['evaluation_stats']['elapsed_turns']+=1
            if steps[0]>=80:
                api.observation['hero']['hp']-=1
                if api.observation['hero']['hp']<=0:api.observation['status']='dead'
            return api.observation
        api.step=step;r=self.execute(api,StalledPolicy())
        self.assertEqual('dead',r['outcome']);self.assertEqual(82,r['actions'])

    def test_identical_public_state_and_nonadvancing_clock_can_deadlock(self):
        api=DamageAPI();api.observation['evaluation_stats']={'elapsed_turns':0}
        def step(action):
            api.actions.append(action);return copy.deepcopy(api.observation)
        api.step=step;r=self.execute(api,StalledPolicy())
        self.assertEqual('deadlocked',r['outcome']);self.assertEqual(32,r['actions'])
        self.assertGreater(r['hero']['hp'],0)

    def test_changing_time_bubble_is_progress_even_if_world_clock_stays_still(self):
        api=DamageAPI();a=api.observation;a['evaluation_stats']={'elapsed_turns':0}
        a['hero']['buffs']=[{'name':'time bubble','description':'10 turns'}]
        b=copy.deepcopy(a);b['hero']['buffs'][0]['description']='9 turns'
        guard=ClockDeadlock()
        for _ in range(40):self.assertFalse(guard.observe(a,{'type':'wait'},b))

    def test_startup_ui_and_verification_errors_are_not_gameplay_recovery(self):
        class Unsafe(StalledPolicy):
            def choose(self,state):raise Finished('blocked','Unverified startup/unsupported UI')
        api=DamageAPI();r=self.execute(api,Unsafe())
        self.assertEqual('blocked',r['outcome']);self.assertFalse(api.actions)

    def test_ambiguous_api_execution_is_never_repeated(self):
        api=DamageAPI()
        def step(action):
            api.actions.append(action);raise PlayerAPIError(500,'execution unknown')
        api.step=step
        with self.assertRaises(PlayerAPIError):self.execute(api,StalledPolicy())
        self.assertEqual(1,len(api.actions))

    def test_survival_has_no_separate_until_death_mode_or_early_stop_flags(self):
        args=SimpleNamespace(challenge_preset=None,challenge=[],disable_challenge=[],without_on_a_diet=False,
                             goal='survival',engine='legacy',seed=None)
        self.assertEqual('survival',configured_policy(args).goal)
        self.assertFalse(hasattr(configured_policy(args),'until_death'))
        args.stop_on_no_safe_action=True
        with self.assertRaises(ValueError):configured_policy(args)

    def test_cli_keeps_live_game_open_on_technical_pause_but_closes_after_death(self):
        for outcome in ('blocked','dead'):
            with TemporaryDirectory() as temp:
                sock=MagicMock();sock.__enter__.return_value.connect_ex.return_value=1
                with patch('sys.argv',['survival_bot.py','--launch']), \
                        patch('tools.survival_bot.socket.socket',return_value=sock), \
                        patch('tools.survival_bot.configured_policy',return_value=SimpleNamespace(goal='survival')), \
                        patch('tools.survival_bot.launch_game',return_value=('api','process',Path(temp))), \
                        patch('tools.survival_bot.run',return_value={'outcome':outcome}), \
                        patch('tools.survival_bot.stop_game') as stop:
                    main()
                self.assertEqual(outcome=='dead',stop.called)


if __name__=='__main__':unittest.main()
