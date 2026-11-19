import copy
import unittest
from tools.floor_metrics import FloorMetrics,from_rows


def state(depth=1,hp=20,turns=0,xp=0,level=1,items=()):
    return {'depth':depth,'branch':0,'hero':{'hp':hp,'max_hp':20,'cell':24,'level':level,'gold':0},
        'evaluation_stats':{'experience':xp,'experience_to_level':10,'elapsed_turns':turns},
        'inventory':[dict(name=n,quantity=q,id=str(i)) for i,(n,q) in enumerate(items)],'keys':[],'objects':[]}


class FloorMetricsTests(unittest.TestCase):
    def test_processed_meat_return_is_not_double_counted_as_new_ground_loot(self):
        m=FloorMetrics();a=state(items=[('mystery meat',3)]);b=state()
        m.accept(a,{'type':'item','id':'0','action':'DROP'},b)
        b['objects']=[{'cell':24,'name':'frozen carpaccio x3','top_item':{'name':'frozen carpaccio x3','quantity':3}}]
        c=state(items=[('frozen carpaccio',3)])
        m.accept(b,{'type':'cell','cell':24},c)
        floor=m.report()['floors'][0]
        self.assertEqual(0,floor['confirmed_ground_pickup_units'])
        self.assertEqual(3,floor['retrieved_drops']['frozen carpaccio'])
    def test_missed_rewards_are_separate_from_collected_units_and_floor_scoped(self):
        loss={'depth':1,'branch':0,'cell':26,'status':'missed-unrecoverable','collected':False}
        report=from_rows([{'accepted_transition':{'before':state(),'action':{'type':'wait'},'after':state(turns=1)}},
                          {'result':{'missed_loot':[loss]}}])
        f=report['floors'][0]
        self.assertEqual([loss],f['missed_loot'])
        self.assertEqual(1,f['missed_loot_incidents'])
        self.assertEqual(0,f['confirmed_ground_pickup_units'])
        old=from_rows([{'accepted_transition':{'before':state(),'action':{},'after':state(turns=1)}}])
        self.assertIsNone(old['floors'][0]['missed_loot_incidents'])
        self.assertFalse(old['missed_loot_evidence_available'])

    def test_turns_are_not_api_inputs_and_menu_is_not_a_turn(self):
        m=FloorMetrics();a=state(items=[('staff',1)]);b=state(turns=1,items=[('staff',1)])
        m.accept(a,{'type':'wait'},b);m.accept(b,{'type':'inspect'},copy.deepcopy(b))
        f=m.report()['floors'][0]
        self.assertEqual(2,f['accepted_inputs']);self.assertEqual(1,f['turns'])
        self.assertEqual({},f['inventory_additions'])

    def test_floor_transition_charged_to_departing_floor_and_terminal_damage_kept(self):
        m=FloorMetrics();a=state(hp=5,turns=4);b=state(depth=2,hp=4,turns=6)
        m.accept(a,{'type':'cell'},b)
        m.accept(b,{'type':'wait'},state(depth=2,hp=0,turns=7))
        one,two=m.report()['floors']
        self.assertEqual(2,one['turns']);self.assertEqual(1,one['observed_hp_loss'])
        self.assertTrue(one['descended_from']);self.assertEqual(4,two['observed_hp_loss'])

    def test_xp_rollover_and_unobservable_multilevel_gap(self):
        m=FloorMetrics();a=state(xp=8);b=state(xp=2,level=2)
        m.accept(a,{},b);self.assertEqual(4,m.report()['floors'][0]['experience_gained'])
        m.accept(b,{},state(xp=0,level=4))
        self.assertFalse(m.report()['floors'][0]['experience_complete'])

    def test_healing_does_not_cancel_previous_damage(self):
        m=FloorMetrics();a=state(hp=20);b=state(hp=10)
        m.accept(a,{},b);m.accept(b,{},state(hp=18))
        self.assertEqual(10,m.report()['floors'][0]['observed_hp_loss'])
        self.assertEqual(8,m.report()['floors'][0]['observed_hp_recovery'])

    def test_identification_rename_is_not_item_acquisition(self):
        m=FloorMetrics();m.accept(state(items=[('crimson potion',1)]),{},state(items=[('potion of frost',1)]))
        self.assertEqual({},m.report()['floors'][0]['inventory_additions'])

    def test_ground_pickup_and_drop_retrieval_not_double_counted(self):
        m=FloorMetrics();a=state();a['objects']=[{'cell':24,'name':'ration of food','top_item':{'name':'ration of food'}}]
        b=state(items=[('ration of food',1)])
        m.accept(a,{'type':'cell','cell':24},b)
        m.accept(b,{'type':'item','id':'0','action':'DROP'},a)
        m.accept(a,{'type':'cell','cell':24},b)
        f=m.report()['floors'][0]
        self.assertEqual(1,f['confirmed_ground_pickup_units'])
        self.assertEqual(1,f['retrieved_drops']['ration of food'])

    def test_missing_old_telemetry_is_unavailable_not_zero(self):
        a=state();b=state();a.pop('evaluation_stats');b.pop('evaluation_stats')
        m=FloorMetrics();m.accept(a,{},b);f=m.report()['floors'][0]
        self.assertIsNone(f['turns']);self.assertIsNone(f['experience_gained'])

    def test_rejected_proposal_cannot_change_metrics(self):
        a=state();b=state(hp=0,turns=10)
        report=from_rows([{'index':1,'action':{},'state':a},{'index':1,'rejected':'400'}])
        self.assertEqual([],report['floors'])

    def test_journal_keys_count_separately_and_initial_gear_not_loot(self):
        m=FloorMetrics();start=state(items=[('staff',1)])
        m.accept({}, {}, start)
        after=copy.deepcopy(start);after['keys']=[{'name':'iron key','depth':1,'quantity':1}]
        m.accept(start,{},after)
        f=m.report()['floors'][0]
        self.assertEqual({},f['inventory_additions'])
        self.assertEqual(1,f['journal_keys_acquired']['iron key (floor 1)'])


if __name__=='__main__':unittest.main()
