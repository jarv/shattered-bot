import unittest
from tools.test_required_corridor_and_flight_staging import flight_room
from tools.test_multi_enemy_and_fly_feedback import choke
from tools.test_unit_strategies import enemy
from tools.room_tactics import plan_journey
from tools.puzzle_supplies import prepare_supplies
from tools.policy_geometry import distance,neighbors,line_clear
from tools.doorway_tactics import hold_doorway
from tools import multi_enemy_tactics as multi
from tools.policy_decision import TacticalBlocked,NoSafeAction


class NecessaryProtectionRewardTests(unittest.TestCase):
    def test_chasm_shortcut_to_ground_reachable_dew_cannot_fund_probe(self):
        s,p=flight_room();s['hero']['cell']=67
        for t in s['map']['cells']:
            t['visible']=True
            if t['cell']//15==7 and 9<=t['cell']%15<=12:t['terrain']=1
        p.update(s);p.loot={73:{'cell':73,'name':'dewdrop','top_item':{'name':'dewdrop'}}}
        self.assertIn(73,p.paths(s))
        self.assertIsNone(plan_journey(p,s,[],neighbors,probe_kind='flight',plan_only=True))
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertTrue(a is None or a.action.get('action')!='DRINK')
        self.assertFalse(p.puzzle_drinks)

    def test_actual_inaccessible_chest_not_ordinary_dew_is_committed(self):
        s,p=flight_room();s['hero']['cell']=67
        for t in s['map']['cells']:t['visible']=True
        p.update(s);p.loot={73:{'cell':73,'name':'Chest'},68:{'cell':68,'name':'dewdrop','top_item':{'name':'dewdrop'}}}
        j=plan_journey(p,s,[],neighbors,probe_kind='flight',plan_only=True)
        self.assertEqual(73,j.route[-1]);self.assertNotIn(73,p.paths(s));self.assertIn(68,p.paths(s))


class ChokeEntryTests(unittest.TestCase):
    def test_direct_retreat_through_door_establishes_hold(self):
        s,p,foes=choke();a=multi.choose(p,s,foes)
        self.assertEqual(31,a.action['cell'])
        self.assertEqual({'door':24,'hide':31},{k:p.doorway_hold[k] for k in ('door','hide')})

    def entry(self):
        s,p,foes=choke();multi.choose(p,s,foes)
        s['hero']['cell']=31;s['objects']=[enemy('sewer snake',24)]
        s['inventory'][0]['status']='0/3';p.update(s);p.previous_position=24
        return s,p

    def test_observed_snake_entry_gets_surprise_attempt_instead_of_passive_wait(self):
        s,p=self.entry();a=hold_doorway(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertEqual({'type':'cell','cell':24},a.action)
        self.assertIn('surprise attack attempt',a.reason)

    def test_entry_does_not_override_critical_health_or_fly_splitting_guards(self):
        for case in ('health','fly'):
            s,p=self.entry()
            if case=='health':s['hero']['hp']=1
            else:s['objects']=[enemy('swarm of flies',24)]
            # Test only the new entry shortcut, not later legacy emergency handling.
            p.previous_position=24
            try:a=hold_doorway(p,s,s['objects'],distance,neighbors,line_clear)
            except (TacticalBlocked,NoSafeAction):a=None
            self.assertTrue(a is None or 'observed entry after retreat' not in a.reason,case)


if __name__=='__main__':unittest.main()
