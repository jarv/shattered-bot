import copy
import unittest

from tools.pursuit_budget import due, observe_accepted, reassess
from tools.policy_decision import Decision, Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_systems import ready


class PursuitBudgetTests(unittest.TestCase):
    def scenario(self):
        s,p=ready()
        s['hero']['hp']=6
        s['inventory'][0]['curse_known']=True
        p.pursuit_retreat_moves=4
        snake={'name':'sewer snake','cell':25,'description':'_Growing Champion_'}
        s['objects']=[snake]
        return s,p,[snake]

    def test_known_charge_intervention_before_more_growing_snake_retreat(self):
        s,p,enemies=self.scenario()
        action=reassess(p,s,enemies)
        self.assertEqual('ZAP',action.action['action'])
        self.assertEqual(25,p.target)
        self.assertEqual(1,p.pursuit_interventions)
        self.assertFalse(due(p))

    def test_only_actual_accepted_retreat_movements_count(self):
        s,p,enemies=self.scenario()
        p.pursuit_retreat_moves=0
        action=Decision({'type':'cell','cell':23},'withdraw',Intent.RETREAT)
        observe_accepted(p,s,action,s)
        self.assertEqual(0,p.pursuit_retreat_moves)
        after=copy.deepcopy(s)
        after['hero']['cell']=23
        observe_accepted(p,s,action,after)
        self.assertEqual(1,p.pursuit_retreat_moves)

    def test_visibility_flicker_and_free_inspection_do_not_reset_budget(self):
        s,p,enemies=self.scenario()
        quiet=copy.deepcopy(s)
        quiet['objects']=[]
        inspect=Decision({'type':'inspect','cell':25},'inspect')
        for _ in range(5):observe_accepted(p,quiet,inspect,quiet)
        self.assertEqual(4,p.pursuit_retreat_moves)
        after=copy.deepcopy(quiet)
        after['hero']['cell']=23
        observe_accepted(p,quiet,Decision({'type':'cell','cell':23},'move',Intent.EXPLORE),after)
        self.assertEqual(4,p.pursuit_retreat_moves)

    def test_three_quiet_moves_reset_without_claiming_enemy_defeat(self):
        s,p,enemies=self.scenario()
        s['objects']=[]
        p.pursuit_interventions=1
        action=Decision({'type':'wait'},'observe')
        for _ in range(3):observe_accepted(p,s,action,s)
        self.assertEqual(0,p.pursuit_retreat_moves)
        self.assertEqual(0,p.pursuit_interventions)

    def test_two_interventions_maximum_with_four_more_retreat_moves_between(self):
        s,p,enemies=self.scenario()
        self.assertIsNotNone(reassess(p,s,enemies))
        self.assertIsNone(reassess(p,s,enemies))
        p.pursuit_retreat_moves+=4
        self.assertIsNotNone(reassess(p,s,enemies))
        p.pursuit_retreat_moves+=4
        self.assertIsNone(reassess(p,s,enemies))

    def test_real_door_sight_break_retains_priority(self):
        s,p,enemies=self.scenario()
        p.tiles[24]['terrain']=6
        self.assertIsNone(reassess(p,s,enemies))
        self.assertEqual(0,p.pursuit_interventions)

    def test_danger_invisibility_and_damage_over_time_retain_safety(self):
        for buff in ('invisible','burning','poison','paralyzed'):
            s,p,enemies=self.scenario()
            s['hero']['buffs']=[{'name':buff}]
            self.assertIsNone(reassess(p,s,enemies))
        s,p,enemies=self.scenario()
        s['danger_cells']=[24]
        self.assertIsNone(reassess(p,s,enemies))

    def test_no_known_charge_no_shot(self):
        for status in ('0/4',None):
            s,p,enemies=self.scenario()
            s['inventory'][0]['status']=status
            self.assertIsNone(reassess(p,s,enemies))
        s,p,enemies=self.scenario()
        s['inventory'][0]['known_cursed']=True
        self.assertIsNone(reassess(p,s,enemies))

    def test_no_memory_only_target_or_passive_mimic_intervention(self):
        s,p,enemies=self.scenario()
        self.assertIsNone(reassess(p,s,[]))
        enemies[0]['name']='crystal mimic'
        self.assertIsNone(reassess(p,s,enemies))

    def test_bosses_antimagic_and_dry_blazing_remain_excluded(self):
        for name,description in [('goo',''),('sewer snake','_Antimagic Champion_'),
                                  ('marsupial rat','_Blazing Champion_')]:
            s,p,enemies=self.scenario()
            enemies[0].update(name=name,description=description)
            self.assertIsNone(reassess(p,s,enemies))

    def test_healthy_ordinary_pursuit_does_not_force_magic(self):
        s,p,enemies=self.scenario()
        s['hero']['hp']=20
        enemies[0]['description']='ordinary rat'
        self.assertIsNone(reassess(p,s,enemies))

    def test_immediate_blazing_from_water_precedes_distant_weakened_rat(self):
        s,p,_=self.scenario();s['hero']['hp']=10;p.tiles[24]['terrain']=29
        enemies=[{'name':'marsupial rat','cell':25,'description':'_Blazing Champion_'},
                 {'name':'marsupial rat','cell':10,'health_bar':[1,43]}]
        s['objects']=enemies
        action=reassess(p,s,enemies)
        self.assertEqual('ZAP',action.action.get('action'))
        self.assertEqual(25,p.target)
        self.assertTrue(p.planner.report['pursuit_reassessment']['protected_blazing_priority'])

    def test_noncontact_blazing_does_not_override_visible_weak_target(self):
        s,p,_=self.scenario();s['hero']['hp']=10;p.tiles[24]['terrain']=29
        enemies=[{'name':'marsupial rat','cell':26,'description':'_Blazing Champion_'},
                 {'name':'marsupial rat','cell':10,'health_bar':[1,43]}]
        s['objects']=enemies
        self.assertIsNotNone(reassess(p,s,enemies))
        self.assertEqual(10,p.target)

    def test_water_target_priority_does_not_admit_multi_attacker_trade(self):
        s,p,_=self.scenario();s['hero']['hp']=10;p.tiles[24]['terrain']=29
        enemies=[{'name':'marsupial rat','cell':25,'description':'_Blazing Champion_'},
                 {'name':'marsupial rat','cell':23}]
        s['objects']=enemies
        self.assertIsNone(reassess(p,s,enemies))

    def test_rejected_intent_rolls_back_and_floor_reset_clears_state(self):
        s,p,enemies=self.scenario()
        transaction=Transaction(p)
        reassess(p,s,enemies)
        transaction.rollback()
        self.assertEqual(0,p.pursuit_interventions)
        self.assertTrue(due(p))
        p.memory.reset_floor(24)
        self.assertEqual(0,p.pursuit_retreat_moves)

    def test_challenge_preparation_reassesses_before_another_doorway_hold(self):
        from unittest.mock import patch
        s,p,enemies=self.scenario()
        with patch('tools.mage_policy.hold_doorway',side_effect=AssertionError('intervene first')):
            action=p.challenge_preparation(s,enemies)
        self.assertEqual('ZAP',action.action['action'])


if __name__=='__main__':unittest.main()
