import copy
import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_combat_items import gear
from tools.test_well_rose_food_followup import spare
from tools.test_challenge_rules import verified
from tools.test_challenge_systems import ready
from tools.test_consumable_tactics import potion
from tools.mapping_knowledge import observe,complete
from tools.hidden_doors import secret_search_allowed,seek_required_corridor_tip
from tools.policy_decision import Intent,Finished
from tools.policy_geometry import distance,neighbors
from tools.trap_field_tactics import before_move
from tools.priority_resources import choose as pickup,targets
from tools.inventory_tactics import redundant,candidates,choose as cleanup,sale_menu
from tools.puzzle_supplies import prepare_supplies,stage_sentry
from tools.room_loot import before_room_exit


class MappingReceiptTests(unittest.TestCase):
    def test_accepted_named_mapping_consumption_disables_searches_only_on_that_floor(self):
        s,p=arena();scroll={'id':'map','name':'scroll of magic mapping','quantity':1}
        s['inventory'].append(scroll);after=copy.deepcopy(s);after['inventory'].remove(scroll)
        a=p.decision({'type':'item','id':'map','action':'READ'},'test')
        self.assertTrue(observe(p,s,a,after)['full_mapping_confirmed'])
        self.assertFalse(secret_search_allowed(s,p))
        self.assertIsNone(seek_required_corridor_tip(p,s,[],distance))
        self.assertTrue(secret_search_allowed(dict(s,depth=s['depth']+1),p))
        self.assertTrue(secret_search_allowed(dict(s,branch=1),p) is False)  # Existing boss/branch restriction remains.
        p.memory.reset_floor(40)
        self.assertTrue(complete(p,s))

    def test_proposal_no_consumption_or_partial_clairvoyance_is_not_full_mapping(self):
        s,p=arena();s['inventory'].append({'id':'map','name':'scroll of magic mapping'})
        a=p.decision({'type':'item','id':'map','action':'READ'},'test')
        self.assertIsNone(observe(p,s,a,copy.deepcopy(s)))
        a=p.decision({'type':'cell','cell':40},'stone of clairvoyance')
        after=copy.deepcopy(s);after['map']['cells'][0]['mapped']=True
        self.assertIsNone(observe(p,s,a,after));self.assertFalse(complete(p,s))

    def test_fresh_public_layout_effect_can_confirm_spellbook_mapping(self):
        s,p=arena();after=copy.deepcopy(s)
        after['ui']['texts'].append('You are now aware of the level layout.')
        a=p.decision({'type':'item','id':'book','action':'READ'},'spellbook')
        self.assertTrue(observe(p,s,a,after)['public_layout_message'])
        self.assertIsNone(observe(p,after,a,copy.deepcopy(after)))

    def test_mapped_trap_field_does_not_spend_search_or_scry(self):
        s,p=arena();p.mapped_floors.add((s['depth'],s.get('branch',0)))
        for c in (42,43,44):p.tiles[c].update(terrain=18,trap='poison dart trap')
        self.assertIsNone(before_move(p,s,p.cell(41,'explore',intent=Intent.EXPLORE),[]))
        self.assertIsNone(p.trap_scan_pending)


class DuplicateSaleTests(unittest.TestCase):
    def setup_duplicates(self):
        s,p=arena();one=spare('sword');two=copy.deepcopy(one);two['id']='sword2'
        s['inventory'] += [one,two]
        return s,p,one,two

    def test_identical_safe_equipment_copies_are_redundant_but_last_copy_is_not(self):
        s,p,one,two=self.setup_duplicates()
        self.assertTrue(redundant(s,one));self.assertIn(one,candidates(p,s,'DROP'))
        s['inventory'].remove(two)
        self.assertFalse(redundant(s,one));self.assertNotIn(one,candidates(p,s,'DROP'))

    def test_equipped_unknown_cursed_incomparable_and_utility_duplicates_preserved(self):
        for changes in ({'equipped':True},{'identified':False},{'known_cursed':True},
                        {'description':'A unique quest weapon.'},{'description':'An enchanted blade.'}):
            s,p,one,two=self.setup_duplicates();two.update(changes)
            self.assertFalse(redundant(s,one),str(changes))

    def test_identical_duplicate_selector_can_sell_one_without_guessing_between_distinct_items(self):
        s,p,one,two=self.setup_duplicates();s['objects']=[{'name':'shopkeeper','cell':41}]
        cleanup(p,s,[])
        self.assertTrue(p.sell_plan['interchangeable'])
        p.sell_plan['stage']='select'
        s['modal']=True
        s['ui']={'texts':['Sell an item'],'buttons':[{'id':'one','label':'sword'},{'id':'two','label':'sword'}]}
        self.assertEqual('one',sale_menu(p,s).action['id'])
        self.assertEqual('quote',p.sell_plan['stage'])

    def test_consumable_duplicates_are_not_treated_as_disposable_equipment(self):
        s,p=arena()
        for name in ('potion of healing','scroll of upgrade','seed of icecap','stone of blink'):
            item={'id':name,'name':name,'identified':True,'curse_known':True,'quantity':3,'actions':['DROP']}
            s['inventory'] += [item,dict(item)]
            self.assertFalse(redundant(s,item))


class PriorityPickupTests(unittest.TestCase):
    def test_progression_pickup_preempts_other_loot_and_is_not_reordered_into_tour(self):
        s,p=arena();p.loot[41]={'name':'gold','top_item':{'name':'gold'}}
        p.loot[42]={'name':'scroll of upgrade','top_item':{'name':'scroll of upgrade'}}
        a=pickup(p,s,[])
        self.assertIn('prioritize observed permanent',a.reason)
        self.assertIsNone(before_room_exit(p,s,a))

    def test_named_strength_is_priority_but_color_hypothesis_and_shop_stock_are_not(self):
        s,p=arena()
        p.loot[41]={'name':'jade potion','top_item':{'name':'jade potion'}}
        p.loot[42]={'name':'potion of strength','for_sale':True}
        self.assertFalse(targets(p))
        p.loot[42].pop('for_sale')
        self.assertEqual({42},set(targets(p)))

    def test_pickup_never_crosses_traps_or_ignores_active_threats(self):
        s,p=arena();p.loot[41]={'name':'potion of strength'}
        self.assertIsNone(pickup(p,s,[{'name':'rat','cell':42}]))
        p.tiles[41].update(terrain=18,trap='poison dart trap')
        self.assertIsNone(pickup(p,s,[]))

    def test_descent_with_observed_priority_resource_is_blocked(self):
        s,p=arena();p.loot[42]={'name':'scroll of upgrade'}
        a=p.cell(41,'test: descend',intent=Intent.DESCEND)
        with patch('tools.survival_policy.SurvivalPolicy.choose',return_value=a), \
                patch('tools.mage_policy.before_room_exit',return_value=None):
            with self.assertRaises(Finished):p.choose(s)


def sentry_room(known=False):
    s,_=ready()
    for tile in s['map']['cells']:
        x,y=tile['cell']%7,tile['cell']//7
        tile['terrain']=4 if x in {0,6} or y in {0,6} else 14
        if x in {1,2} and 1<=y<=5 and y!=3:tile['terrain']=1
        if tile['cell']==7:tile['terrain']=6
        if tile['cell'] in {22,23,24}:tile['terrain']=25
        if tile['cell'] in {26,29}:tile['terrain']=11
    s['hero']['cell']=15
    s['objects']=[{'name':'red sentry','cell':26},{'name':'chest','cell':29}]
    s['inventory'].append(potion('potion of haste' if known else 'azure potion'))
    p=verified();p.update(s)
    return s,p


class SentryPreparationTests(unittest.TestCase):
    def test_known_haste_is_staged_and_real_buff_still_required(self):
        s,p=sentry_room(True);a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(a)
        if a.action['type']=='cell':
            s['hero']['cell']=p.puzzle_sentry_bank;p.update(s)
            a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action['action']);self.assertEqual('sentry',p.room_journey.kind)
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))

    def test_unknown_haste_test_uses_white_entrance_not_carpet(self):
        s,p=sentry_room();a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(a)
        for _ in range(8):
            if a.action['type']!='cell':break
            s['hero']['cell']=a.action['cell'];p.update(s)
            a=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',a.action['action'])
        self.assertNotEqual(14,p.tiles[s['hero']['cell']]['terrain'])
        self.assertEqual('sentry',p.room_journey.kind)
        self.assertEqual(29,p.room_journey.route[-1])

    def test_incomplete_geometry_or_recent_threat_prevents_haste_commitment(self):
        s,p=sentry_room();p.tiles.pop(0)
        self.assertIsNone(stage_sentry(p,s,neighbors))
        s,p=sentry_room();p.recent_threats[15]={'name':'rat','cell':15}
        self.assertIsNone(stage_sentry(p,s,neighbors))


if __name__=='__main__':unittest.main()
