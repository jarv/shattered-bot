import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.loot_route import shortest_tour,nearest_tour,TourTooLarge
from tools.room_loot import before_room_exit,plan_tour
from tools.policy_decision import Intent,TacticalBlocked,Finished
from tools.policy_geometry import distance,neighbors,line_clear
from tools.tactical_recovery import recover


class LargeRoomLootTests(unittest.TestCase):
    def test_exact_limit_has_explicit_nonoptimal_progress_fallback(self):
        s,p=arena();targets=list(range(10,17))+list(range(19,26))+[28,29]
        region={c for c in p.tiles if p.walkable(c)}
        with self.assertRaises(TourTooLarge):shortest_tour(40,targets,region,9,9)
        tour=plan_tour(p,s,region,targets)
        self.assertEqual(set(targets),set(tour[0]))
        self.assertIn('NOT optimal',p.planner.report['room_loot_route']['method'])
        self.assertFalse(p.loot_collection_receipts)

    def test_large_coin_room_returns_pickup_not_recovery_wait(self):
        s,p=arena();targets=list(range(10,17))+list(range(19,26))+[28,29]
        for c in targets:p.loot[c]={'cell':c,'name':'gold','top_item':{'name':'gold','quantity':8}}
        s['hero']['buffs']=[{'name':'hungry'}]
        d=p.cell(41,'loot: collect/open',intent=Intent.LOOT)
        a=before_room_exit(p,s,d)
        self.assertEqual('cell',a.action['type']);self.assertEqual(Intent.LOOT,a.intent)

    def test_heuristic_does_not_claim_unreachable_targets(self):
        self.assertIsNone(nearest_tour(10,[16],{10,16},9,9))


class HungryRecoveryTests(unittest.TestCase):
    def test_idle_hungry_recovery_is_bounded_instead_of_waiting_to_death(self):
        s,p=arena();s['hero']['buffs']=[{'name':'starving'}]
        with patch.object(p,'walkable',return_value=False):
            for _ in range(2):
                self.assertEqual('wait',recover(p,s,[],TacticalBlocked('room-loot-stall','no progress'),distance,neighbors,line_clear).action['type'])
            with self.assertRaises(Finished) as stopped:
                recover(p,s,[],TacticalBlocked('room-loot-stall','no progress'),distance,neighbors,line_clear)
        self.assertEqual('blocked',stopped.exception.outcome)
        self.assertEqual(s['hero']['max_hp'],s['hero']['hp'])


class DoorwayArrivalBudgetTests(unittest.TestCase):
    def setup_lure(self):
        s,p=arena();s['objects']=[enemy('gnoll scout',13)]
        for t in s['map']['cells']:
            if t['cell']//9==4:t['terrain']=6 if t['cell']==40 else 4
        p.update(s)
        a=p.door_ambush(s,s['objects'],s['objects'],kind='doorway')
        return s,p,a

    def test_distant_lure_waits_beyond_three_turns_just_outside_door(self):
        s,p,a=self.setup_lure();hide=p.ambush_plan['hide']
        self.assertNotEqual(40,hide);self.assertGreater(p.ambush_plan['arrival_budget'],3)
        s['hero']['cell']=hide;s['objects']=[];p.update(s)
        for _ in range(4):
            self.assertEqual('wait',p.door_ambush(s,[],[],kind='doorway').action['type'])

    def test_observed_entry_gets_surprise_attempt_not_more_waiting(self):
        s,p,a=self.setup_lure();s['hero']['cell']=p.ambush_plan['hide']
        s['objects']=[enemy('gnoll scout',40)];p.update(s)
        a=p.door_ambush(s,s['objects'],s['objects'],kind='doorway')
        self.assertEqual(40,a.action['cell']);self.assertIn('surprise attack',a.reason)

    def test_no_unbounded_wait_or_wait_through_large_health_loss(self):
        s,p,a=self.setup_lure();s['hero']['cell']=p.ambush_plan['hide'];s['objects']=[];p.update(s)
        p.ambush_plan['waits']=p.ambush_plan['arrival_budget']
        self.assertIsNone(p.door_ambush(s,[],[],kind='doorway'))
        s,p,a=self.setup_lure();s['hero']['hp']=1
        self.assertIsNone(p.door_ambush(s,[],[],kind='doorway'))


if __name__=='__main__':unittest.main()
