import unittest
from unittest.mock import patch

from tools.test_challenge_systems import ready,item
from tools.exploration_budget import current_floor_food_work,selective_descent
from tools.policy_decision import Decision,Intent,Finished
from tools.survival_policy import SurvivalPolicy


class CurrentFloorFoodTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['hero'].update(hp=20,max_hp=20,buffs=[{'name':'starving'}])
        s['inventory']=[];p.tiles[26]['terrain']=8
        work=[23];original=p.exploration_report
        p.exploration_report=lambda state,paths:dict(original(state,paths),unexplored_frontiers=list(work),unopened_doors=[])
        return s,p,work

    def test_starvation_searches_current_floor_before_known_stairs(self):
        s,p,work=self.encounter()
        self.assertEqual([23],current_floor_food_work(p,s))
        self.assertIsNone(selective_descent(p,s,[]))
        self.assertEqual(Intent.EXPLORE,p.explore(s,[]).intent)
        self.assertIn('food_search_priority',p.planner.report)

    def test_carried_food_then_observed_food_precede_unknown_room_search(self):
        s,p,work=self.encounter();s['inventory'].append(item('ration of food','EAT'))
        self.assertEqual('EAT',selective_descent(p,s,[]).action.get('action'))
        s['inventory']=[];p.loot[23]={'name':'pasty','top_item':item('pasty','EAT')}
        self.assertEqual(Intent.LOOT,selective_descent(p,s,[]).intent)

    def test_current_floor_exhaustion_allows_safe_resource_descent(self):
        s,p,work=self.encounter();work.clear()
        self.assertFalse(current_floor_food_work(p,s))
        self.assertEqual(Intent.DESCEND,selective_descent(p,s,[]).intent)

    def test_starvation_does_not_force_hazard_or_recent_enemy_route(self):
        for mode in ('plant','threat','danger','enemy'):
            s,p,work=self.encounter();enemies=[]
            if mode=='plant':p.tiles[23]['plant']='firebloom'
            elif mode=='threat':p.recent_threats[23]={'name':'rat','cell':23}
            elif mode=='danger':s['danger_cells']=[24]
            else:enemies=[{'name':'rat','cell':23}]
            self.assertFalse(current_floor_food_work(p,s,enemies))

    def test_door_search_is_current_floor_work_too(self):
        s,p,work=self.encounter();work.clear();p.tiles[23]['terrain']=5
        original=p.exploration_report
        p.exploration_report=lambda state,paths:dict(original(state,paths),unopened_doors=[23])
        self.assertEqual([23],current_floor_food_work(p,s))
        self.assertIsNone(selective_descent(p,s,[]))

    def test_search_budget_is_not_a_waiver_for_known_unexplored_branches(self):
        s,p,work=self.encounter();p.searches=p.secret_search_steps=999
        self.assertIsNone(selective_descent(p,s,[]))
        with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'cell','cell':26},'descend',Intent.DESCEND)):
            with self.assertRaisesRegex(Finished,'current-floor food search is unfinished'):p.choose(s)


if __name__=='__main__':unittest.main()
