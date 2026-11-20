"""Floor-first Ghost and escape-backed crab ambush, using public synthetic inputs."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.ghost_quest import map_explored,visit_ghost,prepare_ghost,quest_combat,observe_quest
from tools.great_crab_tactics import choose,escape_route,guard_movement
from tools.policy_geometry import distance,neighbors
from tools.policy_decision import TacticalBlocked,Decision,Intent
from tools.policy_runtime import Transaction


class GhostExplorationTests(unittest.TestCase):
    def fixture(self):
        s,p=arena();s['depth']=3
        s['objects']=[{'name':'sad ghost','cell':41}]
        p.update(s)
        return s,p

    def test_unseen_frontier_defers_dialogue_even_if_exploration_attempts_exhausted(self):
        s,p=self.fixture()
        p.tiles.pop(0)
        p.exhausted.update(p.tiles)
        self.assertFalse(map_explored(p,s))
        self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))
        self.assertIsNone(p.ghost_menu)
        self.assertEqual(p.ghost_quest['stage'],'new')

    def test_mapped_only_tile_is_not_explored(self):
        s,p=self.fixture();p.tiles[50].update(mapped=True,observed=False)
        self.assertFalse(map_explored(p,s))
        self.assertIn(50,p.planner.report['ghost_exploration']['frontiers'])

    def test_unopened_regular_and_unresolved_iron_doors_defer_start(self):
        for terrain in (5,10):
            s,p=self.fixture();p.tiles[42]['terrain']=terrain
            self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))
            self.assertIsNone(p.ghost_menu)

    def test_completed_observed_map_allows_existing_prepared_dialogue(self):
        s,p=self.fixture()
        self.assertTrue(map_explored(p,s))
        self.assertEqual(visit_ghost(p,s,[],distance,neighbors).action,{'type':'cell','cell':41})
        self.assertEqual(p.ghost_menu['stage'],'dialogue')

    def test_no_quest_health_or_charge_waits_before_exploring(self):
        s,p=self.fixture();s['inventory'][0]['status']='2/6'
        s['hero']['hp']=int(.75*s['hero']['max_hp'])
        p.tiles.pop(0)
        self.assertIsNone(prepare_ghost(p,s,[]))
        self.assertNotIn('prepare_inputs',p.ghost_quest)
        p.update(s)
        self.assertEqual(prepare_ghost(p,s,[]).action['type'],'wait')

    def test_pending_reward_does_not_wait_for_new_map_coverage(self):
        s,p=self.fixture();p.ghost_quest['stage']='reward';p.tiles.pop(0)
        self.assertEqual(visit_ghost(p,s,[],distance,neighbors).action,{'type':'cell','cell':41})


class CrabEscapeTests(unittest.TestCase):
    def fixture(self,exit=True):
        s,p=arena();s['depth']=4
        width,height=13,9;door=57;crab=55
        floors={y*width+x for x in range(1,5) for y in range(3,6)}
        floors|={y*width+x for x in range(6,9) for y in range(3,6)}
        if exit:floors|={62,63}
        s['hero'].update(cell=door,hp=40,max_hp=40)
        s['map']={'width':width,'height':height,'cells':[
            {'cell':c,'terrain':6 if c==door or exit and c==61 else 1 if c in floors else 4,
             'visible':True,'observed':True} for c in range(width*height)]}
        s['objects']=[{'name':'great crab','cell':crab}]
        p.update(s)
        p.ghost_quest.update(stage='active',target='great crab',depth=4)
        return s,p,door

    def begin_hide(self):
        s,p,door=self.fixture()
        action=quest_combat(p,s,s['objects'],distance,neighbors)
        hide=p.great_crab_plan['hide']
        self.assertEqual(action.action,{'type':'cell','cell':hide})
        after=copy.deepcopy(s);after['hero']['cell']=hide;after['objects']=[]
        next(t for t in after['map']['cells'] if t['cell']==door)['terrain']=5
        p.update(after)
        return after,p,door,hide

    def test_one_entrance_pocket_is_not_an_ambush_or_escape_route(self):
        s,p,door=self.fixture(exit=False)
        self.assertFalse(escape_route(p,s,58,door,{55}))
        with self.assertRaises(TacticalBlocked):
            quest_combat(p,s,s['objects'],distance,neighbors)
        self.assertIsNone(p.great_crab_plan)

    def test_second_observed_exit_is_retained_when_hiding(self):
        s,p,door=self.fixture()
        action=quest_combat(p,s,s['objects'],distance,neighbors)
        plan=p.great_crab_plan
        self.assertTrue(plan['departing'])
        self.assertNotEqual(action.action.get('cell'),55)
        route=p.planner.report['great_crab']['escape_route']
        self.assertIn(61,route)
        self.assertNotIn(door,route)

    def test_shared_recovery_cannot_move_into_a_rejected_pocket(self):
        s,p,door=self.fixture(exit=False)
        action=Decision({'type':'cell','cell':58},'recovery: retreat',intent=Intent.RETREAT)
        with self.assertRaises(TacticalBlocked):
            guard_movement(p,s,action)

    def test_shared_movement_with_second_exit_and_real_attacks_are_not_misclassified(self):
        s,p,door=self.fixture()
        guard_movement(p,s,Decision({'type':'cell','cell':58},'retreat',intent=Intent.RETREAT))
        guard_movement(p,s,Decision({'type':'cell','cell':55},'attack'))

    def test_confirmed_door_departure_then_fresh_entry_admits_one_surprise(self):
        s,p,door,hide=self.begin_hide()
        self.assertEqual(choose(p,s,[]).action['type'],'wait')
        self.assertTrue(p.great_crab_plan['armed'])
        arrived=copy.deepcopy(s)
        arrived['objects']=[{'name':'great crab','cell':door}]
        next(t for t in arrived['map']['cells'] if t['cell']==door)['terrain']=6
        p.update(arrived)
        attack=choose(p,arrived,arrived['objects'])
        self.assertEqual(attack.action,{'type':'cell','cell':door})
        self.assertIn('fresh doorway surprise',attack.reason)
        self.assertIsNone(p.great_crab_plan)
        try:
            following=choose(p,arrived,arrived['objects'])
        except TacticalBlocked:
            following=None
        self.assertTrue(following is None or following.action!={'type':'cell','cell':door})

    def test_existing_open_door_and_previous_position_do_not_prove_fresh_surprise(self):
        s,p,door=self.fixture();s['hero']['cell']=58
        s['objects']=[{'name':'great crab','cell':door}]
        p.update(s);p.previous_position=door
        p.great_crab_plan={'depth':4,'branch':0,'door':door,'hide':58,'steps':0,'waits':0,
                           'start_hp':40,'last_crab':door,'armed':False}
        try:action=choose(p,s,s['objects'])
        except TacticalBlocked:action=None
        self.assertTrue(action is None or action.action!={'type':'cell','cell':door})

    def test_crab_entry_immediately_after_confirmed_departure_has_fresh_surprise(self):
        s,p,door=self.fixture()
        choose(p,s,s['objects']);hide=p.great_crab_plan['hide']
        after=copy.deepcopy(s);after['hero']['cell']=hide
        after['objects']=[{'name':'great crab','cell':door}]
        p.update(after)
        self.assertEqual(choose(p,after,after['objects']).action,{'type':'cell','cell':door})

    def test_blocked_second_exit_cancels_wait_instead_of_ignoring_lost_escape(self):
        s,p,door,hide=self.begin_hide()
        choose(p,s,[])
        p.tiles[61]['terrain']=4
        self.assertIsNone(choose(p,s,[]))
        self.assertIsNone(p.great_crab_plan)

    def test_hazards_and_unknown_onward_terrain_are_not_escape_routes(self):
        for mode in ('trap','plant','unknown','danger'):
            s,p,door=self.fixture()
            if mode=='trap':p.tiles[61]['trap']='burning trap'
            elif mode=='plant':p.tiles[61]['plant']='firebloom'
            elif mode=='unknown':p.tiles[62]['observed']=False
            else:s['danger_cells']=[61]
            self.assertFalse(escape_route(p,s,58,door,{55}),mode)

    def test_other_active_enemy_preempts_crab_lure(self):
        s,p,door,hide=self.begin_hide()
        s['objects']=[{'name':'sewer crab','cell':72}]
        self.assertIsNone(choose(p,s,s['objects']))
        self.assertIsNone(p.great_crab_plan)

    def test_unseen_crab_wait_is_bounded_and_does_not_claim_quest_completion(self):
        s,p,door,hide=self.begin_hide()
        for _ in range(8):self.assertEqual(choose(p,s,[]).action['type'],'wait')
        self.assertIsNone(choose(p,s,[]))
        self.assertEqual(p.ghost_quest['stage'],'active')

    def test_lure_health_and_input_budgets_cancel_without_claiming_success(self):
        for mode in ('health','inputs','floor'):
            s,p,door,hide=self.begin_hide()
            if mode=='health':s['hero']['hp']=30
            elif mode=='inputs':p.great_crab_plan['steps']=24
            else:s['depth']=3
            self.assertIsNone(choose(p,s,[]))
            self.assertIsNone(p.great_crab_plan)
            self.assertEqual(p.ghost_quest['stage'],'active')

    def test_public_quest_completion_releases_lure_and_return_movement(self):
        s,p,door,hide=self.begin_hide()
        s['ui']['texts']=['Thank you... come find me...']
        observe_quest(p,s)
        self.assertEqual(p.ghost_quest['stage'],'reward')
        self.assertIsNone(p.great_crab_plan)
        p.recent_threats={door:{'name':'great crab','cell':door}}
        guard_movement(p,s,Decision({'type':'cell','cell':58},'return for reward',intent=Intent.REPOSITION))

    def test_sleep_and_invisibility_preserve_observed_surprise_alternatives(self):
        for mode in ('sleep','invisible'):
            s,p,door=self.fixture(exit=False)
            if mode=='sleep':s['objects'][0]['sleeping']=True
            else:s['hero']['buffs']=[{'name':'invisibility'}]
            action=quest_combat(p,s,s['objects'],distance,neighbors)
            self.assertIn('surprise',action.reason)

    def test_rollback_does_not_keep_an_unexecuted_lure(self):
        s,p,door=self.fixture();transaction=Transaction(p)
        choose(p,s,s['objects'])
        transaction.rollback()
        self.assertIsNone(p.great_crab_plan)
        self.assertFalse(p.great_crab_attempts)


if __name__=='__main__':
    unittest.main()
