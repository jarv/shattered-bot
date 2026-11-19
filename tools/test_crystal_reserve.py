import unittest

from tools import test_environment_quest as fixtures
from tools.room_tactics import investigate_suspect_container,charge_suspect_container
from tools.policy_geometry import distance
from tools.policy_runtime import Transaction


class CrystalReserveTests(unittest.TestCase):
    def encounter(self):
        s,p=fixtures.EnvironmentTests().setup_arena();s['hero']['cell']=42
        p.tiles[39]['terrain']=6
        p.loot[44]={'cell':44,'name':'Crystal chest','description':'It feels off; opening is a bad idea.'}
        s['inventory'][0]['status']='3/4'
        return s,p

    def test_three_known_shots_do_not_start_crystal_attempt(self):
        s,p=self.encounter()
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))
        self.assertFalse(p.mimic_obligations)
        self.assertNotIn((s['depth'],'suspect-container',44),p.room_attempts)
        self.assertEqual(4,p.planner.report['suspect_readiness']['known_charges_required'])
        self.assertEqual('wait',charge_suspect_container(p,s,[]).action['type'])

    def test_four_known_shots_allow_existing_range_two_interception(self):
        s,p=self.encounter();s['inventory'][0]['status']='4/4'
        self.assertIsNone(charge_suspect_container(p,s,[]))
        action=investigate_suspect_container(p,s,[],distance)
        self.assertEqual('ZAP',action.action.get('action'));self.assertEqual(44,p.target)

    def test_ordinary_suspicious_chest_keeps_three_shot_readiness(self):
        s,p=self.encounter();p.loot[44]['name']='Chest'
        self.assertIsNone(charge_suspect_container(p,s,[]))
        self.assertIsNotNone(investigate_suspect_container(p,s,[],distance))

    def test_cursed_or_unknown_secondary_charges_never_fund_reserve(self):
        for mode in ('cursed','unknown'):
            s,p=self.encounter();wand=dict(s['inventory'][0],id='extra',name='wand of magic missile',status='4/4')
            if mode=='cursed':wand['known_cursed']=True
            else:wand['status']=None
            s['inventory'].append(wand)
            self.assertIsNone(investigate_suspect_container(p,s,[],distance))

    def test_recharge_never_overrides_starvation_threat_or_capacity(self):
        for mode in ('starving','enemy','capacity'):
            s,p=self.encounter();enemies=[]
            if mode=='starving':s['hero']['buffs']=[{'name':'starving'}]
            elif mode=='enemy':enemies=[{'name':'marsupial rat','cell':41}]
            else:s['inventory'][0]['status']='3/3'
            self.assertIsNone(charge_suspect_container(p,s,enemies))

    def test_rejected_recharge_rolls_back_existing_wait_budget(self):
        s,p=self.encounter();tx=Transaction(p)
        charge_suspect_container(p,s,[]);tx.rollback()
        self.assertNotIn((s['depth'],'suspect-charge-waits',0),p.room_attempts)


if __name__=='__main__':unittest.main()
