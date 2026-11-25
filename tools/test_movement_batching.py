import copy
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools.movement_batching import prepare,observe
from tools.region_navigation import accepted_navigation
from tools.policy_runner import run
from tools.player_api import PlayerAPIError


def corridor():
    s,_=arena();w,h=17,7
    s['map']={'width':w,'height':h,'cells':[{'cell':c,'terrain':1 if c//w==3 and 1<=c%w<=15 else 4,
        'visible':True,'observed':True}for c in range(w*h)]}
    s['hero'].update(cell=54,hp=20,max_hp=20,buffs=[])
    s['objects']=[];s['capabilities']=['movement_trace'];s['evaluation_stats']={'elapsed_turns':20}
    p=verified();p.update(s)
    for c,t in p.tiles.items():
        if t['terrain']==1:p.visits[c]=1
    return s,p


def proposal(s,p,intent=Intent.EXPLORE,target=64):
    return p.toward(s,target,'explore: frontier',intent=intent)


def receipt(s,cells):
    after=copy.deepcopy(s);after['hero']['cell']=cells[-1]
    after['evaluation_stats']['elapsed_turns']+=len(cells)-1
    after['movement_trace']={'depth':s['depth'],'branch':s.get('branch',0),'same_floor':True,
                             'truncated':False,'cells':cells}
    return after


class MovementBatchTests(unittest.TestCase):
    def test_simple_batches_observed_unvisited_open_ground_and_descent_approach(self):
        from tools.mage_policy import MagePolicy
        for intent in (Intent.EXPLORE, Intent.LOOT, Intent.DESCEND):
            s, _ = corridor()
            for t in s['map']['cells']:
                if 1 <= t['cell']//17 <= 5 and 1 <= t['cell']%17 <= 15:
                    t['terrain'] = 1
            p = MagePolicy(profile='simple-bot')
            p.challenges_verified = True
            p.update(s)
            a = proposal(s, p, intent=intent)
            # Equal-length BFS routes across open rooms need not be straight.
            a.navigation_route = tuple(range(54, 65))
            a.action = {'type': 'cell', 'cell': 55}
            a = prepare(p, s, a)
            self.assertEqual(tuple(range(54, 61)), a.movement_batch)

    def test_simple_does_not_batch_past_unknown_edges_or_locked_doors(self):
        from tools.mage_policy import MagePolicy
        for mode in ('unknown', 'door', 'trap', 'loot'):
            s, _ = corridor()
            p = MagePolicy(profile='simple-bot')
            p.challenges_verified = True
            p.update(s)
            if mode == 'unknown':p.tiles[38]['observed'] = False
            elif mode == 'door':p.tiles[38]['terrain'] = 10
            elif mode == 'trap':p.tiles[38].update(terrain=18, trap='flock trap')
            else:p.loot[38] = {'name': 'gold', 'cell': 38}
            a = prepare(p, s, proposal(s, p))
            self.assertFalse(a.movement_batch, mode)

    def test_clear_visited_straight_corridor_batches_at_most_six_steps(self):
        s,p=corridor();a=prepare(p,s,proposal(s,p))
        self.assertEqual({'type':'cell','cell':60},a.action)
        self.assertEqual(tuple(range(54,61)),a.movement_batch)
        self.assertEqual(64,a.navigation_route[-1])
        self.assertEqual(6,p.planner.report['movement_batch']['requested_steps'])

    def test_mage_final_arbitration_batches_but_plain_toward_stays_single_step(self):
        s,p=corridor();a=proposal(s,p)
        self.assertEqual(55,a.action['cell'])
        with patch('tools.survival_policy.SurvivalPolicy.choose',return_value=a):
            chosen=p.choose(s)
        self.assertEqual(60,chosen.action['cell']);self.assertTrue(chosen.movement_batch)

    def test_old_api_short_paths_and_non_navigation_actions_remain_single_step(self):
        for mode in ('old-api','short','targeting','modal'):
            s,p=corridor();a=proposal(s,p,target=56 if mode=='short' else 64)
            if mode=='old-api':s.pop('capabilities')
            if mode=='targeting':s['status']='targeting'
            if mode=='modal':s['modal']=True
            original=dict(a.action)
            self.assertEqual(original,prepare(p,s,a).action,mode)
            self.assertFalse(a.movement_batch)

    def test_retreat_combat_reposition_and_descent_are_not_batched(self):
        for intent in (Intent.RETREAT,Intent.BOSS,Intent.APPROACH,Intent.REPOSITION,Intent.DESCEND,Intent.OTHER):
            s,p=corridor();a=prepare(p,s,proposal(s,p,intent))
            self.assertEqual(55,a.action['cell']);self.assertFalse(a.movement_batch)

    def test_actors_sleepers_allies_and_recent_threats_prevent_batching(self):
        for mode in ('rat','sleeping','ally','recent','damage'):
            s,p=corridor()
            if mode=='recent':p.recent_threats[64]={'name':'marsupial rat','cell':64}
            elif mode=='damage':p.unseen_damage_turns=1
            else:s['objects']=[{'name':'sad ghost' if mode=='ally' else 'marsupial rat','cell':64,'sleeping':mode=='sleeping'}]
            self.assertFalse(prepare(p,s,proposal(s,p)).movement_batch,mode)

    def test_low_hp_hunger_and_volatile_statuses_prevent_batching(self):
        for mode in ('low','hungry','starving','haste','levitating','invisible','time bubble','poisoned','herbal healing','unknown status'):
            s,p=corridor()
            if mode=='low':s['hero']['hp']=10
            else:s['hero']['buffs']=[{'name':mode}]
            self.assertFalse(prepare(p,s,proposal(s,p)).movement_batch,mode)

    def test_timed_journeys_and_committed_tactics_never_batch(self):
        for owner in ('room_journey','puzzle_probe','ambush_plan','doorway_hold','escape_commitment',
                      'secret_search_goal','food_freeze_plan','ranged_plan'):
            s,p=corridor();setattr(p,owner,{'active':True})
            self.assertFalse(prepare(p,s,proposal(s,p)).movement_batch,owner)

    def test_unknown_unvisited_hazard_or_interaction_near_start_prevents_batching(self):
        for mode in ('unknown','invisible','unvisited','trap','plant','effect','loot','door','stairs','junction','barrier'):
            s,p=corridor()
            if mode=='unknown':p.tiles.pop(38)  # Wall beside the next corridor square.
            if mode=='invisible':p.tiles[55]['visible']=False
            if mode=='unvisited':p.visits[55]=0
            if mode=='trap':p.tiles[55]['trap']='poison dart trap'
            if mode=='plant':p.tiles[55]['plant']='Sungrass'
            if mode=='effect':p.tiles[55]['effects']=['Unnaturally frigid air.']
            if mode=='loot':p.loot[55]={'name':'gold'}
            if mode=='door':p.tiles[55]['terrain']=6
            if mode=='stairs':p.tiles[55]['terrain']=8
            if mode=='junction':p.tiles[38]['terrain']=1
            if mode=='barrier':p.completed_maze_cells.add(55)
            a=proposal(s,p)
            if a:self.assertFalse(prepare(p,s,a).movement_batch,mode)

    def test_segment_stops_before_junction_or_pickup_instead_of_crossing_it(self):
        for mode in ('junction','loot'):
            s,p=corridor()
            if mode=='junction':p.tiles[43]['terrain']=1  # Side opening next to cell 60.
            else:p.loot[60]={'name':'potion of strength'}
            a=prepare(p,s,proposal(s,p))
            self.assertTrue(a.movement_batch)
            self.assertLess(a.action['cell'],60)

    def test_receipt_counts_actual_intermediate_cells_without_double_counting_final_update(self):
        s,p=corridor();a=prepare(p,s,proposal(s,p));after=receipt(s,list(range(54,61)))
        p.last_decision=a
        r=observe(p,s,a,after)
        self.assertEqual('completed',r['status']);self.assertEqual(6,r['confirmed_steps'])
        self.assertEqual(2,p.visits[55]);self.assertEqual(1,p.visits[60])
        p.update(after)
        self.assertEqual(2,p.visits[60]);self.assertEqual(2,p.visits[55])

    def test_interruption_records_only_crossed_prefix_and_replans_after_cooldown(self):
        s,p=corridor();a=prepare(p,s,proposal(s,p));after=receipt(s,[54,55,56])
        after['objects']=[{'name':'marsupial rat','cell':59}]
        r=observe(p,s,a,after)
        self.assertEqual('interrupted',r['status']);self.assertEqual(2,r['confirmed_steps'])
        self.assertEqual(1,p.visits[57])
        self.assertGreater(p.movement_batch_ready_at,after['evaluation_stats']['elapsed_turns'])

    def test_missing_off_route_or_wrong_floor_receipts_disable_batching_without_fabricated_visits(self):
        for mode in ('missing','offroute','floor','branch','truncated','malformed'):
            s,p=corridor();a=prepare(p,s,proposal(s,p))
            after=receipt(s,[54,55,56])
            if mode=='missing':after.pop('movement_trace')
            if mode=='offroute':after=receipt(s,[54,55,72])
            if mode=='floor':after['depth']+=1
            if mode=='branch':after['branch']=1
            if mode=='truncated':after['movement_trace']['truncated']=True
            if mode=='malformed':after['movement_trace']=None
            r=observe(p,s,a,after)
            self.assertEqual('unverified',r['status'],mode);self.assertTrue(p.movement_batch_disabled)
            self.assertEqual(1,p.visits[55])

    def test_navigation_goal_accounts_observed_edges_not_a_fictional_long_jump(self):
        s,p=corridor()
        p.exploration_goal={'kind':'frontier','cell':64,'steps':0,'edges':Counter(),
                            'proposed':(s['depth'],54,55)}
        a=prepare(p,s,proposal(s,p));after=receipt(s,[54,55,56])
        accepted_navigation(p,s,a,after)
        self.assertEqual(2,p.exploration_goal['steps'])
        self.assertEqual(1,p.exploration_goal['edges'][(54,55)])
        self.assertEqual(1,p.exploration_goal['edges'][(55,56)])
        self.assertFalse(p.exploration_goal['edges'][(54,60)])

    def test_rejected_proposal_has_no_movement_credit_or_persistent_goal_change(self):
        s,p=corridor();p.exploration_goal={'kind':'frontier','cell':64,'steps':0,'edges':Counter(),
                                        'proposed':(s['depth'],54,55)}
        old=copy.deepcopy(p.exploration_goal);tx=Transaction(p,p.planner)
        prepare(p,s,proposal(s,p));tx.rollback()
        self.assertEqual(old,p.exploration_goal);self.assertEqual(1,p.visits[55])

    def test_runner_records_one_input_and_actual_six_step_receipt(self):
        s,p=corridor()
        class API:
            observation=s
            def step(self,action):
                self.action=action
                self.after=receipt(s,list(range(54,61)))
                return self.after
        api=API()
        with TemporaryDirectory() as temp,patch.object(p,'choose',side_effect=lambda state:prepare(p,state,proposal(state,p))):
            path=Path(temp)/'trace.jsonl'
            result=run(api,p,1,0,path,bounded=True);log=path.read_text()
        self.assertEqual(1,result['actions']);self.assertEqual(60,api.action['cell'])
        self.assertEqual(26,api.after['evaluation_stats']['elapsed_turns'])
        self.assertIn('"confirmed_steps": 6',log)
        self.assertIn('"requested_movement_route": [54, 55, 56, 57, 58, 59, 60]',log)
        self.assertEqual(2,p.visits[55])

    def test_rejected_api_batch_is_replanned_without_speculative_movement_credit(self):
        s,p=corridor()
        class API:
            observation=s
            calls=0
            def step(self,action):
                self.calls+=1
                if self.calls==1:raise PlayerAPIError(409,'stale observation')
                return receipt(s,[54,55,56])
            def state(self):return copy.deepcopy(s)
        api=API()
        with TemporaryDirectory() as temp,patch.object(p,'choose',side_effect=lambda state:prepare(p,state,proposal(state,p))):
            path=Path(temp)/'trace.jsonl';result=run(api,p,2,0,path,bounded=True)
        self.assertEqual(2,result['attempts']);self.assertEqual(1,result['actions'])
        self.assertEqual(2,p.visits[55]);self.assertEqual(1,p.visits[57])


if __name__=='__main__':unittest.main()
