import unittest

from tools.challenge_combat import exposure
from tools.doorway_tactics import doorway_first,hold_doorway
from tools.fly_tactics import escape,physical_attack_unsafe
from tools.policy_decision import Intent,TacticalBlocked
from tools.policy_geometry import distance,neighbors,line_clear
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


class ProjectingFlyTests(unittest.TestCase):
    def encounter(self):
        s=state()
        s['hero'].update(cell=97,hp=9,max_hp=30,buffs=[])
        s['map']={'width':15,'height':15,'cells':[
            {'cell':c,'terrain':4 if c%15 in {0,14} or c//15 in {0,14} else 1,'visible':True}
            for c in range(225)]}
        es=[{'name':'swarm of flies','cell':127,'description':'_Projecting Champion_ +3 attack range.'}]
        s['objects']=es
        p=verified_policy();p.update(s)
        return s,p,es

    def test_single_projecting_fly_blocks_melee_and_thrown_before_split(self):
        s,p,es=self.encounter()
        self.assertTrue(physical_attack_unsafe(p,s,es[0]))
        self.assertFalse(p.attack_kind_allowed(s,es[0],'melee'))
        self.assertFalse(p.attack_kind_allowed(s,es[0],'thrown'))
        self.assertTrue(p.attack_kind_allowed(s,es[0],'magic'))

    def test_three_step_exit_can_start_with_equal_range_four_exposure(self):
        s,p,es=self.encounter()
        a=escape(p,s,es)
        self.assertEqual(Intent.RETREAT,a.intent)
        report=p.planner.report['fly_pressure']
        self.assertEqual(1,report['visible_attackers_next'])
        self.assertEqual(0,report['endpoint_exposure'])
        self.assertEqual(4,len(report['route']))
        self.assertGreater(distance(a.action['cell'],127,15),distance(97,127,15))

    def test_recovery_repositions_when_no_clear_shot_instead_of_exposed_wait(self):
        s,p,es=self.encounter()
        p.shot_clear=lambda *a:False
        a=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','no shot'))
        self.assertEqual(Intent.RETREAT,a.intent)
        self.assertNotEqual('wait',a.action['type'])

    def test_doorway_does_not_reintroduce_splitting_surprise_strike(self):
        s,p,es=self.encounter()
        s['hero'].update(cell=112,hp=25)
        p.door_ambush=lambda *a,**k:p.cell(127,'doorway surprise strike')
        a=doorway_first(p,s,es,distance,neighbors,line_clear)
        self.assertEqual('ZAP',a.action.get('action'))

    def test_hold_at_door_is_invalidated_by_extended_reach(self):
        s,p,es=self.encounter()
        p.doorway_hold={'depth':s['depth'],'door':127,'hide':97,'inputs':0,'quiet':0,'waits':0}
        self.assertIsNone(hold_doorway(p,s,es,distance,neighbors,line_clear))
        self.assertIsNone(p.doorway_hold)

    def test_underlying_ambush_wait_also_checks_extended_reach(self):
        s,p,es=self.encounter()
        p.ambush_plan={'kind':'doorway','door':112,'hide':97,'waits':0}
        self.assertIsNone(p.door_ambush(s,es,es,kind='doorway'))
        self.assertIsNone(p.ambush_plan)

    def test_missing_bounded_endpoint_does_not_allow_blind_distance_step(self):
        s,p,es=self.encounter()
        for c,t in p.tiles.items():
            if c not in {97,82,67,127}:t['terrain']=4
        self.assertIsNone(escape(p,s,es))

    def test_hazard_on_all_exits_does_not_get_overridden(self):
        s,p,es=self.encounter()
        for c in neighbors(97,15,15):p.tiles[c]['plant']='firebloom'
        self.assertIsNone(escape(p,s,es))

    def test_remembered_projection_only_constrains_movement_not_attack(self):
        s,p,es=self.encounter()
        a=escape(p,s,es)
        s['hero']['cell']=a.action['cell']
        s['objects']=[]
        a=escape(p,s,[])
        self.assertEqual(Intent.RETREAT,a.intent)
        self.assertNotEqual(127,a.action['cell'])


if __name__=='__main__':unittest.main()
