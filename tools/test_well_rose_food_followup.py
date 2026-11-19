import copy
import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_combat_items import gear
from tools.test_complete_artifact_utilization import artifact
from tools.well_cleansing import choose as cleanse
from tools.rose_outfitting import choose as outfit,menu,spares
from tools.hungry_cooking import choose as cook
from tools.resource_tactics import choose_well
from tools.inventory_tactics import candidates
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Transaction
from tools.policy_decision import Finished
from tools.challenge_rules import ChallengeRules
from tools.test_challenge_rules import verified


def spare(name='sword',kind='melee',strength=12,damage=3):
    wording='melee weapon deals' if kind=='melee' else 'armor blocks'
    return {'id':name,'name':name,'identified':True,'curse_known':True,'known_cursed':False,
            'description':f'This {wording} 0-{damage*2} damage and requires {strength} strength.',
            'actions':['EQUIP','DROP','THROW']}


class WellCleansingTests(unittest.TestCase):
    def setup_well(self):
        s,p=arena();s['hero'].update(hp=20,max_hp=20,strength=10)
        p.tiles[41].update(terrain=24,visible=True,effects=['Power of health radiates from the water of this well.'])
        item=spare('plate armor','armor',18);item['known_cursed']=True
        s['inventory'].append(item)
        return s,p,item

    def test_overweight_cursed_spare_is_thrown_not_equipped(self):
        s,p,item=self.setup_well();a=choose_well(p,s,[],distance,neighbors)
        self.assertEqual({'type':'item','id':item['id'],'action':'THROW'},a.action)
        self.assertEqual(41,p.target)
        self.assertFalse(item.get('equipped'))

    def test_immediate_healing_starvation_and_equipped_curses_preserve_well(self):
        for mode in ('hurt','starving','equipped'):
            s,p,item=self.setup_well()
            if mode=='hurt':s['hero']['hp']=4
            if mode=='starving':s['hero']['buffs']=[{'name':'starving'}]
            if mode=='equipped':item['equipped']=True
            self.assertIsNone(cleanse(p,s,[]),mode)
            self.assertEqual(41,choose_well(p,s,[],distance,neighbors).action['cell'])

    def test_retrieve_and_verify_public_cleansing_not_throw_alone(self):
        s,p,item=self.setup_well();cleanse(p,s,[])
        s['inventory'].remove(item);item['known_cursed']=False
        s['objects']=[{'cell':41,'name':item['name'],'top_item':item}]
        p.tiles[41].pop('effects')
        self.assertEqual(41,cleanse(p,s,[]).action['cell'])
        s['inventory'].append(item);s['objects']=[]
        self.assertIsNone(cleanse(p,s,[]))
        self.assertTrue(p.planner.report['well_cleansing']['confirmed'])

    def test_missing_item_is_not_rethrown_or_claimed(self):
        s,p,item=self.setup_well();cleanse(p,s,[]);s['inventory'].remove(item)
        self.assertIsNone(cleanse(p,s,[]));self.assertIsNone(p.well_cleanse_plan)
        self.assertNotIn('well_cleansing',p.planner.report)

    def test_unknown_or_safe_spares_and_active_threats_do_not_spend_well(self):
        s,p,item=self.setup_well();item['known_cursed']=False
        self.assertIsNone(cleanse(p,s,[]))
        item['known_cursed']=True
        self.assertIsNone(cleanse(p,s,[{'cell':42,'name':'gnoll scout'}]))

    def test_rejected_well_proposal_rolls_back_plan_and_attempts(self):
        s,p,item=self.setup_well();tx=Transaction(p,p.planner);cleanse(p,s,[]);tx.rollback()
        self.assertIsNone(p.well_cleanse_plan);self.assertFalse(p.well_cleanse_attempts)


class RoseOutfitTests(unittest.TestCase):
    def setup_rose(self):
        s,p=arena();s['inventory'].append(artifact('dried rose',['OUTFIT','DIRECT']))
        item=spare();s['inventory'].append(item)
        return s,p,item

    def slots(self,s,weapon='Empty weapon slot',armor='Empty armor slot',strength=13):
        s['modal']=True
        s['ui']={'texts':["Ghost's Equipment",f'The ghost can currently equip items requiring up to _{strength} strength._'],
                 'buttons':[{'id':'weapon','label':weapon},{'id':'armor','label':armor}]}

    def test_fill_empty_slot_verify_transfer_and_never_click_occupied_slot(self):
        s,p,item=self.setup_rose();self.assertEqual('OUTFIT',outfit(p,s,[]).action['action'])
        plan=p.artifact_menu;self.slots(s)
        self.assertEqual('weapon',menu(p,s,plan).action['id'])
        s['ui']={'texts':['Select a weapon'],'buttons':[{'id':'spare','label':item['name']}]}
        self.assertEqual('spare',menu(p,s,plan).action['id'])
        s['inventory'].remove(item);self.slots(s,weapon=item['name'])
        self.assertEqual('back',menu(p,s,plan).action['type'])
        self.assertTrue(p.planner.report['rose_outfit']['confirmed'])

    def test_unknown_cursed_equipped_overstrong_and_unique_gear_protected(self):
        for change in ({'identified':False},{'curse_known':False},{'known_cursed':True},{'equipped':True},
                       {'description':'A unique weapon.'}):
            s,p,item=self.setup_rose();item.update(change)
            self.assertNotIn(item,spares(s,13),str(change))
        s,p,item=self.setup_rose();self.assertNotIn(item,spares(s,10))

    def test_occupied_ghost_slots_not_removed(self):
        s,p,item=self.setup_rose();outfit(p,s,[]);self.slots(s,weapon='old sword',armor='old armor')
        self.assertEqual('back',menu(p,s,p.artifact_menu).action['type'])

    def test_missing_strength_ui_stops_without_positional_guess(self):
        s,p,item=self.setup_rose();outfit(p,s,[]);s['ui']={'buttons':[],'texts':["Ghost's Equipment"]}
        with self.assertRaises(Finished):menu(p,s,p.artifact_menu)

    def test_duplicate_names_and_hero_upgrades_not_transferred(self):
        s,p,item=self.setup_rose();s['inventory'].append(copy.deepcopy(item))
        self.assertNotIn(item,spares(s))
        armor=spare('plate armor','armor',18,10);s['inventory'].append(armor)
        self.assertNotIn(armor,spares(s))

    def test_eligible_spare_armor_reserved_from_sale(self):
        s,p,item=self.setup_rose()
        # Install a strictly stronger known armor before testing spare disposal.
        current=spare('scale armor','armor',12,8);current['equipped']=True
        s['inventory']=[i for i in s['inventory'] if 'armor' not in i['name']]
        old=spare('leather armor','armor',12,3)
        s['inventory'] += [current,old]
        self.assertIn(old,spares(s))
        self.assertNotIn(old,candidates(p,s,'DROP'))


class HungryCookingTests(unittest.TestCase):
    def setup_food(self):
        s,p=arena();s['hero']['buffs']=[{'name':'hungry'}]
        s['inventory'] += [{'id':'meat','name':'mystery meat','actions':['THROW','EAT']},
                           {'id':'ice','name':'seed of icecap','actions':['THROW']},
                           {'id':'fire','name':'seed of firebloom','actions':['THROW']}]
        return s,p

    def test_icecap_first_then_observed_meat_trigger_recovery_and_eat(self):
        s,p=self.setup_food();a=cook(p,s,[]);self.assertEqual('ice',a.action['id']);cell=p.target
        p.tiles[cell]['plant']='Icecap'
        a=cook(p,s,[]);self.assertEqual('meat',a.action['id'])
        p.tiles[cell].pop('plant');p.tiles[cell]['effects']=['Unnaturally frigid air.']
        self.assertEqual('wait',cook(p,s,[]).action['type'])
        p.tiles[cell].pop('effects')
        cooked={'id':'cooked','name':'frozen carpaccio','actions':['EAT']}
        s['objects']=[{'cell':cell,'name':'frozen carpaccio','top_item':cooked}]
        self.assertIn('collect observed',cook(p,s,[]).reason)
        s['inventory'].append(cooked)
        self.assertEqual({'type':'item','id':'cooked','action':'EAT'},cook(p,s,[]).action)

    def test_fire_fallback_when_no_ice_and_no_flammable_collateral(self):
        s,p=self.setup_food();s['inventory']=[i for i in s['inventory'] if i['id']!='ice']
        self.assertEqual('fire',cook(p,s,[]).action['id'])
        s,p=self.setup_food();s['inventory']=[i for i in s['inventory'] if i['id']!='ice']
        for t in p.tiles.values():
            if t['terrain']==1:t['terrain']=2
        self.assertIsNone(cook(p,s,[]))

    def test_no_forced_cooking_when_not_hungry_threatened_or_barren(self):
        s,p=self.setup_food();s['hero']['buffs']=[]
        self.assertIsNone(cook(p,s,[]))
        s,p=self.setup_food();self.assertIsNone(cook(p,s,[{'name':'rat','cell':41}]))
        s,_=self.setup_food();p=verified(ChallengeRules(barren_land=True));p.update(s)
        self.assertIsNone(cook(p,s,[]))

    def test_unconfirmed_seed_does_not_get_replanted(self):
        s,p=self.setup_food();cook(p,s,[])
        self.assertIsNone(cook(p,s,[]));self.assertIsNone(p.hungry_cooking_plan)


if __name__=='__main__':unittest.main()
