import unittest

from tools.barrier_followup import begin,advance,observe
from tools.puzzle_supplies import refresh_barrier,Demand
from tools.policy_decision import Intent
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


FIRE='A wall of dense bright green fire, caused by magic; extinguish it.'


class BarrierFollowupTests(unittest.TestCase):
    def encounter(self):
        s=state();s['hero'].update(cell=39,hp=20,max_hp=20,buffs=[])
        s['map']={'width':9,'height':9,'cells':[
            {'cell':c,'terrain':4 if c%9 in {0,8} or c//9 in {0,8} else 1,'visible':True,
             'effects':[FIRE] if c%9==5 and 2<=c//9<=6 else []} for c in range(81)]}
        s['objects']=[]
        p=verified_policy();p.update(s);begin(p,s,41,neighbors)
        return s,p

    def clear(self,s,p):
        for t in s['map']['cells']:t['effects']=[]
        p.update(s);observe(p)

    def test_return_goal_survives_recovery_visibility_loss(self):
        s,p=self.encounter();self.clear(s,p)
        for c in (23,32,41,50,59):p.tiles[c]['visible']=False
        a=advance(p,s,[],distance,neighbors)
        self.assertEqual(Intent.EXPLORE,a.intent)
        self.assertIn('return to observed extinguished',a.reason)
        self.assertIsNotNone(p.barrier_followup)

    def test_known_local_reward_precedes_distant_exploration(self):
        s,p=self.encounter();self.clear(s,p)
        s['hero']['cell']=41
        s['objects']=[{'name':'ration of food','cell':43,'top_item':{'name':'ration of food'}}]
        p.update(s)
        a=advance(p,s,[],distance,neighbors)
        self.assertEqual(Intent.LOOT,a.intent)
        self.assertLess(distance(a.action['cell'],43,9),distance(41,43,9))
        self.assertEqual(43,p.barrier_followup['target'])
        self.assertIn(43,p.loot)  # Proposal is not collection.

    def test_unknown_hazard_is_not_reinterpreted_as_cleared(self):
        s,p=self.encounter()
        self.assertIsNone(advance(p,s,[],distance,neighbors))
        self.assertIsNone(p.barrier_followup)
        self.assertEqual('deferred-unfinished',p.deferred_obligations[-1]['status'])
        self.assertTrue(p.fire_buffer)

    def test_combat_or_cold_recovery_pauses_without_dropping_goal(self):
        s,p=self.encounter();self.clear(s,p)
        self.assertIsNone(advance(p,s,[{'name':'rat','cell':40}],distance,neighbors))
        self.assertIsNotNone(p.barrier_followup)
        p.puzzle_probe={'depth':s['depth'],'kind':'frost','turns':0}
        self.assertIsNone(advance(p,s,[],distance,neighbors))
        self.assertIsNotNone(p.barrier_followup)

    def test_unseen_remembered_cold_gets_safe_reobservation_not_goal_loss(self):
        s,p=self.encounter();self.clear(s,p)
        s['hero']['cell']=37
        for c in p.barrier_followup['cleared']:
            p.tiles[c].update(visible=False,effects=['The air is unnaturally frigid here.'])
        a=advance(p,s,[],distance,neighbors)
        self.assertIsNotNone(a)
        self.assertEqual(Intent.EXPLORE,a.intent)
        self.assertIn('reobserve',a.reason)
        self.assertFalse(p.tiles[a.action['cell']].get('effects'))
        self.assertIsNotNone(p.barrier_followup)

    def test_deferred_or_suspicious_rewards_are_not_opened_by_followup(self):
        s,p=self.encounter();self.clear(s,p)
        s['hero']['cell']=41
        p.loot[43]={'name':'locked chest','cell':43}
        p.combat_deferred_loot.add(43)
        a=advance(p,s,[],distance,neighbors)
        self.assertTrue(a is None or a.intent!=Intent.LOOT)
        self.assertIn(43,p.loot)

    def test_budget_defers_without_claiming_room_complete(self):
        s,p=self.encounter();self.clear(s,p)
        p.barrier_followup['steps']=64
        self.assertIsNone(advance(p,s,[],distance,neighbors))
        self.assertIsNone(p.barrier_followup)
        self.assertTrue(p.deferred_obligations)
        self.assertFalse(p.completed_room_rewards)

    def test_rejection_rolls_back_goal_steps_and_floor_change_resets(self):
        s,p=self.encounter();self.clear(s,p)
        tx=Transaction(p);advance(p,s,[],distance,neighbors);tx.rollback()
        self.assertEqual(0,p.barrier_followup['steps'])
        p.frost_view_plan={'barrier':41,'view':39,'steps':1}
        p.frost_view_attempts.add((41,39))
        p.memory.reset_floor(0)
        self.assertIsNone(p.barrier_followup)
        self.assertIsNone(p.frost_view_plan)
        self.assertFalse(p.frost_view_attempts)

    def test_failed_vantage_is_not_reselected_or_reversed(self):
        s=state();s['hero'].update(cell=110,hp=20,max_hp=20,buffs=[])
        s['map']={'width':15,'height':15,'cells':[
            {'cell':c,'terrain':4 if c%15 in {0,14} or c//15 in {0,14} else 1,
             'visible':True,'effects':[]} for c in range(225)]}
        s['objects']=[];p=verified_policy();p.update(s)
        p.tiles[116].update(visible=False,effects=[FIRE])
        p.shot_clear=lambda *a:True
        demand=Demand('frost','potion of frost',116)
        paths=p.paths(s)
        a=refresh_barrier(p,s,demand,paths,distance)
        self.assertEqual(Intent.EXPLORE,a.intent)
        target=p.frost_view_plan['view']
        s['hero']['cell']=a.action['cell']
        b=refresh_barrier(p,s,demand,p.paths(s),distance)
        self.assertEqual(target,p.frost_view_plan['view'])
        self.assertNotEqual(110,b.action['cell'])
        s['hero']['cell']=target
        self.assertIsNone(refresh_barrier(p,s,demand,p.paths(s),distance))
        self.assertIn((116,target),p.frost_view_attempts)
        self.assertIsNone(refresh_barrier(p,s,demand,p.paths(s),distance))


if __name__=='__main__':unittest.main()
