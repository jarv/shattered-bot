import unittest

from tools.test_challenge_systems import ready
from tools.challenge_combat import finish_weak_crab
from tools.policy_geometry import distance,neighbors,line_clear
from tools.policy_runtime import Transaction


class WeakCrabFinishTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['hero'].update(hp=9,max_hp=20,buffs=[])
        s['inventory'][0].update(status='1/4',curse_known=True,known_cursed=False)
        s['objects']=[{'name':'sewer crab','cell':25,'health_bar':[2,10]},
                      {'name':'marsupial rat','cell':10}]
        return s,p

    def choose(self,s,p):return finish_weak_crab(p,s,s['objects'],distance,neighbors,line_clear)

    def test_known_charge_can_finish_weak_adjacent_crab_before_withdrawal(self):
        s,p=self.encounter();a=self.choose(s,p)
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(25,p.target)
        self.assertEqual(1,p.weak_crab_finish_casts)

    def test_real_next_step_door_sight_break_retains_priority(self):
        s,p=self.encounter();p.tiles[24]['terrain']=6;s['objects'][1]['cell']=26
        self.assertIsNone(self.choose(s,p))

    def test_no_new_multi_attacker_or_critical_health_trade(self):
        for mode in ('critical','two_attackers','champion','burning','boss'):
            s,p=self.encounter()
            if mode=='critical':s['hero']['hp']=6
            elif mode=='two_attackers':s['objects'][1]['cell']=23
            elif mode=='champion':s['objects'][0]['description']='_Blazing Champion_'
            elif mode=='burning':s['hero']['buffs']=[{'name':'burning'}]
            else:s['boss_health_text']='10/10'
            self.assertIsNone(self.choose(s,p))

    def test_unknown_cursed_empty_and_nonweakened_do_not_qualify(self):
        for mode in ('unknown','cursed','empty','healthy_target'):
            s,p=self.encounter()
            if mode=='unknown':s['inventory'][0]['status']=None
            elif mode=='cursed':s['inventory'][0]['known_cursed']=True
            elif mode=='empty':s['inventory'][0]['status']='0/4'
            else:s['objects'][0]['health_bar']=[8,10]
            self.assertIsNone(self.choose(s,p))

    def test_two_cast_floor_budget_and_rejection_rollback(self):
        s,p=self.encounter();tx=Transaction(p);self.choose(s,p);tx.rollback()
        self.assertEqual(0,p.weak_crab_finish_casts)
        self.choose(s,p);self.choose(s,p)
        self.assertIsNone(self.choose(s,p))
        p.memory.reset_floor(24);self.assertEqual(0,p.weak_crab_finish_casts)


if __name__=='__main__':unittest.main()
