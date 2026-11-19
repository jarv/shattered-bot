import unittest
from tools.test_challenge_systems import ready, item
from tools.exploration_budget import pressure, selective_descent
from tools.policy_decision import Intent


class ExplorationBudgetTests(unittest.TestCase):
    def test_starving_prioritizes_distant_food_without_known_exit(self):
        from tools.exploration_budget import starving_food
        s,p=self.setup_exit()
        s['hero']['buffs']=[{'name':'starving'}]
        p.tiles[26]['terrain']=1
        paths={24:None,23:24,22:23,21:22,20:21,19:20,18:19,17:18}
        p.paths=lambda *a,**k:paths
        p.loot[17]={'name':'ration of food','top_item':item('ration of food','EAT')}
        self.assertTrue(p.exploration_loot_allowed(s,17,paths))
        action=starving_food(p,s,[])
        self.assertEqual(Intent.LOOT,action.intent)
        self.assertEqual(23,action.action['cell'])

    def test_starving_eats_carried_food_before_optional_equipment(self):
        s,p=self.setup_exit()
        s['hero']['buffs']=[{'name':'starving'}]
        s['inventory'] += [item('ration of food','EAT'),item('agate ring','EQUIP')]
        action=p.challenge_preparation(s,[])
        self.assertEqual('EAT',action.action['action'])

    def test_starving_food_does_not_bypass_recent_threats_or_sales(self):
        from tools.exploration_budget import starving_food,food_loot
        s,p=self.setup_exit()
        s['hero']['buffs']=[{'name':'starving'}]
        p.loot[23]={'name':'ration of food','top_item':item('ration of food','EAT')}
        p.recent_threats[22]={'name':'gnoll scout','cell':22}
        self.assertIsNone(starving_food(p,s,[]))
        self.assertFalse(food_loot(dict(p.loot[23],for_sale=True)))

    def test_natural_healing_is_disabled_while_starving_even_with_funded_budget(self):
        from tools.policy_nodes import preparation_and_recovery
        from tools.policy_runtime import Context
        s,p=self.setup_exit()
        s['hero']['buffs']=[{'name':'starving'}]
        p.food_recovery_until=90
        self.assertIsNone(preparation_and_recovery(Context(p,s)))

    def setup_exit(self):
        s,p=ready()
        s['inventory']=[]
        s['hero'].update(hp=8,max_hp=20,buffs=[{'name':'hungry'}])
        p.tiles[26]['terrain']=8
        return s,p

    def test_healthy_exploration_is_not_skipped(self):
        s,p=self.setup_exit()
        s['hero'].update(hp=20,buffs=[])
        self.assertIsNone(selective_descent(p,s,[]))

    def test_strict_coverage_retains_distant_loot_despite_resource_pressure(self):
        s,p=self.setup_exit()
        p.tiles[26]['terrain']=1
        paths={24:None,23:24,22:23,21:22,20:21,19:20,18:19,17:18}
        p.loot[17]={'name':'charcoal potion','top_item':item('charcoal potion','DRINK')}
        self.assertTrue(p.exploration_loot_allowed(s,17,paths))
        self.assertFalse(p.deferred_obligations)
        self.assertTrue(p.exploration_loot_allowed(s,23,paths))
        s['inventory'].append(item('ration of food','EAT'))
        self.assertTrue(p.exploration_loot_allowed(s,17,paths))

    def test_deferred_floor_transition_is_not_reported_as_cleared(self):
        from tools.policy_decision import Decision
        s,p=self.setup_exit()
        p.defer_obligations(s,[{'kind':'optional exploration','cell':26}],'hungry and wounded')
        p.last_decision=Decision({'type':'cell','cell':26},'resource-aware descent',Intent.DESCEND)
        s['depth']+=1
        p.update(s)
        self.assertNotIn(1,p.cleared_floors)
        self.assertEqual('deferred-unfinished',p.deferred_obligations[0]['status'])

    def test_resource_descent_with_no_remaining_work_does_not_invent_deferral(self):
        from unittest.mock import patch
        from tools.survival_policy import SurvivalPolicy
        s,p=self.setup_exit();action=selective_descent(p,s,[])
        with patch.object(SurvivalPolicy,'choose',return_value=action):p.choose(s)
        self.assertFalse(p.deferred_obligations)
        self.assertTrue(p.descent_counts_as_clear())

    def test_resource_descent_retains_real_unopened_door_work(self):
        from unittest.mock import patch
        from tools.survival_policy import SurvivalPolicy
        s,p=self.setup_exit();p.tiles[23]['terrain']=5;action=selective_descent(p,s,[])
        self.assertEqual(1,p.planner.report['exploration_budget']['doors_deferred'])
        with patch.object(SurvivalPolicy,'choose',return_value=action):p.choose(s)
        self.assertEqual(1,p.deferred_obligations[0]['obligation']['doors'])
        self.assertFalse(p.descent_counts_as_clear())

    def test_multiple_deferral_categories_keep_all_nonfatal_log_records(self):
        s,p=self.setup_exit()
        p.defer_obligations(s,[{'kind':'unresolved room','cell':23}],'no supplies')
        p.defer_obligations(s,[{'kind':'optional exploration','cell':26}],'resource pressure')
        self.assertEqual(2,len(p.planner.report['nonfatal_obligations']))

    def test_wounded_hungry_hero_descends_and_records_unfinished_frontiers(self):
        s,p=self.setup_exit()
        a=selective_descent(p,s,[])
        self.assertEqual(Intent.DESCEND,a.intent)
        self.assertIn('exploration_budget',p.planner.report)
        self.assertEqual(0,p.search_limit(s,6,True))
        self.assertEqual(0,p.sweep_limit(s))

    def test_nearby_concrete_supplies_come_before_descent(self):
        s,p=self.setup_exit()
        p.loot[23]={'name':'ration of food','top_item':item('ration of food','EAT')}
        # The strict room/exploration planner, not selective early descent, owns
        # this pickup. Known ordinary loot cannot be waived by resource pressure.
        self.assertIsNone(selective_descent(p,s,[]))

    def test_food_reserve_prevents_hunger_only_rush(self):
        s,p=self.setup_exit()
        s['inventory'].append(item('ration of food','EAT'))
        self.assertIsNone(pressure(p,s))

    def test_active_enemy_hazard_and_recent_threat_do_not_trigger_rush(self):
        s,p=self.setup_exit()
        self.assertIsNone(selective_descent(p,s,[{'name':'gnoll scout','cell':25}]))
        s['danger_cells']=[25]
        self.assertIsNone(selective_descent(p,s,[]))
        s['danger_cells']=[]
        p.recent_threats[25]={'name':'gnoll scout','cell':25}
        self.assertIsNone(selective_descent(p,s,[]))

    def test_no_exit_and_damage_over_time_do_not_override_recovery(self):
        s,p=self.setup_exit()
        p.tiles[26]['terrain']=1
        self.assertIsNone(selective_descent(p,s,[]))
        p.tiles[26]['terrain']=8
        s['hero']['buffs'].append({'name':'burning'})
        self.assertIsNone(selective_descent(p,s,[]))

    def test_sale_or_suspicious_loot_is_not_a_supply_detour(self):
        from tools.exploration_budget import useful_loot
        self.assertFalse(useful_loot({'name':'wand','for_sale':True,'top_item':item('wand','ZAP')}))

    def test_transfusion_controls_adjacent_crab_before_nearly_dead_distant_champion(self):
        from tools.wand_tactics import choose_transfusion
        from tools.policy_geometry import distance
        s,p=self.setup_exit()
        s['inventory']=[item('wand of transfusion','ZAP',curse_known=True,known_cursed=False)]
        p.charged_magic=lambda s:False
        p.shot_clear=lambda *a:True
        p.target_allowed=lambda *a:True
        enemies=[{'name':'swarm of flies','cell':10,'health_bar':[2,43],
                  'description':'A projecting champion'}, {'name':'sewer crab','cell':25}]
        inspected=[]
        p.inspect_enemy=lambda e:inspected.append(e['name']) or p.decision({'type':'inspect','cell':e['cell']},'inspect')
        choose_transfusion(p,s,enemies,distance)
        self.assertEqual(['sewer crab'],inspected)


if __name__=='__main__':unittest.main()
