import copy
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_consumable_tactics import potion
from tools.test_wooden_barrier import wood_room
from tools.test_multi_enemy_and_fly_feedback import choke
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Transaction,Context
from tools.wooden_barrier import known_burn,recover
from tools.ghost_quest import prepare_ghost,visit_ghost
from tools.room_completion import obligations
from tools import policy_nodes
from tools import multi_enemy_tactics as multi
from tools.policy_decision import Finished


class EmergencyRetreatPriorityTests(unittest.TestCase):
    def test_known_healing_preempts_multi_attacker_retreat(self):
        s,p,foes=choke();s['hero']['hp']=5
        s['inventory'].append(potion('potion of healing'))
        a=p.choose(s)
        self.assertEqual('emergency-healing',a.controller)
        self.assertEqual('DRINK',a.action['action'])

    def test_critical_admitted_consumable_is_not_starved_by_retreat(self):
        s,p,foes=choke();s['hero']['hp']=5
        admitted=p.decision({'type':'wait'},'synthetic admitted emergency item')
        with patch.object(policy_nodes,'emergency_consumable',return_value=admitted):
            a=p.choose(s)
        self.assertEqual('multi-threat-emergency-item',a.controller)

    def test_healthy_multi_attacker_still_retreats_first(self):
        s,p,foes=choke()
        self.assertEqual('multi-threat-retreat',p.choose(s).controller)

    def test_exhausted_multi_pressure_budget_still_allows_immediate_reduction(self):
        s,p,foes=choke();p.multi_retreat_streak=3
        a=multi.choose(p,s,foes)
        self.assertIsNotNone(a)
        self.assertLessEqual(p.planner.report['multi_enemy_retreat']['next_approach_slots'],1)


class KnownBarricadeTests(unittest.TestCase):
    def scene(self):
        s,p=wood_room();s['hero']['cell']=38;s['inventory'][-1]=potion('potion of liquid flame')
        # Only the far side of the barricade is unseen, not the throwing bank.
        for t in s['map']['cells']:
            if t['cell'] in {33,42,51}:t.update(terrain=None,visible=False,observed=False)
        p.update(s)
        for c in (33,42,51):p.tiles.pop(c,None)
        return s,p

    def test_known_flame_throws_without_inventing_far_side_terrain(self):
        s,p=self.scene();a=known_burn(p,s,[])
        self.assertEqual('THROW',a.action['action']);self.assertEqual(41,p.target)
        self.assertEqual('verify-wood',p.wood_burn_plan['phase'])
        self.assertNotIn(42,p.tiles)

    def test_known_loot_or_ally_near_impact_prevents_throw(self):
        for case in ('loot','ally'):
            s,p=self.scene()
            if case=='loot':p.loot[42]={'name':'scroll'}
            else:s['objects']=[{'name':'mirror image','cell':42}]
            self.assertIsNone(known_burn(p,s,[]),case)

    def test_burn_requires_actual_clearance_and_bounded_observation(self):
        s,p=self.scene();known_burn(p,s,[])
        self.assertEqual('wait',recover(p,s,[]).action['type'])
        p.tiles[41].update(terrain=20,effects=['A fire is raging here.'])
        self.assertEqual('wait',recover(p,s,[]).action['type'])
        p.tiles[41]['effects']=[]
        self.assertIsNone(recover(p,s,[]));self.assertIsNone(p.wood_burn_plan)
        self.assertFalse(p.loot_collection_receipts)

    def test_rejected_throw_rolls_back_plan_and_attempt(self):
        s,p=self.scene();tx=Transaction(p,p.planner);known_burn(p,s,[]);tx.rollback()
        self.assertIsNone(p.wood_burn_plan);self.assertNotIn((s['depth'],'burn',41),p.room_attempts)


class SleepingAndGhostTests(unittest.TestCase):
    def test_sleeping_enemy_sighting_does_not_drive_adjacent_patrol(self):
        s,p=arena();s['objects']=[{'name':'sewer crab','cell':41,'sleeping':True}];p.update(s)
        report=p.exploration_report(s,p.paths(s))
        report.update(unexplored_frontiers=[],unopened_doors=[],remaining_enemy_sightings=s['objects'])
        with patch.object(p,'exploration_report',return_value=report):
            original=p.toward
            def toward(*args,**kwargs):
                self.assertNotIn('clear ordinary enemy sighting',args[2])
                return original(*args,**kwargs)
            with patch.object(p,'toward',side_effect=toward):
                try:p.explore(s,[])
                except Finished:pass
        self.assertTrue(p.enemy_sightings[41]['sleeping'])

    def ghost(self):
        s,p=arena();s['depth']=3;p.update(s)
        p.ghost_quest.update(last_depth=3,last_cell=42)
        s['inventory'][0]['status']='2/6'
        s['hero']['hp']=int(s['hero']['max_hp']*.75)
        return s,p

    def test_ghost_safe_readiness_wait_is_bounded_without_potion_spend(self):
        s,p=self.ghost()
        for _ in range(24):self.assertEqual('wait',prepare_ghost(p,s,[]).action['type'])
        self.assertIsNone(prepare_ghost(p,s,[]))
        self.assertTrue(any(o['kind']=='unstarted observed Sad Ghost quest' for o in obligations(p,s)))

    def test_no_ghost_preparation_while_starving_under_threat_or_sleeping_foe(self):
        for case in ('starving','recent','sleeping','escape'):
            s,p=self.ghost()
            if case=='starving':s['hero']['buffs']=[{'name':'starving'}]
            if case=='recent':p.recent_threats[50]={'name':'gnoll scout'}
            if case=='sleeping':s['objects']=[{'name':'sewer crab','cell':41,'sleeping':True}]
            if case=='escape':p.escape_commitment={'target':20}
            self.assertIsNone(prepare_ghost(p,s,[]),case)

    def test_ready_hero_can_return_to_last_observed_ghost_area_but_not_talk_to_memory(self):
        s,p=self.ghost();s['hero']['hp']=s['hero']['max_hp'];s['inventory'][0]['status']='3/6'
        self.assertIsNone(prepare_ghost(p,s,[]))
        a=visit_ghost(p,s,[],distance,neighbors)
        self.assertIn('last observed Sad Ghost',a.reason)
        self.assertNotEqual(42,a.action['cell'])


if __name__=='__main__':unittest.main()
