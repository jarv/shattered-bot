import copy
import unittest
from unittest.mock import patch

from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools import multi_enemy_tactics as multi
from tools.ranged_tactics import choose


def door_room():
    s,_=arena();s['hero']['cell']=38
    cells=[]
    for c in range(99):
        x,y=c%11,c//11
        terrain=4 if x in {0,10} or y in {0,8} or y==5 else 1
        if y>=6:terrain=1 if x==5 and y<=7 else 4
        if c==60:terrain=5
        if y<=5:cells.append({'cell':c,'terrain':terrain,'visible':True,'observed':True})
    s['map']={'width':11,'height':9,'cells':cells}
    s['objects']=[enemy('swarm of flies',39),enemy('swarm of flies',50)]
    p=verified();p.update(s)
    return s,p


class DoorCommitmentTests(unittest.TestCase):
    def test_closed_door_is_a_staging_goal_without_certifying_unknown_side(self):
        s,p=door_room();a=multi.choose(p,s,s['objects'])
        self.assertEqual(60,p.multi_door_plan['door'])
        self.assertIn(a.action['cell'],{48,49})
        self.assertNotIn(71,p.tiles);self.assertIsNone(p.doorway_hold)
        self.assertIn('open/reobserve',a.reason)

    def test_route_continues_with_only_one_current_attacker(self):
        s,p=door_room();multi.choose(p,s,s['objects'])
        s['hero']['cell']=49;s['objects']=[enemy('swarm of flies',38),enemy('swarm of flies',39)];p.update(s)
        a=multi.choose(p,s,s['objects'])
        self.assertEqual(60,a.action['cell'])
        self.assertEqual(60,p.multi_door_plan['door'])

    def test_accepted_door_opening_counts_without_inventing_hero_movement(self):
        s,p=door_room();multi.choose(p,s,s['objects'])
        s['hero']['cell']=49;s['objects']=[enemy('swarm of flies',38),enemy('swarm of flies',39)];p.update(s)
        a=multi.choose(p,s,s['objects']);a.controller='multi-threat-retreat'
        after=copy.deepcopy(s);next(t for t in after['map']['cells'] if t['cell']==60)['terrain']=6
        receipt=multi.observe_accepted(p,s,a,after)
        self.assertIsNotNone(receipt);self.assertEqual(1,p.multi_door_plan['steps'])
        self.assertEqual(49,after['hero']['cell'])

    def test_observed_far_side_enables_actual_single_attacker_hold(self):
        s,p=door_room();multi.choose(p,s,s['objects'])
        s['hero']['cell']=60;s['objects']=[enemy('swarm of flies',38),enemy('swarm of flies',39)]
        s['map']['cells'].extend({'cell':c,'terrain':1 if c%11==5 and c//11<=7 else 4,
                                 'visible':True,'observed':True} for c in range(66,99))
        for t in s['map']['cells']:
            t.update(visible=True,observed=True)
            if t['cell']//11>=6:t['terrain']=1 if t['cell']%11==5 and t['cell']//11<=7 else 4
            if t['cell']==60:t['terrain']=6
        p.update(s);a=multi.choose(p,s,s['objects'])
        self.assertEqual(71,a.action['cell']);self.assertEqual(71,p.doorway_hold['hide'])

    def test_staging_rejection_rolls_back_plan_and_door_attempt(self):
        s,p=door_room();tx=Transaction(p,p.planner);multi.choose(p,s,s['objects']);tx.rollback()
        self.assertIsNone(p.multi_door_plan);self.assertFalse(p.multi_door_attempts)

    def test_door_plan_cannot_ignore_trap_or_health_loss_budget(self):
        for case in ('trap','health'):
            s,p=door_room();multi.choose(p,s,s['objects'])
            if case=='trap':p.tiles[60]['trap']='burning trap'
            else:s['hero']['hp']=1
            # Check the committed helper directly; ordinary fallback may choose another route.
            self.assertIsNone(multi.doorway_route(p,s,s['objects'],2),case)
            self.assertIsNone(p.multi_door_plan)


class TricksterCoverTests(unittest.TestCase):
    def setup_cover(self):
        s,p=arena();foe=enemy('gnoll trickster',44);s['objects']=[foe]
        s['inventory'][0]['status']='0/3'
        # A closed door between the hero and Trickster; do not step into it to hide.
        for c in (41,):next(t for t in s['map']['cells'] if t['cell']==c)['terrain']=5
        p.update(s)
        return s,p,foe

    def test_retain_actual_cover_instead_of_entering_doorway(self):
        s,p,foe=self.setup_cover();a=choose(p,s,[foe])
        self.assertEqual('wait',a.action['type']);self.assertEqual(40,p.ranged_plan['goal'])

    def test_cover_destination_is_never_the_door_itself(self):
        s,p,foe=self.setup_cover();s['hero']['cell']=42;p.update(s)
        a=choose(p,s,[foe])
        if p.ranged_plan and p.ranged_plan['mode']=='cover':
            self.assertNotIn(p.tiles[p.ranged_plan['goal']]['terrain'],{5,6})
        self.assertIsNotNone(a)

    def test_cover_is_rejected_on_new_poison_instead_of_excusing_damage(self):
        s,p,foe=self.setup_cover();choose(p,s,[foe]);s['hero']['buffs']=[{'name':'poisoned'}]
        s['hero']['hp']-=1;p.update(s);choose(p,s,[foe])
        self.assertIn(('gnoll trickster',40),p.ranged_failed_cover)

    def test_recent_trickster_still_gets_cover_logic_when_temporarily_unseen(self):
        s,p,foe=self.setup_cover();s['objects']=[];p.recent_threats[44]=foe
        a=choose(p,s,[])
        self.assertEqual('wait',a.action['type']);self.assertEqual('gnoll trickster',p.ranged_plan['name'])


if __name__=='__main__':unittest.main()
