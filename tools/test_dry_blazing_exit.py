import unittest
from tools.challenge_combat import exposure
from tools.policy_decision import Finished,Intent
from tools.policy_geometry import distance,neighbors,line_clear
from tools.policy_runtime import Transaction
from tools.combat_positioning import rinse_ooze
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


class DryBlazingExitTests(unittest.TestCase):
    def encounter(self):
        s=state();s['hero'].update(cell=40,hp=18,max_hp=20,buffs=[])
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':4 if c%9 in {0,8} or c//9 in {0,8} else 1,'visible':True} for c in range(81)]}
        s['objects']=[{'name':'marsupial rat','cell':31,'description':'_Blazing Champion_'}]
        p=verified_policy();p.update(s)
        return s,p

    def test_healthy_dry_hero_disengages_before_adjacent_zap(self):
        s,p=self.encounter();a=p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertEqual(Intent.RETREAT,a.intent)
        self.assertIn('dry blazing contact',a.reason)
        self.assertEqual(0,exposure(p,s,s['objects'],a.action['cell'],distance,line_clear)['exposure'])

    def test_existing_water_staging_still_has_priority(self):
        s,p=self.encounter();p.tiles[49]['terrain']=29
        a=p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertEqual(49,a.action['cell'])
        self.assertIn('stage water',a.reason)

    def test_hazard_steps_do_not_become_fire_escape(self):
        s,p=self.encounter()
        for c in neighbors(40,9,9):p.tiles[c]['plant']='firebloom'
        p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertNotIn('dry_blazing_exit',p.planner.report)

    def test_burning_is_left_to_existing_extinguishing_controller(self):
        s,p=self.encounter();s['hero']['buffs']=[{'name':'burning'}]
        p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertNotIn('dry_blazing_exit',p.planner.report)

    def test_new_branch_keeps_withdrawal_budget_and_rolls_back(self):
        s,p=self.encounter();tx=Transaction(p)
        p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear);tx.rollback()
        self.assertEqual(0,p.challenge_combat.withdrawals)
        p.challenge_combat.withdrawals=16
        p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertNotIn('dry_blazing_exit',p.planner.report)

    def test_critical_burning_hard_gate_is_unchanged(self):
        s,p=self.encounter();s['hero'].update(hp=1,buffs=[{'name':'burning'}]);s['objects']=[]
        p.tiles[58]['terrain']=29
        with self.assertRaises(Finished) as caught:rinse_ooze(p,s,[],distance,neighbors)
        self.assertIn('Critical burning',caught.exception.reason)

    def test_visibly_weakened_death_spacing_keeps_existing_controller(self):
        s,p=self.encounter();s['objects'][0]['health_bar']=[1,10]
        p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertNotIn('dry_blazing_exit',p.planner.report)
