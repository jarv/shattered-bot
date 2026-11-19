import copy
import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.survival_policy import NavigationLoopGuard
from tools.policy_decision import Decision,Intent,TacticalBlocked
from tools.policy_runtime import Transaction
from tools.region_navigation import context
from tools.hidden_doors import continue_search_vantage


class DoorToggleLoopTests(unittest.TestCase):
    def test_open_close_flicker_cannot_hide_two_square_cycle(self):
        s,p=arena();guard=NavigationLoopGuard(repetitions=3)
        with self.assertRaises(TacticalBlocked):
            for i in range(20):
                s['hero']['cell']=40 if i%2==0 else 41
                next(t for t in s['map']['cells'] if t['cell']==40)['terrain']=6 if i%2==0 else 5
                guard.check(s,Decision({'type':'cell','cell':41 if i%2==0 else 40},
                                      'frontier' if i%2==0 else 'search vantage',Intent.EXPLORE))

    def test_region_decline_context_stable_across_ordinary_door_toggle(self):
        s,p=arena();p.tiles[40]['terrain']=5;a=context(p,s)
        p.tiles[40]['terrain']=6;self.assertEqual(a,context(p,s))
        p.tiles[40]['terrain']=4;self.assertNotEqual(a,context(p,s))

    def test_normalization_does_not_change_projectile_or_movement_geometry(self):
        s,p=arena();p.tiles[41]['terrain']=5
        self.assertFalse(p.shot_clear(s,43))
        p.tiles[41]['terrain']=6;self.assertTrue(p.shot_clear(s,43))

    def goal(self):
        s,p=arena();p.tiles[40]['terrain']=6;p.tiles[31]['terrain']=4
        p.secret_search_goal={'cell':40,'walls':{31},'steps':0}
        return s,p

    def test_arrival_at_door_finishes_search_before_frontier_can_reverse_it(self):
        s,p=self.goal()
        with patch.object(p,'systematic_exploration_enabled',return_value=True), \
                patch.object(p,'systematic_exploration',side_effect=AssertionError('must finish pending search first')):
            a=p.explore(s,[])
        self.assertEqual('search',a.action['type']);self.assertIn(31,p.searched_walls)
        self.assertIsNone(p.secret_search_goal)

    def test_search_commitment_retains_safety_and_rolls_back_rejected_proposals(self):
        s,p=self.goal();tx=Transaction(p,p.planner)
        continue_search_vantage(p,s,[],p.paths(s));tx.rollback()
        self.assertNotIn(31,p.searched_walls);self.assertIsNotNone(p.secret_search_goal)
        p.recent_threats[49]={'name':'gnoll scout','cell':49}
        self.assertIsNone(continue_search_vantage(p,s,[],p.paths(s)))
        self.assertIsNone(p.secret_search_goal)


if __name__=='__main__':unittest.main()
