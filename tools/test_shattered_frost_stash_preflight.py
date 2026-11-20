"""Run 21: do not start a frost test approach with no potion-protection route."""
import copy
import unittest

from tools.test_survival_bot import state
from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import Finished
from tools.potion_stash import stash_cells
from tools.puzzle_supplies import prepare_supplies, safe_test_bank


def potions():
    return [{'id':str(n), 'name':name, 'identified':False, 'quantity':1,
             'actions':['DROP','THROW','DRINK']}
            for n,name in enumerate(('silver potion','amber potion'))]


def fire_approach():
    # Visible public geometry reduction of decision 219, log line 609.
    # Omitted cells remain unknown, never newly visible safe stash squares.
    s=state()
    s['hero'].update(cell=457,hp=24,max_hp=25,level=2,strength=10,buffs=[])
    groups={
        4:[351,352,353,354,376,401,409,426,432,451,476,482,501,526,
           540,551,576,577,578],
        14:[377,378,402,403,427,428,440,452,453,465,477,478,490,502,
            503,514,515,527,528,535,536,537,538,539,552,553,564],
        29:[380,405,406,408,430,431,433,455,456,458,459,480,481,483,
            505,506,508,509,534],
        1:[414,435,436,437,460,484,485],
        18:[415,530],12:[434],
        0:[438,439,461,462,463,464,486,487,488,489,510,511,512,513,
           560,561,562,563,586,587,588,589,612,613],
        6:[457],
    }
    cells=[{'cell':c,'terrain':t,'visible':True,'observed':True}
           for t,cs in groups.items() for c in cs]
    cells += [{'cell':c,'terrain':14,'visible':True,'observed':True,
               'effects':['magical fire']}
              for c in (379,404,429,454,479,504,529,554)]
    s['map']={'width':25,'height':43,'cells':cells}
    s['inventory']=potions()
    s['objects']=[{'cell':377,'name':'iron key','top_item':{'name':'iron key'}},
                  {'cell':402,'name':'honeypot','top_item':{'name':'honeypot'}},
                  {'cell':428,'name':'ration of food','top_item':{'name':'ration of food'}}]
    p=verified();p.update(s)
    return s,p


class FrostStashPreflightTests(unittest.TestCase):
    def test_infeasible_recorded_bank_declines_before_approach(self):
        s,p=fire_approach()
        before=copy.deepcopy(s)
        self.assertTrue(safe_test_bank(p,s,456,distance,neighbors,allow_dry=True))
        staged=dict(s,hero=dict(s['hero'],cell=456))
        self.assertEqual([],stash_cells(p,staged,distance,neighbors,safe_test_bank))
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNone(d, 'Unstarted frost preparation must not approach a bank without a stash route')
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.deferred_room_controllers)
        self.assertEqual(before,s)
        self.assertIn(377,p.loot)  # No invented key or progression receipt.

    def test_current_bank_still_requires_actual_potion_protection(self):
        s,p=fire_approach()
        s['hero']['cell']=456  # Isolated position probe, not a replayed next observation.
        with self.assertRaises(Finished):
            prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.deferred_room_controllers)

    def test_admitted_stash_still_starts_real_drop_plan_not_drinking(self):
        s,_=arena()
        s['inventory']=potions()
        for t in s['map']['cells']:
            if t['cell']==40:t['terrain']=29
            if t['cell']==42:t.update(terrain=14,effects=['magical fire'])
        p=verified();p.update(s)
        self.assertTrue(stash_cells(p,s,distance,neighbors,safe_test_bank))
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(d)
        self.assertEqual('drop',p.potion_stash['phase'])
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.puzzle_probe)
        self.assertNotEqual('DRINK',d.action.get('action'))


if __name__=='__main__':
    unittest.main()
