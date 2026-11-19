import unittest
from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.policy_geometry import distance,neighbors
from tools.hidden_doors import narrow_dead_ends,seek_corridor_end
from tools.puzzle_supplies import prepare_supplies
from tools.puzzle_supplies import revisit_flight_room,demands
from tools.room_tactics import plan_journey
from tools.policy_runtime import Transaction


def short_tip():
    s,p=arena()
    for t in s['map']['cells']:
        if t['cell'] in {30,31,32,39,41}:t['terrain']=4
    p.update(s)
    return s,p


def flight_room(known=False):
    s,_=arena();s['hero']['cell']=16
    s['map']={'width':15,'height':9,'cells':[
        {'cell':c,'terrain':4 if c%15 in {0,14} or c//15 in {0,8} else 0 if 9<=c%15<=12 else 29 if c==67 else 1,
         'visible':c%15<=4,'observed':True} for c in range(135)]}
    s['objects']=[];s['inventory'].append(potion('potion of levitation' if known else 'azure potion'))
    p=verified();p.update(s);p.loot[73]={'name':'Chest','cell':73}
    return s,p


class RequiredTipTests(unittest.TestCase):
    def test_short_one_wide_tip_is_searched_even_hungry_with_generic_budgets_spent(self):
        s,p=short_tip();s['hero']['buffs']=[{'name':'hungry'}]
        p.searches=40;p.corridor_tip_searches=4;p.secret_search_steps=50
        self.assertEqual(40,narrow_dead_ends(p.tiles,9,9)[31])
        self.assertEqual('search',seek_corridor_end(p,s,[],distance).action['type'])
        self.assertIsNone(seek_corridor_end(p,s,[],distance))

    def test_unknown_sides_and_wide_end_are_not_certified_corridor_walls(self):
        for case in ('unknown','wide'):
            s,p=short_tip()
            if case=='unknown':p.tiles.pop(39)
            else:p.tiles[39]['terrain']=1
            self.assertNotIn(31,narrow_dead_ends(p.tiles,9,9),case)

    def test_required_tip_retains_boss_exception_and_threat_safety(self):
        s,p=short_tip();s['depth']=10
        self.assertIsNone(seek_corridor_end(p,s,[],distance))
        s['depth']=5
        self.assertIsNotNone(seek_corridor_end(p,s,[],distance))
        s,p=short_tip();p.recent_threats[49]={'name':'gnoll scout','cell':49}
        self.assertIsNone(seek_corridor_end(p,s,[],distance))

    def test_rejected_search_does_not_mark_wall_searched(self):
        s,p=short_tip();tx=Transaction(p,p.planner);seek_corridor_end(p,s,[],distance);tx.rollback()
        self.assertNotIn(31,p.searched_walls)


class FlightRevisitTests(unittest.TestCase):
    def closed_trap_room(self):
        s,p=flight_room();s['hero']['cell']=67
        for t in s['map']['cells']:
            t['visible']=True
            if t['cell']%15==8:t['terrain']=4
            if t['cell']==68:t['terrain']=5
            if 9<=t['cell']%15<=12:
                t.update(terrain=18,trap='poison dart trap')
        s['objects']=[{'name':'Chest','cell':73}]
        p.update(s)
        return s,p

    def test_open_flight_room_door_before_unknown_potion_test(self):
        s,p=self.closed_trap_room()
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual({'type':'cell','cell':68},a.action)
        self.assertFalse(p.puzzle_drinks);self.assertIsNone(p.room_journey)
        next(t for t in s['map']['cells'] if t['cell']==68)['terrain']=6
        p.update(s)
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action['action'])
        self.assertEqual(73,p.room_journey.route[-1])
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))

    def test_revisit_targets_reward_route_not_nearest_unrelated_hazard(self):
        s,p=self.closed_trap_room();s['hero']['cell']=16
        d=next(d for d in demands(p,s,distance) if d.kind=='flight')
        a=revisit_flight_room(p,s,d,distance)
        self.assertIsNotNone(a)
        j=plan_journey(p,dict(s,hero=dict(s['hero'],cell=p.puzzle_flight_bank)),
                       [],neighbors,probe_kind='flight',plan_only=True)
        self.assertEqual(73,j.route[-1])
        self.assertIn(68,j.route)

    def test_safe_open_doorway_can_test_without_leaving_and_reclosing_it(self):
        s,p=self.closed_trap_room()
        next(t for t in s['map']['cells'] if t['cell']==68)['terrain']=6
        s['hero']['cell']=68;p.update(s)
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action['action'])
        self.assertEqual(68,p.room_journey.route[0])

    def test_unknown_candidate_returns_to_remembered_room_without_drinking(self):
        s,p=flight_room();a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('cell',a.action['type']);self.assertIn('revisit levitation-room',a.reason)
        self.assertFalse(p.puzzle_drinks);self.assertIsNone(p.room_journey)
        self.assertTrue(p.planner.report['puzzle_revisit']['identity_inferred'] is False)

    def test_after_reobservation_unknown_test_requires_planned_round_trip(self):
        s,p=flight_room();s['hero']['cell']=67
        for t in s['map']['cells']:t['visible']=True
        p.update(s);p.loot[73]={'name':'Chest','cell':73}
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action['action']);self.assertEqual('flight',p.room_journey.kind)
        self.assertEqual(73,p.room_journey.route[-1])
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))  # No actual levitation: no crossing.

    def test_known_levitation_is_staged_near_reward_before_consumption(self):
        s,p=flight_room(True);a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('cell',a.action['type']);self.assertIn('stage known levitation',a.reason)
        self.assertIsNone(p.room_journey)

    def test_revisit_budget_and_hazards_prevent_unbounded_or_unsafe_return(self):
        s,p=flight_room();p.puzzle_revisit_steps['flight']=48
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertTrue(a is None or 'revisit levitation-room' not in a.reason)
        s,p=flight_room();p.recent_threats[20]={'name':'gnoll scout','cell':20}
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertTrue(a is None or 'revisit levitation-room' not in a.reason)


if __name__=='__main__':unittest.main()
