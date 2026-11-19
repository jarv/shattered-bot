import copy
import json
import os
from pathlib import Path
import unittest

from tools.hunger_budget import observe,forecast,admits,prioritize_supply,travel_cost
from tools.policy_decision import Decision
from tools.test_challenge_systems import ready,item


class HungerBudgetTests(unittest.TestCase):
    def setup_budget(self, phase='hungry', food=False):
        from tools.mage_policy import MagePolicy
        s,_=ready()
        p=MagePolicy(engine='planner')
        p.challenges_verified=True
        s['evaluation_stats']={'elapsed_turns':0}
        s['hero']['buffs']=[{'name':phase}] if phase else []
        s['inventory']=[item('ration of food','EAT')] if food else []
        p.update(s)
        return s,p

    def test_hunger_projection_uses_clock_not_decision_count(self):
        s,p=self.setup_budget('')
        s['evaluation_stats']['elapsed_turns']=1
        s['hero']['buffs']=[{'name':'hungry'}]
        observe(p,s)
        self.assertEqual(149,p.hunger_projection['remaining'])
        for _ in range(10):observe(p,s)
        self.assertEqual(149,p.hunger_projection['remaining'])
        s['evaluation_stats']['elapsed_turns']=21
        observe(p,s)
        self.assertEqual(129,p.hunger_projection['remaining'])

    def test_search_spends_more_hunger_than_its_two_clock_turns(self):
        s,p=self.setup_budget('')
        s['hero']['buffs']=[{'name':'hungry'}]
        s['evaluation_stats']['elapsed_turns']=1
        observe(p,s)
        p.last_decision=Decision({'type':'search'},'test')
        s['evaluation_stats']['elapsed_turns']=3
        observe(p,s)
        self.assertEqual(137,p.hunger_projection['remaining'])

    def test_meal_is_credited_only_after_observed_consumption(self):
        s,p=self.setup_budget('starving')
        s['inventory']=[item('small food ration','EAT')]
        p.hunger_projection=None
        observe(p,s)
        p.last_decision=Decision({'type':'item','id':s['inventory'][0]['id'],'action':'EAT'},'test')
        observe(p,s)
        self.assertEqual(0,p.hunger_projection['remaining'])
        s['inventory']=[]
        s['hero']['buffs']=[{'name':'hungry'}]
        s['evaluation_stats']['elapsed_turns']=3
        observe(p,s)
        self.assertEqual(147,p.hunger_projection['remaining'])

    def test_floor_transition_does_not_reset_hunger_reserve(self):
        s,p=self.setup_budget('hungry')
        s['depth']+=1
        s['evaluation_stats']['elapsed_turns']=20
        p.update(s)
        self.assertEqual(0,p.hunger_projection['remaining'])

    def test_carried_food_supports_turns_but_ground_food_is_not_prepaid(self):
        s,p=self.setup_budget('hungry',True)
        before=forecast(p,s)
        p.loot[25]={'name':'ration of food','top_item':item('ration of food','EAT')}
        after=forecast(p,s)
        self.assertEqual(297,before['supported_turns'])
        self.assertEqual(before['supported_turns'],after['supported_turns'])
        self.assertEqual(25,after['next_supply']['cell'])
        self.assertGreater(after['reserved_turns'],30)

    def test_distant_or_sale_food_is_not_credited_as_reachable(self):
        s,p=self.setup_budget('hungry')
        p.loot[25]={'name':'ration of food','top_item':item('ration of food','EAT')}
        self.assertIsNone(forecast(p,s)['next_supply'])
        self.assertEqual(0,forecast(p,s)['optional_turns'])
        p.loot[25]['for_sale']=True
        self.assertEqual([],forecast(p,s)['known_food_routes'])

    def test_route_cost_accounts_for_slow_movement_and_closed_doors(self):
        s,p=self.setup_budget('')
        route=[24,25,26]
        plain=travel_cost(s,p,route)
        s['hero']['buffs']=[{'name':'crippled'}]
        p.tiles[25]['terrain']=5
        self.assertEqual(plain*2+1,travel_cost(s,p,route))

    def test_optional_turns_are_gated_before_reserve_is_spent(self):
        s,p=self.setup_budget('hungry',True)
        budget=forecast(p,s)['optional_turns']
        self.assertTrue(admits(p,s,budget))
        self.assertFalse(admits(p,s,budget+1))
        s['inventory']=[]
        self.assertFalse(admits(p,s,1))
        self.assertEqual(0,p.search_limit(s,40,True))
        self.assertEqual(0,p.sweep_limit(s))
        self.assertEqual(0,p.recovery_limit(s,True))

    def test_hungry_food_is_collected_before_reserve_runs_out_not_eaten(self):
        s,p=self.setup_budget('')
        p.hunger_projection['remaining']=40
        p.loot[25]={'name':'ration of food','top_item':item('ration of food','EAT')}
        a=prioritize_supply(p,s,[])
        self.assertEqual({'type':'cell','cell':25},a.action)
        s['inventory']=[item('ration of food','EAT')]
        from tools.exploration_budget import starving_food
        s['hero']['buffs']=[{'name':'hungry'}]
        self.assertIsNone(starving_food(p,s,[]))

    def test_raw_meat_and_unknown_potions_do_not_fund_optional_work(self):
        s,p=self.setup_budget('starving')
        s['inventory']=[item('mystery meat','EAT'),item('azure potion','DRINK')]
        self.assertEqual(0,forecast(p,s)['supported_turns'])
        self.assertFalse(admits(p,s,1))

    def test_exhausted_budget_prefers_exit_over_speculative_food_search(self):
        from tools.exploration_budget import selective_descent
        from tools.policy_decision import Intent
        s,p=self.setup_budget('starving')
        p.tiles[26]['terrain']=8
        a=selective_descent(p,s,[])
        self.assertIsNotNone(a)
        self.assertEqual(Intent.DESCEND,a.intent)
        self.assertIn('projected hunger',a.reason)

    def test_exhaustion_can_defer_loot_but_never_override_explicit_strict_stop(self):
        from tools.exploration_budget import selective_descent
        from tools.policy_decision import Intent
        s,p=self.setup_budget('starving')
        p.tiles[26]['terrain']=8
        p.loot[23]={'cell':23,'name':'azure potion','top_item':item('azure potion','DRINK')}
        self.assertEqual(Intent.DESCEND,selective_descent(p,s,[]).intent)
        p.stop_on_incomplete_loot=True
        self.assertIsNone(selective_descent(p,s,[]))

    def test_exhausted_budget_does_not_override_immediate_danger(self):
        from tools.exploration_budget import selective_descent
        s,p=self.setup_budget('starving')
        p.tiles[26]['terrain']=8
        self.assertIsNone(selective_descent(p,s,[{'name':'prison guard','cell':25}]))
        s['danger_cells']=[25]
        self.assertIsNone(selective_descent(p,s,[]))

    def test_on_diet_reduces_carried_food_projection(self):
        from tools.mage_policy import MagePolicy
        from tools.challenge_rules import ChallengeRules
        s,_=self.setup_budget('hungry',True)
        p=MagePolicy(rules=ChallengeRules(on_diet=True))
        p.update(s)
        self.assertEqual(97,forecast(p,s)['carried_food_turns'])

    def test_private_run48_starving_dead_end_search_is_not_admitted(self):
        path=os.environ.get('SHATTERED_RUN48_FOOD_FIXTURE')
        if not path:self.skipTest('optional private run48 recording')
        from tools.mage_policy import MagePolicy
        from tools.hidden_doors import seek_required_corridor_tip
        from tools.policy_geometry import distance
        rows={r['index']:r for r in json.loads(Path(path).read_text())}
        s=copy.deepcopy(rows[2088]['state'])
        p=MagePolicy(engine='planner')
        p.challenges_verified=True
        p.update(s)
        self.assertEqual(0,forecast(p,s)['optional_turns'])
        from unittest.mock import patch
        with patch('tools.hunger_budget.admits',return_value=True):
            admitted=seek_required_corridor_tip(p,s,[],distance)
        self.assertIsNotNone(admitted)
        self.assertEqual('search',admitted.action['type'])
        # Undo only the synthetic probe's search bookkeeping.
        p=MagePolicy(engine='planner')
        p.challenges_verified=True
        p.update(s)
        self.assertIsNone(seek_required_corridor_tip(p,s,[],distance))


if __name__=='__main__':
    unittest.main()
