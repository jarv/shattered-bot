import copy
import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.maze_objective import recognize,leave
from tools.loot_completion import observe_collected
from tools.policy_geometry import distance,neighbors
from tools.policy_decision import Intent
from tools.puzzle_supplies import prepare_supplies


def maze():
    s,_=arena();w=15
    floors={y*w+x for y in range(1,14,2) for x in range(1,14)}
    for k,y in enumerate(range(2,13,2)):floors.add(y*w+(13 if k%2==0 else 1))
    s['map']={'width':w,'height':w,'cells':[{'cell':c,'terrain':6 if c==15 else 1 if c in floors else 4,
        'visible':True,'observed':True}for c in range(w*w)]}
    s['hero']['cell']=207;s['objects']=[{'name':'Chest','cell':208}]
    p=verified();p.update(s)
    return s,p


class MazeObjectiveTests(unittest.TestCase):
    def test_maze_is_observed_single_entrance_geometry_not_a_hidden_room_id(self):
        s,p=maze();g=recognize(p,s,208)
        self.assertIsNotNone(g);self.assertEqual(15,g['door']);self.assertFalse(g['complete'])
        p.tiles.pop(0)
        self.assertIsNone(recognize(p,s,208))

    def test_opening_or_disappearance_does_not_complete_objective_but_item_pickup_does(self):
        s,p=maze();a=p.cell(208,'loot',intent=Intent.LOOT)
        after=copy.deepcopy(s);after['objects']=[]
        observe_collected(p,s,a,after)
        self.assertFalse(p.maze_goals[208]['complete']);self.assertFalse(p.completed_maze_cells)
        reward={'id':'prize','name':'longsword','quantity':1,'actions':['EQUIP']}
        before=copy.deepcopy(s);before['objects']=[{'cell':208,'name':'longsword','top_item':reward}]
        after=copy.deepcopy(before);after['inventory'].append(reward);after['objects']=[]
        observe_collected(p,before,a,after)
        self.assertTrue(p.maze_goals[208]['complete'])
        self.assertIn(208,p.completed_maze_cells)
        self.assertTrue(p.planner.report['maze_objective']['reward_collected'])
        self.assertFalse(p.visits[208])  # No fabricated visitation/clearance accounting.

    def test_completed_maze_is_left_and_not_reentered_for_optional_work(self):
        s,p=maze();g=recognize(p,s,208);g['complete']=True
        p.maze_goals[208]=g;p.completed_maze_cells.update(g['cells']);s['hero']['cell']=208
        self.assertIn('leave maze',leave(p,s,[]).reason)
        self.assertIsNone(leave(p,s,[{'name':'rat','cell':207}]))
        s['hero']['cell']=15
        self.assertIn(208,p.navigation_barriers(s,Intent.EXPLORE))
        self.assertNotIn(208,p.navigation_barriers(s,Intent.RETREAT))

    def test_uncollected_other_observed_loot_prevents_single_goal_retirement(self):
        s,p=maze();p.loot[16]={'name':'scroll of upgrade'}
        self.assertIsNone(recognize(p,s,208))


class FrostRecoveryTests(unittest.TestCase):
    def setup_barrier(self,heals=2):
        s,p=arena();s['hero'].update(hp=16,max_hp=20,buffs=[{'name':'hungry'}])
        p.tiles[42].update(terrain=14,visible=True,effects=['A wall of magical fire.'])
        s['inventory'] += [{'id':'unknown','name':'crimson potion','actions':['DRINK']},
                           {'id':'heal','name':'potion of healing','quantity':heals,'actions':['DRINK']}]
        return s,p

    def test_surplus_healing_can_fund_near_full_hungry_frost_probe_without_lowering_hp_gate(self):
        s,p=self.setup_barrier();a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual({'type':'item','id':'heal','action':'DRINK'},a.action)
        self.assertTrue(p.puzzle_hungry_frost);self.assertFalse(p.puzzle_drinks)
        s['hero']['hp']=20;s['inventory'][-1]['quantity']=1
        with patch('tools.puzzle_supplies.protect_potions',return_value=None):
            a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('unknown',a.action['id'])
        self.assertEqual('frost',p.puzzle_probe['kind'])

    def test_last_emergency_potion_or_starvation_does_not_fund_discretionary_probe(self):
        s,p=self.setup_barrier(1)
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors));self.assertFalse(p.puzzle_hungry_frost)
        s,p=self.setup_barrier();s['hero']['buffs']=[{'name':'starving'}]
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors));self.assertFalse(p.puzzle_hungry_frost)


if __name__=='__main__':unittest.main()
