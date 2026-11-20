"""Run 10 feedback: prioritize observed doors, not a claimed gameplay replay."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_shattered_dm100_exhausted_sleep import exhausted_scene
from tools.dm100_escape import choose,observe,exposed_memory
from tools.ranged_tactics import exposed_wait
from tools.continuation import best_effort
from tools.policy_nodes import preparation_and_recovery
from tools.policy_runtime import Transaction


class ImmediateDoorFlightTests(unittest.TestCase):
    def corridor(self):
        s,p=arena()
        s['hero'].update(cell=31,hp=40,max_hp=40)
        s['objects']=[{'name':'DM-100','cell':13}]
        floors={y*9+x for y in range(1,4) for x in range(1,8)}
        hidden={49,58,67}
        s['map']['cells']=[{'cell':c,'terrain':5 if c==40 else 1 if c in floors else 4,
                           'visible':True,'observed':True} for c in range(81) if c not in hidden]
        p.tiles.clear()
        p.update(s)
        return s,p

    def at_bank(self):
        s,p=self.corridor()
        self.assertEqual(choose(p,s,s['objects']).action,{'type':'cell','cell':40})
        opened=copy.deepcopy(s)
        next(t for t in opened['map']['cells'] if t['cell']==40)['terrain']=6
        p.update(opened)
        self.assertEqual(choose(p,opened,opened['objects']).action,{'type':'cell','cell':40})
        entered=copy.deepcopy(opened);entered['hero']['cell']=40;entered['objects']=[]
        entered['map']['cells'] += [{'cell':c,'terrain':1,'visible':True,'observed':True} for c in (49,58,67)]
        p.update(entered)
        action=choose(p,entered,[])
        self.assertEqual(action.action,{'type':'cell','cell':49})
        bank=copy.deepcopy(entered);bank['hero']['cell']=49
        next(t for t in bank['map']['cells'] if t['cell']==40)['terrain']=5
        p.update(bank)
        return bank,p

    def test_run10_visible_door_precedes_wand_exchange_loot_and_optional_preparation(self):
        s,p=exhausted_scene();s['inventory'][0]['status']='1/7'
        with patch.object(p,'preparation',side_effect=AssertionError('optional preparation delayed escape')):
            action=p.choose(s)
        self.assertEqual(action.action,{'type':'cell','cell':711})
        self.assertEqual(p.ranged_plan['door'],901)
        self.assertEqual(action.controller,'dm100-door-escape')
        self.assertIsNone(p.target)

    def test_unknown_far_side_does_not_prevent_reaching_visible_door_or_authorize_blind_click(self):
        s,p=self.corridor();action=choose(p,s,s['objects'])
        self.assertEqual(action.action,{'type':'cell','cell':40})
        self.assertEqual(p.ranged_plan['mode'],'door-flight')
        self.assertNotIn(49,p.tiles)

    def test_nearest_visible_door_wins_by_observed_route_length(self):
        s,p=self.corridor();p.tiles[37]['terrain']=5
        self.assertEqual(choose(p,s,s['objects']).action,{'type':'cell','cell':40})
        self.assertEqual(p.ranged_plan['door'],40)

    def test_committed_door_persists_out_of_view_and_after_transit_damage(self):
        s,p=exhausted_scene();choose(p,s,[s['objects'][0]])
        after=copy.deepcopy(s);after['hero'].update(cell=711,hp=25);after['objects']=[]
        for tile in after['map']['cells']:
            if tile['cell'] in {558,901}:tile['visible']=False
        p.update(after);p.recent_threats.clear()
        action=choose(p,after,[])
        self.assertEqual(action.action,{'type':'cell','cell':749})
        self.assertEqual(p.ranged_plan['door'],901)

    def test_step_off_door_then_wait_for_visible_entry_and_one_surprise(self):
        s,p=self.at_bank()
        action=choose(p,s,[])
        self.assertEqual(action.action,{'type':'wait'})
        self.assertTrue(p.ranged_plan['armed'])
        arrived=copy.deepcopy(s);arrived['objects']=[{'name':'DM-100','cell':40}]
        next(t for t in arrived['map']['cells'] if t['cell']==40)['terrain']=6
        p.update(arrived)
        self.assertEqual(choose(p,arrived,arrived['objects']).action,{'type':'cell','cell':40})
        self.assertIsNone(p.ranged_plan)

    def test_no_wait_if_door_reopens_into_the_lightning_lane(self):
        s,p=self.at_bank();choose(p,s,[])
        p.tiles[40]['terrain']=6
        action=choose(p,s,[])
        self.assertTrue(action is None or action.action!={'type':'wait'})

    def test_no_wait_after_damage_at_established_bank(self):
        s,p=self.at_bank();choose(p,s,[])
        hurt=copy.deepcopy(s);hurt['hero']['hp']-=5;p.update(hurt)
        action=choose(p,hurt,[])
        self.assertTrue(action is None or action.action!={'type':'wait'})

    def test_unseen_caster_does_not_allow_natural_healing_in_its_recent_lane(self):
        s,p=exhausted_scene();s['objects']=[];p.update(s);p.recent_threats.clear()
        self.assertTrue(exposed_memory(p,s))
        self.assertTrue(exposed_wait(p,s,[]))
        context=SimpleNamespace(active=[],enemies=[],policy=p,state=s)
        self.assertIsNone(preparation_and_recovery(context))

    def test_last_resort_uses_same_door_before_uncoordinated_retreat_or_noncritical_healing(self):
        s,p=exhausted_scene()
        action=best_effort(p,s,[s['objects'][0]])
        self.assertEqual(action.action,{'type':'cell','cell':711})
        self.assertEqual(p.ranged_plan['door'],901)

    def test_threat_memory_and_plans_reset_at_floor_boundary(self):
        s,p=self.corridor();choose(p,s,s['objects'])
        after=copy.deepcopy(s);after['depth']+=1;after['objects']=[]
        p.update(after)
        self.assertIsNone(p.ranged_plan);self.assertIsNone(p.dm100_threat)

    def test_recent_sighting_caution_is_bounded_not_a_hidden_actor_claim(self):
        s,p=self.corridor();s['objects']=[]
        for _ in range(13):observe(p,s)
        self.assertIsNone(p.dm100_threat)

    def test_known_traps_warning_and_impairment_remain_binding(self):
        for mode in ('trap','warning','rooted','unknown'):
            s,p=self.corridor()
            if mode=='trap':p.tiles[40]['trap']='explosive trap'
            elif mode=='warning':s['danger_cells']=[40]
            elif mode=='rooted':s['hero']['buffs']=[{'name':'rooted'}]
            else:p.tiles[40]['observed']=False
            self.assertIsNone(choose(p,s,s['objects']),mode)

    def test_unexecuted_escape_proposal_rolls_back_commitment(self):
        s,p=self.corridor();transaction=Transaction(p)
        choose(p,s,s['objects']);transaction.rollback()
        self.assertIsNone(p.ranged_plan)


if __name__=='__main__':
    unittest.main()
