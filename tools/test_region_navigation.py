import copy
import unittest

from tools.region_navigation import choose, regions, safe_paths, decline_goal, accepted_navigation
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy
from tools.policy_decision import Intent, TacticalBlocked
from tools.policy_runtime import Transaction


class RegionNavigationTests(unittest.TestCase):
    def layout(self):
        s=state()
        width,height=15,9
        # Two fully observed open regions separated by one public door.
        floors={y*width+x for y in range(2,7) for x in range(1,6)}
        floors|={y*width+x for y in range(2,7) for x in range(7,12)}
        door=4*width+6
        s['hero']['cell']=4*width+3
        s['map']={'width':width,'height':height,'cells':[
            {'cell':c,'terrain':6 if c==door else 1 if c in floors else 4,'visible':True}
            for c in range(width*height)]}
        p=verified_policy()
        p.update(s)
        p.exhausted.update(p.paths(s))
        p.visits.update({c:1 for c in p.paths(s)})
        frontiers=[]
        original=p.exploration_report
        p.exploration_report=lambda st,paths:dict(original(st,paths),unexplored_frontiers=list(frontiers),unopened_doors=[])
        return s,p,frontiers

    def decide(self,s,p):
        return choose(p,s,p.paths(s),set())

    def test_local_frontier_precedes_distant_reward(self):
        s,p,frontiers=self.layout()
        frontiers.append(5*15+4)
        p.loot[4*15+10]={'name':'gold x20','top_item':{'name':'gold x20'}}
        action=self.decide(s,p)
        self.assertEqual(Intent.EXPLORE,action.intent)
        self.assertEqual(frontiers[0],p.exploration_goal['cell'])
        self.assertEqual('finish local work',p.planner.report['region_navigation']['selection'])

    def test_visible_loot_across_adjacent_door_preempts_local_frontier(self):
        s,p,frontiers=self.layout();frontiers.append(5*15+4)
        self.decide(s,p)  # An existing frontier commitment is not absolute.
        p.loot[4*15+7]={'name':'torch','top_item':{'name':'torch'}}
        action=self.decide(s,p)
        self.assertEqual(Intent.LOOT,action.intent)
        self.assertEqual(4*15+7,p.exploration_goal['cell'])
        self.assertEqual('nearby visible loot before further frontier work',p.planner.report['region_navigation']['selection'])

    def test_remembered_non_supply_loot_does_not_gain_adjacent_override(self):
        s,p,frontiers=self.layout();frontiers.append(5*15+4)
        p.loot[4*15+7]={'name':'gold','top_item':{'name':'gold'}}
        p.tiles[4*15+7]['visible']=False
        self.assertEqual(Intent.EXPLORE,self.decide(s,p).intent)

    def test_remembered_nearby_torch_and_scroll_preempt_frontier(self):
        for name in ('torch','scroll of upgrade'):
            s,p,frontiers=self.layout();frontiers.append(5*15+4)
            self.decide(s,p)
            p.loot[4*15+7]={'name':name,'top_item':{'name':name}}
            p.tiles[4*15+7]['visible']=False
            self.assertEqual(Intent.LOOT,self.decide(s,p).intent)

    def test_recent_threat_blocks_adjacent_loot_override(self):
        s,p,frontiers=self.layout();frontiers.append(5*15+4)
        p.loot[4*15+7]={'name':'torch','top_item':{'name':'torch'}}
        p.recent_threats[4*15+6]={'name':'gnoll scout','cell':4*15+6}
        self.assertEqual(Intent.EXPLORE,self.decide(s,p).intent)

    def test_adjacent_loot_does_not_interrupt_committed_local_pickup(self):
        s,p,frontiers=self.layout();p.loot[4*15+2]={'name':'seed','top_item':{'name':'seed'}}
        self.decide(s,p)
        p.loot[4*15+7]={'name':'torch','top_item':{'name':'torch'}}
        self.decide(s,p)
        self.assertEqual(4*15+2,p.exploration_goal['cell'])

    def test_fixed_workload_needs_less_travel_than_global_loot_first(self):
        from unittest.mock import patch
        def travel(enabled):
            s,p,frontiers=self.layout()
            frontiers.append(6*15+2)
            reward=2*15+10
            exit_cell=6*15+11
            p.loot[reward]={'name':'gold x20','top_item':{'name':'gold x20'}}
            p.tiles[exit_cell]['terrain']=8
            p.searches=p.clear_steps=100
            moves=0
            with patch.object(p,'systematic_exploration_enabled',return_value=enabled):
                for _ in range(100):
                    pos=s['hero']['cell']
                    if pos in frontiers:frontiers.remove(pos)
                    action=p.explore(s,[])
                    self.assertEqual('cell',action.action['type'])
                    target=action.action['cell']
                    if target==pos and target in p.loot:p.loot.pop(target)
                    elif target!=pos:
                        moves+=1
                        s['hero']['cell']=target
                        p.visits[target]+=1
                    if target==exit_cell:
                        self.assertEqual(Intent.DESCEND,action.intent)
                        self.assertFalse(frontiers)
                        self.assertFalse(p.loot)
                        return moves
            self.fail('fixed workload did not terminate')
        self.assertLess(travel(True),travel(False))

    def test_local_loot_precedes_local_frontier(self):
        s,p,frontiers=self.layout()
        frontiers.append(5*15+4)
        p.loot[4*15+2]={'name':'gold x20','top_item':{'name':'gold x20'}}
        self.assertEqual(Intent.LOOT,self.decide(s,p).intent)

    def test_remote_goal_persists_when_nearer_frontier_appears(self):
        s,p,frontiers=self.layout()
        remote=4*15+10
        frontiers.append(remote)
        self.decide(s,p)
        frontiers.append(4*15+4)
        self.decide(s,p)
        self.assertEqual(remote,p.exploration_goal['cell'])
        self.assertEqual('continue committed target',p.planner.report['region_navigation']['selection'])

    def test_finished_goal_selects_remaining_work_without_reopening_empty_branch(self):
        s,p,frontiers=self.layout()
        frontiers.extend([4*15+4,4*15+10])
        self.decide(s,p)
        frontiers.remove(4*15+4)
        self.decide(s,p)
        self.assertEqual(4*15+10,p.exploration_goal['cell'])
        frontiers.clear()
        self.assertIsNone(self.decide(s,p))
        self.assertIsNone(p.exploration_goal)

    def test_region_merge_keeps_target_anchor_valid(self):
        s,p,frontiers=self.layout()
        target=4*15+10
        frontiers.append(target)
        self.decide(s,p)
        self.assertEqual(2,p.planner.report['region_navigation']['known_regions'])
        p.tiles[4*15+6]['terrain']=1
        self.decide(s,p)
        self.assertEqual(1,p.planner.report['region_navigation']['known_regions'])
        self.assertEqual(target,p.exploration_goal['cell'])

    def test_stairs_are_not_a_connector_for_ordinary_navigation(self):
        s,p,frontiers=self.layout()
        p.tiles[4*15+6]['terrain']=8
        frontiers.append(4*15+10)
        self.assertIsNone(self.decide(s,p))
        self.assertNotIn(4*15+10,safe_paths(p,s,p.paths(s)))

    def test_second_loop_connection_uses_known_short_route(self):
        s,p,frontiers=self.layout()
        p.tiles[2*15+6]['terrain']=6
        s['hero']['cell']=2*15+5
        target=2*15+7
        frontiers.append(target)
        action=self.decide(s,p)
        self.assertEqual(2*15+6,action.action['cell'])
        self.assertEqual(2,p.planner.report['region_navigation']['route_steps'])

    def test_suspicious_chest_and_missing_key_are_not_ordinary_tasks(self):
        s,p,frontiers=self.layout()
        p.loot[4*15+4]={'name':'Chest','description':'Something is wrong with this chest. It seems to be breathing.'}
        # Use the existing public warning recognizer rather than guessing identity.
        from unittest.mock import patch
        p.tiles[4*15+6]['terrain']=10
        p.keys['iron']=0
        with patch('tools.region_navigation.suspicious_container',return_value=True):
            self.assertIsNone(self.decide(s,p))

    def test_new_key_reopens_an_observed_locked_branch(self):
        s,p,frontiers=self.layout()
        door=4*15+6
        p.tiles[door]['terrain']=10
        p.keys['iron']=0
        self.assertIsNone(self.decide(s,p))
        p.keys['iron']=1
        self.assertIsNotNone(self.decide(s,p))
        self.assertEqual({'kind':'door','cell':door},
                         {k:p.exploration_goal[k] for k in ('kind','cell')})

    def test_mapping_only_room_keeps_observation_frontier(self):
        s,p,frontiers=self.layout()
        del p.exploration_report
        target=4*15+10
        p.tiles[target].update(mapped=True,observed=False,visible=False)
        p.exhausted.discard(target)
        self.assertIsNotNone(self.decide(s,p))
        self.assertEqual(target,p.exploration_goal['cell'])

    def test_stalled_goal_is_deferred_until_public_context_changes(self):
        s,p,frontiers=self.layout()
        target=4*15+4
        frontiers.append(target)
        self.decide(s,p)
        decline_goal(p,s,'bounded routing stall')
        self.assertIsNone(self.decide(s,p))
        self.assertEqual('deferred-unfinished',p.deferred_obligations[0]['status'])
        # A new key changes actionable routing context; passive healing does not.
        s['hero']['hp']-=1
        self.assertIsNone(self.decide(s,p))
        p.keys['iron']=1
        self.assertIsNotNone(self.decide(s,p))

    def test_stalled_pickup_is_not_restarted_by_room_exit_controller(self):
        from tools.room_loot import inventory_context
        s,p,frontiers=self.layout()
        target=4*15+4
        p.loot[target]={'name':'gold x20','top_item':{'name':'gold x20'}}
        self.decide(s,p)
        p.room_loot_plan={'target':target,'region':{target,s['hero']['cell']},'steps':1}
        decline_goal(p,s,'unresolved pickup')
        self.assertIsNone(p.room_loot_plan)
        self.assertEqual(inventory_context(s),p.room_loot_deferred[target])
        self.assertIn(target,p.loot)  # Deferred, not collected.

    def test_goal_state_rolls_back_and_resets_with_floor(self):
        s,p,frontiers=self.layout()
        frontiers.append(4*15+4)
        before=copy.deepcopy(p.memory.exploration)
        transaction=Transaction(p)
        self.decide(s,p)
        transaction.rollback()
        self.assertEqual(before,p.memory.exploration)
        self.decide(s,p)
        p.memory.reset_floor(s['hero']['cell'])
        self.assertIsNone(p.exploration_goal)
        self.assertFalse(p.region_seen_anchors)

    def test_combat_and_planner_engine_do_not_use_quiet_region_routing(self):
        s,p,frontiers=self.layout()
        self.assertFalse(p.systematic_exploration_enabled(s,[{'name':'gnoll scout','cell':64}]))
        p.engine='planner'
        self.assertFalse(p.systematic_exploration_enabled(s,[]))

    def test_repeated_route_edges_are_soft_failures(self):
        s,p,frontiers=self.layout()
        frontiers.append(4*15+4)
        for _ in range(3):
            action=self.decide(s,p)
            accepted_navigation(p,s,action,s)
        with self.assertRaises(TacticalBlocked) as caught:self.decide(s,p)
        self.assertEqual('systematic-route-stall',caught.exception.code)

    def test_overridden_proposal_does_not_spend_goal_progress_budget(self):
        s,p,frontiers=self.layout()
        frontiers.append(4*15+4)
        self.decide(s,p)
        alternative=p.cell(4*15+2,'local pickup interrupted route',intent=Intent.LOOT)
        accepted_navigation(p,s,alternative,s)
        self.assertEqual(0,p.exploration_goal['steps'])
        self.assertFalse(p.exploration_goal['edges'])

    def test_accepted_movement_feedback_uses_actual_hero_position(self):
        s,p,frontiers=self.layout()
        frontiers.append(4*15+4)
        action=self.decide(s,p)
        after=copy.deepcopy(s)
        after['hero']['cell']=action.action['cell']
        feedback=accepted_navigation(p,s,action,after)
        self.assertTrue(feedback['moved'])
        self.assertEqual(after['hero']['cell'],feedback['to'])
        self.assertEqual(1,p.exploration_goal['steps'])

    def test_observed_dead_end_is_not_extended_into_unknown_map(self):
        tiles={0:{'terrain':1},1:{'terrain':4}}
        owner,groups=regions(tiles,{0},3,1)
        self.assertEqual({0:{0}},groups)
        self.assertEqual({0:0},owner)

    def test_underlying_path_filter_preserves_revealed_trap_blocking(self):
        s,p,frontiers=self.layout()
        p.tiles[4*15+6].update(terrain=18,trap='burning trap')
        frontiers.append(4*15+10)
        self.assertIsNone(self.decide(s,p))


if __name__=='__main__':unittest.main()
