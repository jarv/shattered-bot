import unittest
from tools.room_tactics import investigate_suspect_container,suspect_container_pending
from tools.policy_geometry import distance
from tools.policy_runtime import Transaction
from tools import test_environment_quest as fixtures
from tools.test_challenge_rules import verified


class SuspectStagingTests(unittest.TestCase):
    def test_configured_optional_staging_does_not_interrupt_unfinished_threat_routes(self):
        for owner in ('ambush_plan','doorway_hold','multi_door_plan','ranged_plan','recent_threats'):
            s,_=self.encounter();p=verified();p.update(s)
            p.loot[8]={'name':'Chest','cell':8,'description':'It feels off; opening is a bad idea.'}
            p.suspect_probe_plan={'cell':8,'bank':25,'steps':2}
            if owner=='recent_threats':p.recent_threats[41]={'name':'sewer snake','cell':41}
            else:setattr(p,owner,{'goal':25})
            before=dict(p.suspect_probe_plan)
            self.assertIsNone(investigate_suspect_container(p,s,[],distance),owner)
            self.assertEqual(before,p.suspect_probe_plan)
            self.assertFalse(p.room_attempts)

    def encounter(self):
        s,p=fixtures.EnvironmentTests().setup_arena();p.tiles[39]['terrain']=6
        p.loot[8]={'name':'Chest','cell':8,'description':'It feels off; opening is a bad idea.'}
        p.loot[72]={'name':'Crystal chest','cell':72,'description':'It feels off; opening is a bad idea.'}
        p.tiles[8]['visible']=False;p.tiles[72]['visible']=False
        return s,p

    def test_changing_visible_loot_order_does_not_switch_target_or_bank(self):
        s,p=self.encounter();a=investigate_suspect_container(p,s,[],distance)
        self.assertIsNotNone(a);plan=dict(p.suspect_probe_plan)
        self.assertEqual(8,plan['cell'])
        s['hero']['cell']=a.action['cell'];p.loot={72:p.loot[72],8:p.loot[8]}
        a=investigate_suspect_container(p,s,[],distance)
        self.assertEqual(plan['cell'],p.suspect_probe_plan['cell'])
        self.assertEqual(plan['bank'],p.suspect_probe_plan['bank'])
        s['hero']['cell']=plan['bank'];p.tiles[8]['visible']=True
        a=investigate_suspect_container(p,s,[],distance)
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(8,p.target)

    def test_arrival_without_visibility_is_not_a_test_or_pickup(self):
        s,p=self.encounter();investigate_suspect_container(p,s,[],distance)
        bank=p.suspect_probe_plan['bank'];s['hero']['cell']=bank
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))
        self.assertIn((8,bank),p.suspect_failed_banks)
        self.assertNotIn((s['depth'],'suspect-container',8),p.room_attempts)
        self.assertIn(8,p.loot)

    def test_three_failed_views_defer_unfinished_without_recharging_forever(self):
        s,p=self.encounter();p.loot.pop(72)
        p.suspect_failed_banks={(8,24),(8,25),(8,26)}
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))
        self.assertIn(8,p.suspect_staging_deferred)
        self.assertFalse(suspect_container_pending(p,s))
        self.assertEqual('deferred-unfinished',p.deferred_obligations[-1]['status'])
        self.assertIn(8,p.loot)

    def test_staging_budget_is_not_reset_by_target_reordering(self):
        s,p=self.encounter();investigate_suspect_container(p,s,[],distance)
        p.suspect_probe_plan['steps']=32
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))
        self.assertIn(8,p.suspect_staging_deferred)

    def test_combat_pauses_but_does_not_silently_replace_plan(self):
        s,p=self.encounter();investigate_suspect_container(p,s,[],distance)
        plan=dict(p.suspect_probe_plan)
        self.assertIsNone(investigate_suspect_container(p,s,[{'name':'rat','cell':41}],distance))
        self.assertEqual(plan,p.suspect_probe_plan)

    def test_rejected_staging_rolls_back_and_floor_reset_clears_plan(self):
        s,p=self.encounter();tx=Transaction(p);investigate_suspect_container(p,s,[],distance);tx.rollback()
        self.assertIsNone(p.suspect_probe_plan)
        investigate_suspect_container(p,s,[],distance);p.memory.reset_floor(40)
        self.assertIsNone(p.suspect_probe_plan)
        self.assertFalse(p.suspect_failed_banks);self.assertFalse(p.suspect_staging_deferred)
