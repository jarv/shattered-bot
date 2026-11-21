"""Preserve floor puzzle supplies, then use observed protection immediately."""
import copy
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.consumable_tactics import choose_consumable
from tools.potion_discovery import room_ready
from tools.puzzle_supplies import prepare_supplies,recover_probe
from tools.room_tactics import plan_journey
from tools.policy_geometry import distance,neighbors


def surveyed():
    s,p=arena();p.visits.update(p.tiles.keys());p.exhausted.update(p.tiles)
    return s,p


def flight_room():
    s,_=arena();s['hero']['cell']=36
    cells=[]
    for c in range(77):
        x,y=c%11,c//11
        terrain=4 if x in {0,10} or y in {0,6} or x==5 else 1
        if c==36:terrain=29
        if c==38:terrain=18
        tile={'cell':c,'terrain':terrain,'visible':True,'observed':True}
        if c==38:tile['trap']='poison dart trap'
        cells.append(tile)
    s['map']={'width':11,'height':7,'cells':cells}
    s['objects']=[{'cell':40,'name':'Chest'}]
    s['inventory'].append(potion())
    p=verified();p.update(s)
    return s,p


class FloorPotionReservationTests(unittest.TestCase):
    def test_cleared_current_room_is_not_a_cleared_floor(self):
        s,p=arena();s['inventory'].append(potion())
        self.assertFalse(room_ready(p,s))
        action=choose_consumable(p,s,[],distance,neighbors)
        self.assertIsNone(action)
        self.assertIn('potion_reservation',p.planner.report)
        self.assertFalse(p.planner.report['potion_reservation']['identity_inferred'])

    def test_each_unfinished_floor_obligation_preserves_unknown_potions(self):
        for key in ('unvisited_reachable','unexplored_frontiers','unopened_doors','unresolved_doors',
                    'unreachable_known_floor','remaining_enemy_sightings'):
            s,p=surveyed();report=p.exploration_report(s,p.paths(s));report[key]=[20]
            with patch.object(p,'exploration_report',return_value=report):
                self.assertFalse(room_ready(p,s),key)

    def test_blind_testing_waits_for_descent_even_after_survey_without_puzzle_obligations(self):
        s,p=surveyed();s['inventory'].append(potion())
        self.assertTrue(room_ready(p,s))
        action=choose_consumable(p,s,[],distance,neighbors)
        self.assertIsNone(action)
        next(t for t in s['map']['cells'] if t['cell']==s['hero']['cell'])['terrain']=29
        p.update(s)
        from tools.descent_potions import begin
        action=begin(p,s)
        self.assertEqual('DRINK',action.action['action'])

    def test_identification_scroll_and_known_strength_are_not_reserved(self):
        for mode in ('identify','strength'):
            s,p=arena();s['inventory'].append(potion('potion of strength' if mode=='strength' else 'azure potion'))
            if mode=='identify':s['inventory'].append({'id':'identify','name':'scroll of identify','actions':['READ']})
            action=choose_consumable(p,s,[],distance,neighbors)
            self.assertEqual('READ' if mode=='identify' else 'DRINK',action.action['action'])

    def test_hypothetical_protection_plans_but_never_drinks_or_crosses(self):
        s,p=flight_room();original=copy.deepcopy(s)
        journey=plan_journey(p,s,[],neighbors,probe_kind='flight',plan_only=True)
        self.assertIsNotNone(journey);self.assertEqual(40,journey.route[-1])
        self.assertIsNone(p.room_journey);self.assertFalse(p.room_attempts)
        self.assertEqual(original,s)
        with self.assertRaises(ValueError):plan_journey(p,s,[],neighbors,probe_kind='flight')

    def test_no_wasting_the_floor_candidate_when_reward_route_is_unknown(self):
        s,p=flight_room();p.tiles.pop(39);p.tiles.pop(28);p.tiles.pop(50)
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNone(action);self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)
        self.assertIn('no verified',p.planner.report['potion_reservation']['reason'])

    def test_successful_probe_commits_and_immediately_uses_protected_route(self):
        s,p=flight_room()
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',action.action['action'])
        self.assertIsNotNone(p.room_journey)
        self.assertFalse(s['inventory'][-1]['identified'])
        s['hero']['buffs']=[{'name':'levitating','description':'Turns of levitation remaining: 20.'}]
        p.update(s)
        action=p.escape_special_room(s)
        self.assertEqual('room: follow verified protected route',action.reason)
        self.assertNotEqual(s['hero']['cell'],action.action['cell'])
        self.assertIsNone(p.puzzle_probe)

    def test_wrong_effect_does_not_admit_a_hazard_step(self):
        s,p=flight_room();prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(p.room_journey)
        self.assertIsNone(recover_probe(p,s,[],distance,neighbors))
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        s['inventory'][-1]=potion('silver potion')
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',action.action['action'])

    def test_short_observed_duration_does_not_override_round_trip_budget(self):
        s,p=flight_room();prepare_supplies(p,s,[],distance,neighbors)
        s['hero']['buffs']=[{'name':'levitating','description':'Turns of levitation remaining: 3.'}]
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)

    def test_identification_precedes_route_dependent_drinking(self):
        s,p=flight_room();p.tiles.pop(39)
        s['inventory'].append({'id':'identify','name':'scroll of identify','actions':['READ']})
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('READ',action.action['action']);self.assertFalse(p.puzzle_drinks)


if __name__=='__main__':unittest.main()
