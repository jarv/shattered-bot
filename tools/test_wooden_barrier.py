import copy
import unittest
from unittest.mock import patch
from tools.consumable_tactics import choose_consumable
from tools.test_regular_feedback import arena
from tools.test_consumable_tactics import potion
from tools.test_challenge_rules import verified
from tools.puzzle_supplies import prepare_supplies
from tools.wooden_barrier import recover,known_burn
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Transaction
from tools.challenge_rules import ChallengeRules


def wood_room(rules=None):
    s,_=arena()
    for tile in s['map']['cells']:
        if tile['cell']%9==5:tile['terrain']=4
        if tile['cell']==41:tile['terrain']=13
        if tile['cell']==39:tile['terrain']=29
    s['inventory'].append(potion())
    p=verified(rules);p.update(s)
    return s,p


class WoodenBarrierTests(unittest.TestCase):
    def test_last_flame_is_reserved_from_optional_combat_but_not_emergencies(self):
        for hp,expected in ((20,False),(6,True)):
            s,p=wood_room();s['hero'].update(hp=hp,max_hp=20)
            s['inventory']=[potion('potion of liquid flame')]
            p.tiles[41]['terrain']=27
            foe={'name':'prison guard','cell':43}
            with patch.object(p,'shot_clear',return_value=True),patch.object(p,'target_allowed',return_value=True):
                a=choose_consumable(p,s,[foe],distance,neighbors)
            self.assertEqual(expected,a is not None)
    def test_known_flame_burns_bounded_bookshelf_without_burning_runestone(self):
        s,p=wood_room();p.tiles[41]['terrain']=27
        s['inventory'][-1]=potion('potion of liquid flame')
        s['hero']['cell']=39
        p.loot[42]={'name':'stone of enchantment','top_item':{'name':'stone of enchantment'}}
        a=known_burn(p,s,[])
        self.assertEqual('THROW',a.action['action']);self.assertEqual(41,p.target)
        self.assertEqual('verify-wood',p.wood_burn_plan['phase'])

    def test_bookshelf_burn_preserves_scrolls_allies_and_large_fuel_fields(self):
        for case in ('scroll','ally','fuel'):
            s,p=wood_room();p.tiles[41]['terrain']=27;s['hero']['cell']=39
            s['inventory'][-1]=potion('potion of liquid flame')
            if case=='scroll':p.loot[42]={'name':'scroll of upgrade'}
            if case=='ally':s['objects']=[{'cell':42,'name':'sad ghost'}]
            if case=='fuel':
                for t in p.tiles.values():
                    if t['terrain']==1:t['terrain']=27
            self.assertIsNone(known_burn(p,s,[]),case)
    def test_unknown_candidate_can_be_drunk_beside_wood_with_one_move_to_water(self):
        s,p=wood_room()
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',action.action['action'])
        self.assertEqual('azure potion',action.action['id'])
        self.assertEqual(41,p.wood_burn_plan['wood']);self.assertEqual(39,p.wood_burn_plan['water'])
        self.assertIsNone(p.potion_probe_permit)
        self.assertFalse(s['inventory'][-1]['identified'])

    def test_actual_burning_gets_immediate_committed_water_retreat_then_observed_clearance(self):
        s,p=wood_room();prepare_supplies(p,s,[],distance,neighbors)
        s['hero']['buffs']=[{'name':'burning'}]
        next(t for t in s['map']['cells'] if t['cell']==40)['effects']=['A fire is raging here.']
        p.update(s)
        action=p.choose(s)
        self.assertEqual({'type':'cell','cell':39},action.action)
        self.assertEqual('burning-recovery',action.controller)
        s['hero'].update(cell=39,buffs=[])
        wood=next(t for t in s['map']['cells'] if t['cell']==41)
        wood.update(terrain=20,effects=['A fire is raging here.']);p.update(s)
        self.assertEqual('wait',recover(p,s,[]).action['type'])
        wood['effects']=[];p.update(s)
        self.assertIsNone(recover(p,s,[]));self.assertIsNone(p.wood_burn_plan)
        self.assertIn('Observed wooden barrier removed',p.planner.report['wooden_barrier']['status'])
        self.assertFalse(p.loot_collection_receipts)

    def test_wrong_effect_is_not_inferred_to_be_fire(self):
        s,p=wood_room();prepare_supplies(p,s,[],distance,neighbors)
        s['hero']['buffs']=[{'name':'levitating','description':'Turns remaining: 20.'}]
        self.assertIsNone(recover(p,s,[]));self.assertIsNone(p.wood_burn_plan)
        self.assertEqual(13,p.tiles[41]['terrain'])
        self.assertEqual('flame',p.puzzle_probe['kind'])

    def test_no_experiment_without_observed_water_health_or_collateral_admission(self):
        for case in ('water','health','plant','loot','grass','slow','recent','stack','library','water-bank'):
            s,p=wood_room()
            if case=='water':p.tiles[39]['terrain']=1
            if case=='health':s['hero']['hp']=10
            if case=='plant':
                for c in p.tiles:
                    if p.tiles[c]['terrain']==1:p.tiles[c]['plant']='Firebloom'
            if case=='loot':p.loot[39]={'name':'scroll','top_item':{'name':'scroll'}}
            if case=='grass':p.tiles[39]['terrain']=2
            if case=='slow':s['hero']['buffs']=[{'name':'slowed'}]
            if case=='recent':p.recent_threats[30]={'name':'gnoll scout','cell':30,'observations_ago':1}
            if case=='stack':s['inventory'][-1]['quantity']=2
            if case=='library':p.tiles[41]['terrain']=27
            if case=='water-bank':
                for c in neighbors(41,9,9):
                    if p.tiles[c]['terrain'] in {1,29}:p.tiles[c]['terrain']=29
            action=prepare_supplies(p,s,[],distance,neighbors)
            self.assertTrue(action is None or action.action.get('action')!='DRINK',case)
            self.assertIsNone(p.wood_burn_plan,case)

    def test_known_identification_is_preferred_before_risky_probe(self):
        s,p=wood_room();s['inventory'].append({'id':'identify','name':'scroll of identify','actions':['READ']})
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('READ',action.action['action']);self.assertIsNone(p.wood_burn_plan)

    def test_known_fire_potion_is_reserved_for_throwing_not_blind_drinking(self):
        s,p=wood_room();s['inventory'][-1]=potion('potion of liquid flame')
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))
        self.assertIsNone(p.wood_burn_plan)

    def test_wood_probe_has_the_explicit_scoped_pharmacophobia_permit(self):
        s,p=wood_room(ChallengeRules(pharmacophobia=True))
        self.assertEqual('DRINK',prepare_supplies(p,s,[],distance,neighbors).action['action'])
        self.assertIsNone(p.potion_probe_permit)
        self.assertFalse(p.item_action_allowed(s['inventory'][-1],'DRINK'))

    def test_rejected_probe_proposal_rolls_back_the_entire_plan(self):
        s,p=wood_room();transaction=Transaction(p,p.planner)
        prepare_supplies(p,s,[],distance,neighbors)
        transaction.rollback()
        self.assertIsNone(p.wood_burn_plan);self.assertFalse(p.wood_probe_attempts)
        self.assertFalse(p.puzzle_drinks)

    def test_water_route_is_not_used_after_displacement_or_when_airborne(self):
        for case in ('displaced','airborne','blocked'):
            s,p=wood_room();prepare_supplies(p,s,[],distance,neighbors)
            s['hero']['buffs']=[{'name':'burning'}]
            if case=='displaced':s['hero']['cell']=30
            if case=='airborne':s['hero']['buffs'].append({'name':'levitating'})
            if case=='blocked':p.tiles[39]['plant']='Firebloom'
            self.assertIsNone(recover(p,s,[]),case)
            self.assertIsNone(p.wood_burn_plan)

    def test_falling_to_a_new_floor_clears_floor_local_wood_plan(self):
        s,p=wood_room();prepare_supplies(p,s,[],distance,neighbors)
        p.memory.reset_floor(40)
        self.assertIsNone(p.wood_burn_plan);self.assertFalse(p.wood_probe_attempts)


if __name__=='__main__':unittest.main()
