"""Round 10: persistent potion-room retrieval and energy checks before ingredient inputs."""
import copy
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.test_pool_and_mirror_passage import pool_room
from tools.test_puzzle_supplies import puzzle
from tools.test_shattered_alchemy_optional_inventory import scene,Policy as AlchemyPolicy
from tools.alchemy_tactics import approach_alchemy,alchemy_menu,Brew,rendered_energy,observe_energy,context
from tools.piranha_tactics import choose as pool_choose,pending,observe as observe_pool
from tools.puzzle_supplies import demands,prepare_supplies,MAX_ROOM_POTION_TESTS
from tools.room_tactics import plan_journey,Journey
from tools.policy_geometry import distance,neighbors
from tools.policy_decision import Decision,Intent,GameplayBlocked
from tools.survival_policy import SurvivalPolicy
from tools.pickup_priority import replacements


class PoolSupplyTests(unittest.TestCase):
    def closed_pool(self):
        s,_=arena();width,height=11,9
        s['hero']['cell']=51
        s['inventory'].append(potion('potion of invisibility'))
        cells=[]
        for c in range(width*height):
            x,y=c%width,c//width
            terrain=29 if 2<=x<=4 and 3<=y<=5 else 14 if x==5 and 3<=y<=5 \
                else 5 if c==50 else 1 if 7<=x<=9 and 2<=y<=6 else 4
            if c==46:terrain=11
            cells.append({'cell':c,'terrain':terrain,'visible':True,'observed':True})
        s['map']={'width':width,'height':height,'cells':cells}
        s['objects']=[{'name':'giant piranha','cell':36},{'name':'Chest','cell':46}]
        p=verified();p.update(s)
        return s,p

    def test_pool_objective_and_hazard_survive_fish_leaving_view(self):
        s,p=pool_room(True)
        self.assertIn(41,pending(p))
        after=copy.deepcopy(s);after['objects']=[o for o in after['objects'] if 'piranha' not in o['name']]
        p.update(after)
        self.assertFalse(p.room_actors)
        self.assertIn(41,pending(p))
        self.assertTrue(any(d.kind=='pool' for d in demands(p,after,distance)))
        self.assertIn(41,p.room_blocked)
        action=pool_choose(p,after,[])
        self.assertEqual(action.action.get('action'),'DRINK')

    def test_chest_disappearance_and_drink_are_not_collection_receipts(self):
        s,p=pool_room(True);pool_choose(p,s,[])
        p.loot.clear();p.room_actors.clear();observe_pool(p,s)
        self.assertIn(41,pending(p))
        p.loot_collection_receipts.add(41);observe_pool(p,s)
        self.assertNotIn(41,pending(p))

    def test_hazardous_gold_cannot_consume_the_chests_invisibility_trip(self):
        s,p=pool_room(True)
        p.loot[39]={'cell':39,'name':'gold','top_item':{'name':'gold'}}
        journey=plan_journey(p,s,[],neighbors,probe_kind='pool',plan_only=True)
        self.assertEqual(journey.route[-1],41)

    def test_closed_pool_entrance_is_opened_before_drinking(self):
        s,p=self.closed_pool()
        action=pool_choose(p,s,[])
        self.assertIsNotNone(action)
        self.assertEqual(action.action,{'type':'cell','cell':50})
        self.assertIsNone(p.room_journey)
        after=copy.deepcopy(s)
        next(t for t in after['map']['cells'] if t['cell']==50)['terrain']=6
        p.update(after);action=pool_choose(p,after,[])
        self.assertEqual(action.action.get('action'),'DRINK')
        self.assertEqual(p.room_journey.route[-1],46)
        self.assertIsNone(p.room_journey.advance(p,after,[],neighbors))  # Actual buff still required.

    def test_return_trip_can_reopen_its_known_ordinary_door_with_protection(self):
        s,p=self.closed_pool()
        s['hero'].update(cell=49,buffs=[{'name':'invisible','description':'Turns remaining: 10'}])
        journey=Journey('pool',[51,50,49,48,47,46],s['depth'],stage='return')
        action=journey.advance(p,s,[],neighbors)
        self.assertEqual(action.action,{'type':'cell','cell':50})
        self.assertNotIn(46,p.completed_room_rewards)

    def test_descent_is_not_allowed_with_the_piranha_chest_still_pending(self):
        s,p=pool_room(True)
        decision=Decision({'type':'cell','cell':23},'stairs',intent=Intent.DESCEND)
        with patch.object(SurvivalPolicy,'choose',return_value=decision):
            with self.assertRaisesRegex(GameplayBlocked,'Piranha-room chest'):
                p.choose(s)

    def test_last_reserved_invisibility_is_not_dropped_for_other_loot(self):
        s,p=pool_room(True)
        self.assertFalse(any(i['name']=='potion of invisibility'
                             for i in replacements(p,s,{'name':'ration of food'})))

    def test_more_than_two_distinct_room_candidates_can_be_tested_but_not_retried(self):
        s,p=puzzle()
        p.puzzle_drinks={(s['depth'],'silver potion'),(s['depth'],'azure potion')}
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual(action.action.get('action'),'DRINK')
        self.assertIn((s['depth'],'crimson potion'),p.puzzle_drinks)
        self.assertEqual(MAX_ROOM_POTION_TESTS,12)
        self.assertEqual(s['inventory'][-1]['name'],'crimson potion')  # Identity remains unknown.

    def test_floor_change_resets_pool_obligations(self):
        s,p=pool_room(True)
        after=copy.deepcopy(s);after['depth']+=1;after['objects']=[]
        p.update(after)
        self.assertFalse(pending(p))


class AlchemyMinimumEnergyTests(unittest.TestCase):
    def catalyst(self,energy=None,toolkit=None):
        s,p=arena();s['inventory'].append({'name':'magical catalyst','id':'catalyst','actions':['DROP']})
        p.tiles[41]['terrain']=28
        if toolkit:s['inventory'].append(toolkit)
        p.alchemy_energy=energy
        return s,p

    def kit(self,status='4',equipped=True):
        return {'name':"alchemist's toolkit",'id':'toolkit','status':status,'equipped':equipped,
                'identified':True,'known_cursed':False,'actions':['BREW']}

    def test_known_insufficient_global_energy_does_not_open_pot_or_load_ingredients(self):
        s,p=self.catalyst(7)
        self.assertIsNone(approach_alchemy(p,s))
        self.assertIsNone(p.alchemy_plan)
        self.assertEqual(p.planner.report['alchemy_energy']['required'],8)

    def test_exact_minimum_plus_existing_reserve_allows_pot(self):
        s,p=self.catalyst(8)
        action=approach_alchemy(p,s)
        self.assertEqual(action.action,{'type':'cell','cell':41})
        self.assertEqual(p.alchemy_plan['stage'],'energy')

    def test_ready_toolkit_combines_rendered_charge_with_global_not_a_warmup_percent(self):
        s,p=self.catalyst(4,self.kit('4'))
        action=approach_alchemy(p,s)
        self.assertEqual(action.action,{'type':'item','id':'toolkit','action':'BREW'})
        s,p=self.catalyst(0,self.kit('99%'))
        self.assertIsNone(approach_alchemy(p,s))

    def test_unequipped_toolkit_energy_cannot_fund_station_crafting(self):
        s,p=self.catalyst(2,self.kit('100',equipped=False))
        self.assertIsNone(approach_alchemy(p,s))

    def test_unknown_energy_is_inspected_once_before_any_ingredient_selection(self):
        s,p=self.catalyst()
        self.assertIsNotNone(approach_alchemy(p,s))
        alch=scene('Add item','Back',ui={'energy_text':'Energy: 0','texts':[],
                                      'buttons':[{'id':'add','label':'Add item'},{'id':'back','label':'Back'}]})
        result=alchemy_menu(p,alch)
        self.assertEqual(result.action,{'type':'button','id':'back'})
        self.assertIsNone(p.alchemy_plan)
        self.assertEqual(p.alchemy_energy,0)
        self.assertIsNone(approach_alchemy(p,s))
        self.assertEqual(s['inventory'][-1]['name'],'magical catalyst')

    def test_fresh_menu_energy_is_rechecked_even_if_cached_amount_was_sufficient(self):
        s,p=self.catalyst(8);approach_alchemy(p,s)
        result=alchemy_menu(p,scene('Add item','Back',ui={
            'energy_text':'Energy: 7','texts':[],'buttons':[{'id':'add','label':'Add item'},{'id':'back','label':'Back'}]}))
        self.assertEqual(result.action,{'type':'button','id':'back'})
        self.assertEqual(p.alchemy_energy,7)

    def test_toolkit_gaining_charge_reopens_a_previously_deferred_recipe(self):
        s,p=self.catalyst(0,self.kit('1'))
        self.assertIsNone(approach_alchemy(p,s))
        old=context(s);p.alchemy_attempts.add(old)
        s['inventory'][-1]['status']='8'
        self.assertNotEqual(context(s),old)
        self.assertEqual(approach_alchemy(p,s).action['action'],'BREW')

    def test_possible_energy_pickup_invalidates_cache_without_claiming_an_amount(self):
        s,p=self.catalyst(0)
        before=copy.deepcopy(s)
        before['objects']=[{'cell':41,'name':'energy crystal','top_item':{'name':'energy crystal','quantity':5}}]
        after=copy.deepcopy(s);after['hero']['cell']=41
        p.last_decision=Decision({'type':'cell','cell':41},'pickup')
        p.alchemy_attempts.add(context(s))
        observe_energy(p,before,after)
        self.assertIsNone(p.alchemy_energy);self.assertFalse(p.alchemy_attempts)

    def test_free_seed_recipe_does_not_require_unnecessary_energy(self):
        s,p=arena();p.alchemy_energy=0;p.tiles[41]['terrain']=28
        s['inventory'].append({'name':'seed of icecap','quantity':3})
        self.assertIsNotNone(approach_alchemy(p,s))
        self.assertEqual(p.alchemy_plan['brew'].energy,0)
        self.assertEqual(p.alchemy_plan['stage'],'slot')

    def test_rendered_global_and_toolkit_parts_stay_separate(self):
        self.assertEqual(rendered_energy({'ui':{'energy_text':'Energy: 6+2'}}),(6,2))
        self.assertIsNone(rendered_energy({'ui':{'energy_text':'Energy: ?'}}))

    def test_missing_energy_label_does_not_start_a_paid_recipe(self):
        p=AlchemyPolicy(Brew(('magical catalyst',),'trinket','test',6))
        p.alchemy_plan.update(stage='energy',reserve=2)
        state=scene('Add item','Back');state['ui'].pop('energy_text')
        self.assertEqual(alchemy_menu(p,state),{'type':'button','id':'1'})
        self.assertIsNone(p.alchemy_plan)


if __name__=='__main__':
    unittest.main()
