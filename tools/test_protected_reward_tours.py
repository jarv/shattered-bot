"""Synthetic public observations and accepted-action receipts, not live replay."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.policy_geometry import neighbors,distance
from tools.policy_decision import Finished
from tools.room_tactics import Journey,plan_journey
from tools.protected_rewards import gas_plan,RewardTrip,observe,tour,paths
from tools.piranha_profile import observe as profile,scout,survey_plan
from tools.puzzle_supplies import demands,prepare_supplies
from tools.loot_completion import observe_collected


def gas_room():
    s,_=arena();s['hero']['cell']=38
    for t in s['map']['cells']:
        t['terrain']=4
        if 4<=t['cell']%9<=7 and 2<=t['cell']//9<=6:
            t.update(terrain=1,effects=['A cloud of toxic gas swirls here.'])
    for c,t in ((38,1),(39,6),(50,25),(41,19)):
        tile=next(t for t in s['map']['cells'] if t['cell']==c)
        tile['terrain']=t
        if c in {38,39}:tile['effects']=[]
        if c==41:tile.update(name='toxic vent',trap='toxic vent')
    s['objects']=[{'cell':31,'name':'Chest'},{'cell':32,'name':'Chest'},
                  {'cell':40,'name':'Skeletal remains'}]
    s['inventory'].append(potion('potion of purity'))
    p=verified();p.update(s)
    return s,p


def pool_room():
    s,_=arena();s['hero']['cell']=38
    for t in s['map']['cells']:
        c=t['cell'];t['terrain']=4
        if 4<=c%9<=7 and 2<=c//9<=6:t['terrain']=14 if c%9==4 else 29
    for c,t in ((29,1),(37,1),(38,1),(39,6),(47,1)):
        next(tile for tile in s['map']['cells'] if tile['cell']==c)['terrain']=t
    # Unseen lower water/reward area: it is not silently filled in.
    s['map']['cells']=[t for t in s['map']['cells'] if t['cell'] not in {51,52,60,61}]
    s['objects']=[{'cell':33,'name':'giant piranha','sleeping':True}]
    s['inventory'].append(potion('jade potion'))
    p=verified();p.update(s)
    return s,p


class GasTourTests(unittest.TestCase):
    def trip(self,s,p):
        j=gas_plan(p,s,Journey('gas',[38,39,40,31],s['depth']))
        self.assertIsInstance(j,RewardTrip)
        p.room_journey=j
        return j

    def test_three_heap_tour_includes_skull_and_independent_return(self):
        s,p=gas_room();j=self.trip(s,p)
        self.assertEqual({31,32,40},set(j.targets))
        self.assertEqual(3,j.planned_count)
        self.assertLessEqual(j.cost,20)
        self.assertIsNone(j.advance(p,s,[],neighbors))  # A proposal is not purity.
        self.assertFalse(p.completed_room_rewards)

    def test_accepted_open_pickup_sequence_sweeps_all_three_and_returns(self):
        s,p=gas_room();j=self.trip(s,p)
        duration=20
        s['hero']['buffs']=[{'name':'purification barrier','description':f'Turns of immunity remaining: {duration}.'}]
        collected=set()
        for _ in range(40):
            d=j.advance(p,s,[],neighbors)
            if d is None:break
            before=copy.deepcopy(s);c=d.action['cell']
            obj=next((o for o in s['objects'] if o['cell']==c),None)
            if obj and not obj.get('top_item'):
                obj.update(name='gold x10',top_item={'name':'gold','quantity':10})
                spent=1
            else:
                s['hero']['cell']=c;spent=1
                if obj:
                    s['objects'].remove(obj);s['hero']['gold']=s['hero'].get('gold',0)+10
                    collected.add(c);spent+=1
            duration-=spent
            s['hero']['buffs'][0]['description']=f'Turns of immunity remaining: {duration}.'
            p.last_decision=d
            observe_collected(p,before,d,s)
            p.update(s)
        self.assertIsNone(p.room_journey)
        self.assertEqual({31,32,40},collected)
        self.assertEqual(38,s['hero']['cell'])
        self.assertEqual({31,32,40},j.collected)
        self.assertEqual({31,32,40},{c for depth,kind,c in p.completed_room_rewards if kind=='gas'})
        self.assertGreaterEqual(duration,3)

    def test_shortened_buff_aborts_loot_but_keeps_return(self):
        s,p=gas_room();j=self.trip(s,p)
        s['hero'].update(cell=40,buffs=[{'name':'purification barrier','description':'Turns remaining: 6.'}])
        d=j.advance(p,s,[],neighbors)
        self.assertEqual('return',j.stage)
        self.assertIn(d.action['cell'],{38,39})
        self.assertFalse(j.collected)

    def test_removal_without_pickup_receipt_never_credits_collection(self):
        s,p=gas_room();j=self.trip(s,p)
        s['objects']=[];p.loot.clear()
        s['hero']['buffs']=[{'name':'purification barrier','description':'Turns remaining: 20.'}]
        self.assertIsNone(j.advance(p,s,[],neighbors))
        self.assertFalse(p.completed_room_rewards)

    def test_blocked_or_expired_return_is_explicit_not_an_unprotected_step(self):
        for case in ('blocked','expired','branch'):
            s,p=gas_room();j=self.trip(s,p)
            s['hero'].update(cell=31,buffs=[{'name':'purification barrier','description':'Turns remaining: 20.'}])
            if case=='expired':s['hero']['buffs']=[]
            if case=='blocked':p.tiles[39]['terrain']=4
            if case=='branch':s['branch']=1
            with self.assertRaises(Finished):j.advance(p,s,[],neighbors)

    def test_unknown_other_hazard_and_suspicious_heap_are_not_tour_targets(self):
        s,p=gas_room();p.loot[32]['description']='It feels off. Opening it is a bad idea.'
        j=self.trip(s,p)
        self.assertNotIn(32,j.targets)
        p.tiles[39]['effects']=['A fire is raging here.']
        self.assertNotIn(31,paths(p,s,38,'gas',j.room|set(j.route)))

    def test_skeletal_heap_keeps_existing_hunger_and_charge_readiness(self):
        for case in ('hungry','charges'):
            s,p=gas_room()
            if case=='hungry':s['hero']['buffs']=[{'name':'hungry'}]
            else:s['inventory'][0]['status']='1/4'
            j=self.trip(s,p)
            self.assertNotIn(40,j.targets)

    def test_recognized_room_with_one_visible_heap_can_add_later_rewards(self):
        s,p=gas_room()
        p.loot={31:p.loot[31]}
        j=self.trip(s,p)
        self.assertEqual([31],j.targets)
        p.loot[32]={'name':'Chest'}
        s['hero']['buffs']=[{'name':'purification barrier','description':'Turns remaining: 20.'}]
        self.assertIsNotNone(j.advance(p,s,[],neighbors))
        self.assertEqual({31,32},set(j.targets))


class PiranhaProfileTests(unittest.TestCase):
    def test_first_fish_recognizes_profile_without_chest_or_three_fish(self):
        s,p=pool_room()
        self.assertFalse(p.piranha_rooms)
        h=next(iter(p.piranha_habitats.values()))
        self.assertEqual('pool',h['profile'])
        self.assertIn('pool',[d.kind for d in demands(p,s,distance)])
        self.assertIsInstance(survey_plan(p,s),RewardTrip)

    def test_central_aquarium_is_not_a_treasure_pool(self):
        s,p=arena()
        for c in (30,31,39,40):p.tiles[c]['terrain']=29
        s['objects']=[{'cell':30,'name':'giant piranha'}]
        p.room_actors={30:s['objects'][0]}
        profile(p,s)
        self.assertEqual('aquarium',next(iter(p.piranha_habitats.values()))['profile'])
        self.assertNotIn('pool',[d.kind for d in demands(p,s,distance)])
        self.assertIsNone(survey_plan(p,s))

    def test_incomplete_profile_does_not_invent_a_room_or_drink(self):
        s,p=pool_room()
        for t in p.tiles.values():
            if t['terrain']==14:t['terrain']=1
        profile(p,s)
        self.assertEqual('candidate',next(iter(p.piranha_habitats.values()))['profile'])
        self.assertIsNone(survey_plan(p,s))
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertTrue(a is None or a.action.get('action')!='DRINK')

    def test_survey_requires_actual_invisibility_and_preserves_unknown_geometry(self):
        s,p=pool_room();before=copy.deepcopy(p.tiles)
        j=survey_plan(p,s);self.assertIsNotNone(j)
        self.assertEqual('pool',j.kind)
        self.assertTrue(j.survey);self.assertFalse(j.targets)
        self.assertTrue(all(c in before for c in j.route))
        p.room_journey=j
        self.assertIsNone(j.advance(p,s,[],neighbors))
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(next(iter(p.piranha_habitats.values()))['surveyed'])

    def test_unknown_test_is_admitted_before_chest_discovery_but_not_protection(self):
        s,p=pool_room()
        a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action.get('action'))
        self.assertIsInstance(p.room_journey,RewardTrip)
        self.assertTrue(p.room_journey.survey)
        self.assertFalse(p.room_journey.targets)
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))

    def test_protected_survey_retargets_a_newly_observed_chest(self):
        s,p=pool_room();j=survey_plan(p,s);p.room_journey=j
        s['hero'].update(cell=j.route[2],buffs=[{'name':'invisible','description':'Turns remaining: 18.'}])
        p.loot[42]={'name':'Chest'}
        d=j.advance(p,s,[],neighbors)
        self.assertIn(42,j.targets)
        self.assertEqual('outbound',j.stage)
        self.assertFalse(j.collected)
        self.assertNotIn(d.action.get('cell'),{o['cell'] for o in s['objects']})

    def test_survey_cannot_cross_without_buff_and_habitat_shore_never_becomes_test_bank(self):
        from tools.puzzle_supplies import safe_test_bank
        s,p=pool_room()
        self.assertFalse(safe_test_bank(p,s,40,distance,neighbors,allow_dry=True,pool_bank=True))
        j=survey_plan(p,s);p.room_journey=j
        s['hero']['cell']=j.route[2]
        with self.assertRaises(Finished):j.advance(p,s,[],neighbors)

    def test_unknown_survey_test_retains_near_full_health_gate(self):
        s,p=pool_room();s['hero']['hp']=int(.9*s['hero']['max_hp'])
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertTrue(d is None or d.action.get('action')!='DRINK')

    def test_scout_budget_and_floor_reset(self):
        s,p=pool_room()
        for t in p.tiles.values():
            if t['terrain']==14:t['terrain']=1
        profile(p,s)
        h=next(iter(p.piranha_habitats.values()));h['scout_steps']=48
        self.assertIsNone(scout(p,s))
        p.memory.reset_floor(38)
        self.assertFalse(p.piranha_habitats)


if __name__=='__main__':
    unittest.main()
