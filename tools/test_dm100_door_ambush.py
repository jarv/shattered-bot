import copy
import json
import os
from pathlib import Path
import unittest

from tools.ranged_tactics import choose
from tools.test_regular_feedback import arena
from tools.mage_policy import MagePolicy


def doorway():
    s,p=arena()
    s['hero'].update(cell=30,hp=40,max_hp=40)
    cells={t['cell']:t for t in s['map']['cells']}
    cells[40]['terrain']=5
    cells[31]['terrain']=4
    s['objects']=[{'name':'DM-100','cell':11}]
    p.update(s)
    return s,p


class DM100DoorAmbushTests(unittest.TestCase):
    def reach_bank(self):
        s,p=doorway()
        a=p.choose(s)
        self.assertEqual({'type':'cell','cell':40},a.action)
        self.assertEqual(41,p.ranged_plan['goal'])
        after=copy.deepcopy(s)
        after['hero'].update(cell=40,hp=33)
        after['objects']=[]
        for t in after['map']['cells']:
            if t['cell']==40:t['terrain']=6
            if t['cell']==11:t['visible']=False
        a=p.choose(after)
        self.assertEqual({'type':'cell','cell':41},a.action)
        self.assertIn('committed cover',a.reason)
        bank=copy.deepcopy(after)
        bank['hero'].update(cell=41,hp=29)
        for t in bank['map']['cells']:
            if t['cell']==40:t['terrain']=5
        return bank,p

    def test_door_cover_precedes_distant_wand_exchange_and_melee_chase(self):
        s,p=doorway()
        a=choose(p,s,s['objects'])
        self.assertEqual({'type':'cell','cell':40},a.action)
        self.assertEqual('cover',p.ranged_plan['mode'])
        self.assertEqual(41,p.ranged_plan['goal'])
        self.assertEqual(40,p.ranged_plan['door'])

    def test_incoming_doorway_damage_does_not_reverse_into_firing_lane(self):
        self.reach_bank()

    def test_wait_off_doorway_then_attack_visible_adjacent_dm100(self):
        s,p=self.reach_bank()
        a=p.choose(s)
        self.assertEqual({'type':'wait'},a.action)
        self.assertEqual(1,p.ranged_plan['waits'])
        arrived=copy.deepcopy(s)
        arrived['objects']=[{'name':'DM-100','cell':40}]
        a=p.choose(arrived)
        self.assertNotEqual({'type':'wait'},a.action)
        self.assertIn('attack adjacent caster',a.reason)
        self.assertIsNone(p.ranged_plan)

    def test_damage_after_wait_invalidates_cover_even_with_starvation(self):
        s,p=self.reach_bank()
        self.assertEqual({'type':'wait'},choose(p,s,[]).action)
        hurt=copy.deepcopy(s)
        hurt['hero']['hp']-=3
        hurt['hero']['buffs']=[{'name':'starving'}]
        p.update(hurt)
        a=choose(p,hurt,[])
        self.assertIn(('dm-100',41),p.ranged_failed_cover)
        self.assertTrue(a is None or a.action!={'type':'wait'})

    def test_lure_waits_are_bounded_and_do_not_attack_remembered_positions(self):
        s,p=self.reach_bank()
        for _ in range(6):
            a=choose(p,s,[])
            self.assertEqual({'type':'wait'},a.action)
        a=choose(p,s,[])
        self.assertTrue(a is None or a.action!={'type':'wait'})
        self.assertIn(('dm-100',41),p.ranged_failed_cover)

    def test_hazards_and_movement_impairment_are_not_admitted_as_door_route(self):
        for hazard in ('trap','fire','loot','rooted','warning'):
            s,p=doorway()
            if hazard=='trap':p.tiles[40]['trap']='toxic gas trap'
            if hazard=='fire':p.tiles[40]['effects']=['A fire is raging here.']
            if hazard=='loot':p.loot[40]={'name':'gold'}
            if hazard=='rooted':s['hero']['buffs']=[{'name':'rooted'}]
            if hazard=='warning':s['danger_cells']=[40]
            with self.subTest(hazard=hazard):
                a=choose(p,s,s['objects'])
                self.assertTrue(a is None or a.action!={'type':'cell','cell':40})

    def test_low_hp_does_not_fund_multiple_exposed_steps_for_cover(self):
        s,p=doorway()
        s['hero']['hp']=5
        choose(p,s,s['objects'])
        self.assertTrue(p.ranged_plan is None or p.ranged_plan['mode']!='cover')

    def test_unknown_terrain_is_not_proof_of_line_breaking_cover(self):
        s,p=doorway()
        del p.tiles[31]
        choose(p,s,s['objects'])
        self.assertTrue(p.ranged_plan is None or p.ranged_plan['mode']!='cover')

    def test_starvation_budget_does_not_fund_stationary_cover_waits_without_food(self):
        s,p=self.reach_bank()
        s['hero']['buffs']=[{'name':'starving'}]
        s['inventory']=[]
        s['evaluation_stats']={'elapsed_turns':200}
        p.update(s)
        a=choose(p,s,[])
        self.assertTrue(a is None or a.action!={'type':'wait'})

    def test_floor_change_discards_the_door_plan(self):
        s,p=self.reach_bank()
        s=copy.deepcopy(s)
        s['depth']+=1
        p.update(s)
        self.assertIsNone(p.ranged_plan)

    def test_private_recorded_doorway_ping_pong_finishes_the_sight_break(self):
        path=os.environ.get('SHATTERED_DM100_FIXTURE')
        if not path:self.skipTest('optional private run51 recording')
        rows=json.loads(Path(path).read_text())
        observations={r['index']:r['state'] for r in rows if 'state' in r and 'index' in r}
        p=MagePolicy(engine='planner')
        p.challenges_verified=True
        a=p.choose(observations[2697])
        self.assertEqual({'type':'cell','cell':1436},a.action)
        self.assertEqual(1437,p.ranged_plan['goal'])
        a=p.choose(observations[2698])
        self.assertEqual({'type':'cell','cell':1437},a.action)
        self.assertNotEqual(1388,a.action['cell'])


if __name__=='__main__':
    unittest.main()
