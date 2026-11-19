import unittest
from unittest.mock import patch

from tools.fly_tactics import escape,physical_attack_unsafe,defer_threatened_loot,attackers
from tools.policy_decision import Intent,TacticalBlocked
from tools.policy_runtime import Transaction,Context
from tools.policy_nodes import ordinary_combat
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


class FlyPressureTests(unittest.TestCase):
    def test_ordinary_special_escape_cannot_bypass_shared_pocket_rejection(self):
        s,p,foes=self.encounter()
        foes=[foes[0],foes[2]]
        for foe in foes:foe['description']='Non-magical attacks split this swarm.'
        s['objects']=foes
        with patch('tools.fly_tactics.onward_exit',return_value=False) as admission:
            self.assertIsNone(escape(p,s,foes))
            self.assertTrue(admission.called)

    def test_giant_choke_exception_does_not_use_ordinary_pocket_filter(self):
        s,p,foes=self.encounter(1)
        with patch('tools.fly_tactics.onward_exit',return_value=False) as admission:
            self.assertIsNotNone(escape(p,s,foes))
            admission.assert_not_called()

    def encounter(self,count=3):
        s=state()
        s.update(depth=4)
        s['hero'].update(cell=40,hp=11,max_hp=40,strength=10,buffs=[{'name':'starving'}])
        s['inventory'][0].update(status='0/5',curse_known=True,known_cursed=False)
        floors={y*9+x for y in (1,2,3) for x in range(2,7)}|{40,48,49,50,57,58,59}
        s['map']={'width':9,'height':9,'cells':[
            {'cell':c,'terrain':1 if c in floors else 4,'visible':True} for c in range(81)]}
        positions=[32,22,31][:count]
        foes=[{'name':'swarm of flies','cell':c,'health_bar':[12,43],
               'description':'Non-magical attacks split this swarm. _Giant Champion_ Giant champions have +1 attack range and cannot move through enclosed spaces.'}
              for c in positions]
        s['objects']=foes+[{'name':'Locked chest','cell':23}]
        s['keys']=[{'name':'golden key','depth':4,'quantity':1}]
        p=verified_policy();p.update(s)
        return s,p,foes

    def test_two_flies_can_retreat_through_one_exposed_step(self):
        s,p,foes=self.encounter(2)
        action=escape(p,s,foes)
        self.assertEqual(Intent.RETREAT,action.intent)
        report=p.planner.report['fly_pressure']
        self.assertEqual(2,report['visible_attackers_before'])
        self.assertEqual(1,report['visible_attackers_next'])
        self.assertEqual(0,report['endpoint_exposure'])
        self.assertLessEqual(len(report['route'])-1,3)

    def test_three_giants_count_range_two_and_reduce_to_two(self):
        s,p,foes=self.encounter()
        self.assertEqual(3,attackers(s,foes,40))
        action=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','three exposed flies'))
        self.assertEqual(Intent.RETREAT,action.intent)
        self.assertEqual(2,p.planner.report['fly_pressure']['visible_attackers_next'])

    def test_single_giant_at_known_choke_retreats_before_creating_second(self):
        s,p,foes=self.encounter(1)
        self.assertTrue(physical_attack_unsafe(p,s,foes[0]))
        action=escape(p,s,foes)
        self.assertEqual(Intent.RETREAT,action.intent)
        self.assertEqual(1,p.planner.report['fly_pressure']['exposure_next'])
        self.assertGreater(action.action['cell']//9,s['hero']['cell']//9)

    def test_melee_and_thrown_options_cannot_split_multiple_attackers(self):
        s,p,foes=self.encounter()
        s['inventory'].append({'id':'dart','name':'dart','actions':['THROW'],
            'description':'This thrown weapons deals 1-4 damage and requires 1 strength.'})
        self.assertFalse(p.attack_kind_allowed(s,foes[0],'melee'))
        self.assertFalse(p.attack_kind_allowed(s,foes[0],'thrown'))
        self.assertIsNone(p.best_attack(s,foes[0]))
        s['inventory'][0].update(status='1/5',actions=['ZAP','IMBUE'])
        self.assertEqual('ZAP',p.best_attack(s,foes[0]).action.get('action'))

    def test_ordinary_approach_cannot_bypass_blocked_physical_attack(self):
        s,p,foes=self.encounter()
        context=Context(p,s,enemies=foes,active=foes,engage=foes)
        with self.assertRaises(TacticalBlocked) as caught:ordinary_combat(context)
        self.assertEqual('attack-position',caught.exception.code)

    def test_planner_cannot_reintroduce_forbidden_melee_candidates(self):
        from tools.policy_geometry import distance,neighbors,line_clear
        s,p,foes=self.encounter()
        p.planner.positioning_steps=12
        self.assertIsNone(p.planner.tactical(p,s,foes,distance,neighbors,line_clear))

    def test_doorway_surprise_cannot_bypass_non_splitting_attack_guard(self):
        from tools.doorway_tactics import doorway_first
        from tools.policy_geometry import distance,neighbors,line_clear
        s,p,foes=self.encounter(1)
        s['hero']['hp']=40
        p.door_ambush=lambda *a,**k:p.cell(foes[0]['cell'],'doorway strike')
        with self.assertRaises(TacticalBlocked) as caught:
            doorway_first(p,s,foes,distance,neighbors,line_clear)
        self.assertEqual('fly-pressure',caught.exception.code)

    def test_two_ordinary_adjacent_flies_also_block_nonmagical_attacks(self):
        s,p,foes=self.encounter()
        foes=[foes[0],foes[2]]
        for foe in foes:foe['description']='Non-magical attacks split this swarm.'
        s['objects']=foes
        self.assertTrue(physical_attack_unsafe(p,s,foes[0]))
        self.assertEqual(Intent.RETREAT,escape(p,s,foes).intent)

    def test_no_legal_escape_never_forces_a_split_or_hazard_move(self):
        s,p,foes=self.encounter()
        for cell in (48,49,50):
            p.tiles[cell].update(terrain=18,trap='burning trap')
            s['map']['cells'][cell].update(terrain=18,trap='burning trap')
        self.assertIsNone(escape(p,s,foes))
        action=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','boxed flies'))
        self.assertEqual('wait',action.action['type'])

    def test_completed_sight_break_is_not_undone_by_loot_on_visibility_flicker(self):
        s,p,foes=self.encounter(2)
        action=escape(p,s,foes)
        self.assertIn(23,p.combat_deferred_loot)
        s['hero']['cell']=action.action['cell']
        s['objects']=[]
        continuation=escape(p,s,[])
        self.assertEqual(Intent.RETREAT,continuation.intent)
        s['hero']['cell']=continuation.action['cell']
        self.assertIsNone(escape(p,s,[]))
        self.assertIsNone(p.fly_escape_plan)
        self.assertFalse(p.exploration_loot_allowed(s,23,p.paths(s)))
        self.assertIn(23,p.loot)  # Deferral is not pickup.

    def test_new_resources_and_nearby_location_do_not_reopen_deferred_chest(self):
        s,p,foes=self.encounter()
        defer_threatened_loot(p,s,foes)
        s['hero']['hp']=40
        s['hero']['buffs']=[]
        s['inventory'][0]['status']='5/5'
        s['inventory'].append({'id':'food','name':'ration of food','actions':['EAT']})
        self.assertFalse(p.exploration_loot_allowed(s,23,p.paths(s)))
        self.assertEqual('deferred-unfinished',p.deferred_obligations[0]['status'])

    def test_food_and_keys_are_not_silently_deferred_as_optional_chests(self):
        s,p,foes=self.encounter()
        p.loot[24]={'name':'ration of food','top_item':{'name':'ration of food'}}
        p.loot[25]={'name':'golden key','top_item':{'name':'golden key'}}
        p.loot[30]={'name':'golden potion','top_item':{'name':'golden potion'}}
        defer_threatened_loot(p,s,foes)
        self.assertNotIn(24,p.combat_deferred_loot)
        self.assertNotIn(25,p.combat_deferred_loot)
        self.assertNotIn(30,p.combat_deferred_loot)

    def test_active_local_pickup_plan_is_cleared_without_claiming_completion(self):
        s,p,foes=self.encounter()
        p.room_loot_plan={'target':23,'region':{23,40},'steps':1}
        p.exploration_goal={'kind':'loot','cell':23}
        defer_threatened_loot(p,s,foes)
        self.assertIsNone(p.room_loot_plan)
        self.assertIsNone(p.exploration_goal)

    def test_existing_edge_budget_does_not_forbid_pressure_reducing_escape(self):
        s,p,foes=self.encounter(2)
        for cell in (48,49,50):p.soft_recovery_edges[(40,cell)]=10
        self.assertIsNotNone(escape(p,s,foes))

    def test_new_hazard_invalidates_pending_endpoint(self):
        s,p,foes=self.encounter()
        action=escape(p,s,foes)
        s['hero']['cell']=action.action['cell']
        p.tiles[p.fly_escape_plan['target']].update(terrain=18,trap='burning trap')
        self.assertIsNone(escape(p,s,foes))
        self.assertIsNone(p.fly_escape_plan)

    def test_rejected_escape_rolls_back_and_floor_reset_clears_navigation_state(self):
        s,p,foes=self.encounter()
        transaction=Transaction(p)
        escape(p,s,foes)
        transaction.rollback()
        self.assertIsNone(p.fly_escape_plan)
        self.assertFalse(p.combat_deferred_loot)
        escape(p,s,foes)
        p.memory.reset_floor(40)
        self.assertFalse(p.combat_deferred_loot)
        self.assertIsNone(p.fly_escape_plan)
        self.assertTrue(p.deferred_obligations)  # Run-wide unfinished history remains.

    def test_isolated_ordinary_fly_keeps_existing_attack_policy(self):
        s,p,foes=self.encounter(1)
        foes[0]['description']='Non-magical attacks split this swarm.'
        self.assertFalse(physical_attack_unsafe(p,s,foes[0]))
        self.assertIsNone(escape(p,s,foes))

    def test_single_ordinary_fly_does_not_split_when_uncursed_magic_is_available(self):
        s,p,foes=self.encounter(1)
        foes[0]['description']='Non-magical attacks split this swarm.'
        s['inventory'][0].update(status='1/5',actions=['ZAP','IMBUE'])
        self.assertTrue(physical_attack_unsafe(p,s,foes[0]))
        self.assertEqual('ZAP',p.best_attack(s,foes[0]).action.get('action'))

    def test_known_uncursed_unknown_charge_wand_can_replace_surprise_melee(self):
        from tools.doorway_tactics import doorway_first
        from tools.policy_geometry import distance,neighbors,line_clear
        s,p,foes=self.encounter(1);s['hero']['hp']=40
        foes[0]['description']='Non-magical attacks split this swarm.'
        s['inventory'].append({'name':'wand of magic missile','id':'extra','status':None,
            'description':'Each bolt deals _2-8 damage_.','curse_known':True,'known_cursed':False,'actions':['ZAP']})
        p.door_ambush=lambda *a,**k:p.cell(foes[0]['cell'],'doorway strike')
        action=doorway_first(p,s,foes,distance,neighbors,line_clear)
        self.assertEqual('ZAP',action.action.get('action'))
        self.assertEqual('extra',action.action['id'])

    def test_unknown_charge_cooldown_does_not_invent_available_magic(self):
        s,p,foes=self.encounter(1);foes[0]['description']='Non-magical attacks split this swarm.'
        s['inventory'].append({'name':'wand of magic missile','id':'extra','status':None,
            'description':'Each bolt deals _2-8 damage_.','curse_known':True,'known_cursed':False,'actions':['ZAP']})
        p.unknown_magic_cooldowns['wand of magic missile']=1
        self.assertFalse(physical_attack_unsafe(p,s,foes[0]))

    def test_danger_root_and_boss_do_not_get_a_blind_route_override(self):
        s,p,foes=self.encounter()
        s['danger_cells']=[40]
        self.assertIsNone(escape(p,s,foes))
        s['danger_cells']=[]
        s['hero']['buffs']=[{'name':'rooted'}]
        self.assertIsNone(escape(p,s,foes))
        s['hero']['buffs']=[]
        self.assertIsNone(escape(p,s,foes+[{'name':'goo','cell':30}]))


if __name__=='__main__':unittest.main()
