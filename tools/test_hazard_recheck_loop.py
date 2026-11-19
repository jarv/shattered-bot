"""Hazard observation must not fight the immediate room-escape controller."""
import copy
import unittest

from tools.test_survival_bot import state,fully_known
from tools.survival_policy import SurvivalPolicy
from tools.resource_tactics import recheck_hazards,observe_hazard_recheck
from tools.policy_geometry import distance
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools.test_floor_potion_reservation import flight_room
from tools.test_consumable_tactics import potion
from tools.puzzle_supplies import demands,prepare_supplies
from tools.room_tactics import plan_journey
from tools.policy_geometry import neighbors


def gas_room():
    s,p=flight_room()
    tile=next(t for t in s['map']['cells'] if t['cell']==38)
    tile.update(terrain=1,effects=['A greenish cloud of toxic gas is swirling here.'])
    tile.pop('trap')
    p.update(s)
    return s,p


def corridor(door=False):
    s=fully_known(state());s['hero']['cell']=22
    for tile in s['map']['cells']:
        tile['terrain']={22:1,23:5 if door else 1,24:1,25:1,26:8}.get(tile['cell'],4)
        if tile['cell']==25:tile.update(visible=False,effects=['A greenish cloud of toxic gas is swirling here.'])
    p=SurvivalPolicy();p.update(s)
    return s,p


class HazardRecheckLoopTests(unittest.TestCase):
    def test_gas_reward_geometry_reserves_purity_supply_instead_of_waiting(self):
        s,p=gas_room()
        self.assertTrue(any(d.kind=='gas' and d.potion=='potion of purity' for d in demands(p,s,distance)))
        self.assertIsNone(recheck_hazards(p,s,p.paths(s),distance))
        self.assertEqual(0,p.hazard_recheck_waits)
        self.assertEqual('potion of purity',p.planner.report['potion_reservation']['potion'])
        p.tiles[38]['visible']=False
        self.assertIsNone(recheck_hazards(p,s,p.paths(s),distance))
        self.assertEqual(0,p.hazard_recheck_steps)

    def test_unknown_floor_candidate_can_be_tested_only_with_a_gas_reward_plan(self):
        s,p=gas_room()
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',action.action['action'])
        self.assertEqual('gas',p.room_journey.kind)
        s['hero']['buffs']=[{'name':'purification barrier','description':'Turns remaining: 20.'}]
        p.update(s)
        self.assertEqual('room: follow verified protected route',p.escape_special_room(s).reason)

    def test_known_purity_is_saved_for_planned_round_trip_and_observed_protection(self):
        s,p=gas_room();s['inventory'][-1]=potion('potion of purity')
        action=plan_journey(p,s,[],neighbors)
        self.assertEqual('potion of purity',action.action['id'])
        self.assertEqual('protect',p.room_journey.stage)
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))

    def test_closed_door_is_not_a_safe_viewpoint_or_safe_route_into_gas_room(self):
        s,p=corridor(door=True)
        self.assertIsNone(recheck_hazards(p,s,p.paths(s),distance))
        self.assertIsNone(p.hazard_recheck_pending)
        self.assertTrue(p.tiles[25]['effects']);self.assertFalse(p.walkable(25))

    def test_open_doorway_is_not_selected_as_the_viewpoint(self):
        s,p=corridor();p.tiles[23]['terrain']=6
        action=recheck_hazards(p,s,p.paths(s),distance)
        if action:self.assertNotEqual(23,p.hazard_recheck_pending['vantage'])

    def test_repeated_accepted_reentry_edge_stops_before_the_floor_budget(self):
        s,p=corridor()
        for count in (1,2):
            action=recheck_hazards(p,s,p.paths(s),distance)
            self.assertEqual(23,action.action['cell'])
            self.assertEqual(count-1,p.hazard_recheck_edges[(25,22,23)])
            after=copy.deepcopy(s);after['hero']['cell']=23
            receipt=observe_hazard_recheck(p,s,action,after)
            self.assertEqual(count,receipt['accepted_edge_traversals'])
        self.assertIsNone(recheck_hazards(p,s,p.paths(s),distance))
        self.assertEqual(2,p.hazard_recheck_steps)
        self.assertTrue(p.tiles[25]['effects'])

    def test_failed_unrelated_or_cross_floor_moves_do_not_consume_edge_budget(self):
        for case in ('unchanged','depth','branch','intent','action'):
            s,p=corridor();action=recheck_hazards(p,s,p.paths(s),distance)
            after=copy.deepcopy(s);after['hero']['cell']=23
            if case=='unchanged':after['hero']['cell']=22
            if case=='depth':after['depth']+=1
            if case=='branch':after['branch']=1
            if case=='intent':action.intent=Intent.LOOT
            if case=='action':action.action={'type':'wait'}
            self.assertIsNone(observe_hazard_recheck(p,s,action,after),case)
            self.assertFalse(any(p.hazard_recheck_edges.values()))

    def test_accepted_receipt_is_consumed_once_and_floor_local(self):
        s,p=corridor();action=recheck_hazards(p,s,p.paths(s),distance)
        after=copy.deepcopy(s);after['hero']['cell']=23
        self.assertIsNotNone(observe_hazard_recheck(p,s,action,after))
        self.assertIsNone(observe_hazard_recheck(p,s,action,after))
        p.memory.reset_floor(22)
        self.assertFalse(p.hazard_recheck_edges);self.assertIsNone(p.hazard_recheck_pending)

    def test_rejected_proposal_rolls_back_pending_observation_and_budget(self):
        s,p=corridor();transaction=Transaction(p,p.planner)
        recheck_hazards(p,s,p.paths(s),distance)
        self.assertIsNotNone(p.hazard_recheck_pending)
        transaction.rollback()
        self.assertIsNone(p.hazard_recheck_pending);self.assertFalse(p.hazard_recheck_edges)
        self.assertEqual(0,p.hazard_recheck_steps)

    def test_safe_visible_gas_wait_keeps_its_separate_bound(self):
        s,p=corridor();p.tiles[25]['visible']=True
        p.hazard_recheck_waits=16
        self.assertIsNone(recheck_hazards(p,s,p.paths(s),distance))
        self.assertFalse(any(p.hazard_recheck_edges.values()))


if __name__=='__main__':unittest.main()
