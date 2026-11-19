import unittest

from tools.challenge_combat import mixed_water_escape,exposure
from tools.policy_geometry import distance,neighbors,line_clear
from tools.policy_decision import Intent,TacticalBlocked
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


class MixedWaterEscapeTests(unittest.TestCase):
    def encounter(self):
        s=state()
        s['hero'].update(cell=40,hp=12,max_hp=20,buffs=[])
        s['map']={'width':9,'height':9,'cells':[
            {'cell':c,'terrain':4 if c%9 in {0,8} or c//9 in {0,8} else 29 if c==40 else 1,
             'visible':True} for c in range(81)]}
        es=[{'name':'marsupial rat','cell':39,'description':'_Blazing Champion_'},
            {'name':'marsupial rat','cell':31},
            {'name':'sewer snake','cell':22}]
        s['objects']=es
        p=verified_policy();p.update(s)
        return s,p,es

    def escape(self,p,s,es,remembered=()):
        return mixed_water_escape(p,s,es,distance,neighbors,line_clear,remembered)

    def test_escape_precedes_charged_water_attack_and_snake_suppression(self):
        s,p,es=self.encounter()
        action=p.challenge_combat.choose(p,s,es,distance,neighbors,line_clear)
        self.assertEqual(Intent.RETREAT,action.intent)
        self.assertIn('onward exits',action.reason)
        self.assertEqual(0,exposure(p,s,es,action.action['cell'],distance,line_clear)['exposure'])

    def water_choice(self):
        s,p,es=self.encounter()
        es=[{'name':'marsupial rat','cell':30,'description':'_Blazing Champion_'},
            {'name':'marsupial rat','cell':31}]
        s['objects']=es;p.tiles[48]['terrain']=29
        p.tiles[47]['terrain']=p.tiles[56]['terrain']=4
        return s,p,es

    def test_admitted_unexposed_water_precedes_dry_ground_with_extra_exits(self):
        s,p,es=self.water_choice();a=self.escape(p,s,es)
        self.assertEqual(48,a.action['cell'])
        self.assertTrue(p.planner.report['mixed_water_escape']['stays_in_water'])
        self.assertEqual(0,exposure(p,s,es,48,distance,line_clear)['exposure'])

    def test_hazardous_water_does_not_override_safe_dry_escape(self):
        s,p,es=self.water_choice();p.tiles[48]['plant']='firebloom'
        a=self.escape(p,s,es)
        self.assertIsNotNone(a);self.assertNotEqual(48,a.action['cell'])
        self.assertFalse(p.planner.report['mixed_water_escape']['stays_in_water'])

    def test_water_still_requires_two_clear_onward_squares(self):
        s,p,es=self.water_choice()
        for c in (38,49,58):p.tiles[c]['terrain']=4
        a=self.escape(p,s,es)
        self.assertIsNotNone(a);self.assertNotEqual(48,a.action['cell'])

    def test_critical_recovery_does_not_reintroduce_water_pinning(self):
        s,p,es=self.encounter()
        s['hero']['hp']=6
        action=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','crowded water'))
        self.assertEqual(Intent.RETREAT,action.intent)
        self.assertIn('mixed_water_escape',p.planner.report)

    def test_known_cul_de_sac_is_not_an_escape(self):
        s,p,es=self.encounter()
        for c,t in p.tiles.items():
            if c not in {40,39,31,22,50}:t['terrain']=4
        self.assertIsNone(self.escape(p,s,es))

    def test_revealed_hazards_and_plants_are_not_crossed(self):
        s,p,es=self.encounter()
        for c in neighbors(40,9,9):
            if c not in {39,31}:p.tiles[c]['plant']='firebloom'
        self.assertIsNone(self.escape(p,s,es))

    def test_one_clear_onward_square_and_exposed_second_is_not_open_ground(self):
        s,p,es=self.encounter()
        for c,t in p.tiles.items():
            if c not in {40,39,31,22,50,59,41}:t['terrain']=4
        # 50 is unexposed, but only 59 remains unexposed beyond it; 41 is
        # within rat reach. This models the narrowing northern alcove.
        self.assertIsNone(self.escape(p,s,es))

    def test_burning_or_protected_return_cannot_be_overridden(self):
        s,p,es=self.encounter()
        for buff in ('burning','rooted','paralysed','vertigo','poisoned'):
            s['hero']['buffs']=[{'name':buff}]
            self.assertIsNone(self.escape(p,s,es),buff)
        s['hero']['buffs']=[]
        p.room_journey=object()
        self.assertIsNone(self.escape(p,s,es))

    def test_single_blazing_enemy_keeps_existing_water_policy(self):
        s,p,es=self.encounter()
        self.assertIsNone(self.escape(p,s,es[:1]))

    def test_dry_ground_and_boss_warnings_do_not_activate_override(self):
        s,p,es=self.encounter()
        p.tiles[40]['terrain']=1
        self.assertIsNone(self.escape(p,s,es))
        p.tiles[40]['terrain']=29
        s['danger_cells']=[40]
        self.assertIsNone(self.escape(p,s,es))
        s['danger_cells']=[]
        s['boss_health_text']='Boss'
        self.assertIsNone(self.escape(p,s,es))

    def test_rejected_decision_rolls_back_report_and_ambush_changes(self):
        s,p,es=self.encounter()
        p.ambush_plan={'kind':'swarm'}
        tx=Transaction(p)
        self.assertIsNotNone(self.escape(p,s,es))
        self.assertIsNone(p.ambush_plan)
        tx.rollback()
        self.assertEqual({'kind':'swarm'},p.ambush_plan)
        self.assertNotIn('mixed_water_escape',p.planner.report)


if __name__=='__main__':unittest.main()
