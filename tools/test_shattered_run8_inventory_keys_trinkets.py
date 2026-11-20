"""Run 8 feedback: observation-only selectors, not a replay or success claim."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.test_inventory_trap_artifact_feedback import weapon
from tools.policy_decision import Decision, Intent
from tools.policy_geometry import neighbors
from tools.policy_runtime import Transaction
from tools import inventory_tactics as inventory
from tools import pickup_priority as priority
from tools.priority_resources import choose as pickup, targets
from tools.room_loot import before_room_exit
from tools.loot_completion import required_loot
from tools.room_tactics import crystal_choice, prepare_containers
from tools.tactical_recovery import locked_room_route
from tools.keyed_rooms import observe as observe_keys, record_spend
from tools.alchemy_tactics import plan_brew, Brew, alchemy_menu, inventory_baseline
from tools.trinket_tactics import TRINKETS
from tools.test_shattered_alchemy_optional_inventory import Policy as AlchemyPolicy, scene


def item(name, **fields):
    return dict({'name': name, 'id': name, 'description': '', 'quantity': 1,
                 'actions': ['DROP'], 'identified': True}, **fields)


def armor(name, low, high, strength, **fields):
    return item(name, description=f'This tier-2 armor blocks {low}-{high} damage and requires {strength} strength',
                **fields)


def refused(s, p, incoming):
    s['objects'] = [{'cell': s['hero']['cell'], 'name': incoming['name'], 'top_item': incoming}]
    after = copy.deepcopy(s)
    after['ui']['texts'].append(f"You can't carry: {priority.base_name(incoming)}.")
    action = Decision({'type': 'cell', 'cell': s['hero']['cell']}, 'pickup', Intent.LOOT)
    inventory.observe_accepted(p,s,action,after)
    p.loot = {o['cell']: o for o in after['objects']}
    return after


class PickupRankingTests(unittest.TestCase):
    def test_user_tiers_and_missing_categories(self):
        s,p=arena()
        cases=[('potion of strength',0),('scroll of upgrade',0),('ration of food',0),('mystery meat',0),
               ('ankh',0),('wand of frost',1),('ring of might',1),('scroll of identify',1),
               ('azure potion',1),('arcane stylus',1),('stone of blink',1),
               ('dried rose',1),('petrified seed',1),('seed of earthroot',3),
               ('magical catalyst',3),('alchemical catalyst',3),('arcane resin',3),
               ('liquid metal',3),('bomb',4),('honeypot',4)]
        for n,tier in cases:
            self.assertEqual(priority.rank(s,item(n)),tier,n)
        thrown=item('bolas',description='This thrown weapons deals 4-9 damage and requires 13 strength')
        self.assertEqual(priority.rank(s,thrown),2)

    def test_keys_utilities_bags_equipped_quest_and_staff_are_protected(self):
        s,p=arena()
        for n in priority.BAGS | priority.ESSENTIAL | {'iron key', 'Crystal key', 'staff of magic missile +4'}:
            self.assertIsNone(priority.rank(s,item(n)),n)
        self.assertIsNone(priority.rank(s,item('wand of frost',equipped=True)))
        self.assertIsNone(priority.rank(s,item('unknown relic',description='This is a quest item.')))

    def test_upgraded_gear_is_not_dropped_just_because_base_tier_is_lower(self):
        s,p=arena()
        current=armor('leather armor',0,4,12,equipped=True)
        improved=armor('cloth armor +4',0,10,8)
        weak=armor('cloth armor',0,2,10)
        future=armor('plate armor',0,10,18)
        lighter=armor('cloth armor +1',0,2,8)
        s['inventory']=[current,improved,weak,future,lighter]
        self.assertEqual(priority.rank(s,weak),6)
        self.assertEqual(priority.rank(s,improved),1)
        self.assertEqual(priority.rank(s,future),1)
        self.assertEqual(priority.rank(s,lighter),6)  # Both are usable; protection is lower.
        current['description']='This armor blocks 0-4 damage and requires 14 strength'
        self.assertEqual(priority.rank(s,weak),1)  # Never rely on unusable equipped gear.

    def test_duplicate_retains_one_copy_and_different_upgrade_is_not_duplicate(self):
        s,p=arena()
        first=weapon('dirk',identified=False)
        second=dict(first,id='second')
        upgraded=weapon('dirk +2',5,10)
        s['inventory']=[first,second,upgraded]
        self.assertEqual(priority.rank(s,second),5)
        self.assertEqual(priority.rank(s,upgraded),1)
        s['inventory'].remove(first)
        self.assertEqual(priority.rank(s,second),1)

    def test_cursed_is_a_within_tier_tiebreak_not_a_cross_tier_override(self):
        s,p=arena()
        cursed=item('azure potion',known_cursed=True)
        clean=item('amber potion')
        junk=item('bomb')
        s['inventory']=[clean,cursed,junk]
        self.assertEqual(priority.replacements(p,s,item('ration of food')),[junk,cursed,clean])
        self.assertEqual(priority.replacements(p,s,item('seed of earthroot')),[junk])

    def test_bag_specific_relief_never_drops_pouch_seeds_for_backpack_food(self):
        s,p=arena()
        seed=item('seed of blindweed')
        bomb=item('bomb')
        s['inventory']=[item('velvet pouch'),seed,bomb]
        self.assertEqual(priority.replacements(p,s,item('ration of food')),[bomb])
        self.assertEqual(priority.bag(s,seed),'velvet pouch')
        self.assertEqual(priority.bag(s,item('magical catalyst')),'backpack')
        s['inventory'] += [item('potion bandolier'),item('scroll holder'),item('magical holster')]
        self.assertEqual(priority.bag(s,item('rainbow potion')),'backpack')
        self.assertEqual(priority.bag(s,item('arcane stylus')),'scroll holder')
        self.assertEqual(priority.bag(s,item('arcane resin')),'scroll holder')
        self.assertEqual(priority.bag(s,item('liquid metal')),'potion bandolier')
        self.assertEqual(priority.bag(s,item('wand of frost')),'magical holster')

    def test_no_same_or_higher_tier_discard(self):
        s,p=arena()
        s['inventory']=[item('ration of food'),item('potion of strength'),item('ankh')]
        self.assertEqual(priority.replacements(p,s,item('scroll of upgrade')),[])

    def test_run8_food_displaces_known_weaker_armor_before_bombs_or_valuable_wands(self):
        s,p=arena()
        s['inventory']=[armor('leather armor of obfuscation',0,4,12,equipped=True),
                        armor('cloth armor',0,2,10),item('bomb x3',quantity=3),item('wand of warding')]
        s=refused(s,p,item('ration of food'))
        action=pickup(p,s,[])
        self.assertEqual(action.action['type'],'cell')  # First leave the food's square.
        s['hero']['cell']=action.action['cell']
        action=pickup(p,s,[])
        self.assertEqual(action.action,{'type':'item','id':'cloth armor','action':'DROP'})
        self.assertIn(40,required_loot(p))  # Disposal is not a food pickup receipt.

    def test_stack_drop_requires_whole_stack_receipt_and_suppresses_repickup(self):
        s,p=arena()
        bomb=item('bomb x3',quantity=3)
        s['inventory']=[bomb]
        s=refused(s,p,item('ration of food'))
        s['hero']['cell']=41
        action=inventory.choose(p,s,[])
        after=copy.deepcopy(s);after['inventory']=[]
        after['objects']=[{'cell':41,'name':bomb['name'],'top_item':bomb}]
        receipts=inventory.observe_accepted(p,s,action,after)
        self.assertEqual(receipts[0]['quantity'],3)
        self.assertTrue(inventory.discarded(p,41,after['objects'][0]))
        self.assertIsNone(p.inventory_pressure)

    def test_unverified_drop_does_not_claim_receipt_or_retry(self):
        s,p=arena();s['inventory']=[item('bomb')]
        s=refused(s,p,item('ration of food'));s['hero']['cell']=41
        action=inventory.choose(p,s,[])
        events=inventory.observe_accepted(p,s,action,copy.deepcopy(s))
        self.assertEqual(events[0]['kind'],'discard-unverified')
        self.assertFalse(p.intentional_discards)
        self.assertIsNone(inventory.choose(p,s,[]))
        s=refused(s,p,item('ration of food'))
        self.assertIsNone(inventory.choose(p,s,[]))  # Same unchanged item is not dropped again.

    def test_food_is_a_priority_target_and_room_tour_does_not_override_it(self):
        s,p=arena()
        ration={'cell':42,'name':'ration of food','top_item':item('ration of food')}
        p.loot={42:ration,41:{'cell':41,'name':'bomb','top_item':item('bomb')}}
        self.assertIn(42,targets(p))
        action=pickup(p,s,[])
        self.assertIn('food pickup',action.reason)
        self.assertIsNone(before_room_exit(p,s,action))
        p.recent_threats={45:{'name':'gnoll scout','cell':45}}
        self.assertIsNone(pickup(p,s,[]))

    def test_transaction_rolls_back_pending_drop_and_pressure(self):
        s,p=arena();s['inventory']=[item('bomb')]
        s=refused(s,p,item('ration of food'));s['hero']['cell']=41
        tx=Transaction(p)
        inventory.choose(p,s,[])
        tx.rollback()
        self.assertIsNone(p.inventory_disposal_pending)
        self.assertIsNotNone(p.inventory_pressure)


class KeyedRoomTests(unittest.TestCase):
    def room(self):
        s,p=arena()
        # Two small chambers reached from one observed vestibule; a third
        # independent door is deliberately not part of the choice.
        floor={28,37,46,55,29,31,40,49,58,60,69}
        s['hero']['cell']=37
        s['map']['cells']=[{'cell':c,'terrain':31 if c in {30,57,68}
                           else 1 if c in floor else 4,'visible':False,'observed':True}
                          for c in range(81)]
        for t in s['map']['cells']:
            if t['cell'] in {28,37,46,55}:t['visible']=True
        s['keys']=[{'name':'Crystal key','depth':1,'quantity':1}]
        s['objects']=[{'cell':31,'name':'Chest','description':"You won't know what's inside until you open it!"}]
        # The chamber's passable area must connect only through its own door.
        p.update(s)
        return s,p

    def test_remembered_crystal_door_with_ordinary_chest_is_not_skipped(self):
        s,p=self.room()
        action=crystal_choice(p,s,[],neighbors)
        self.assertIsNotNone(action)
        self.assertIn(30,p.crystal_spend_plans)
        self.assertNotIn(68,p.crystal_choice_groups[30])
        self.assertNotIn(68,p.resolved_crystal_alternatives)

    def test_keyless_doors_wait_for_matching_key_without_guessing_prize(self):
        s,p=self.room();p.keys['crystal']=0
        self.assertIsNone(crystal_choice(p,s,[],neighbors))
        observe_keys(p,s)
        locks=p.planner.report['keyed_rooms']['locks']
        self.assertTrue(all('find matching key' in l['status'] for l in locks if l['required_key']=='crystal'))

    def test_observed_key_becomes_priority_when_corresponding_lock_is_pending(self):
        s,p=self.room();p.keys['crystal']=0
        p.loot[28]={'cell':28,'name':'Crystal key','top_item':item('Crystal key')}
        self.assertIn(28,targets(p))

    def test_alternatives_need_visible_opening_and_key_consumption(self):
        s,p=self.room()
        record_spend(p,s,30,'door',{57,60})
        p.tiles[30]['terrain']=6
        observe_keys(p,s)
        self.assertFalse(p.resolved_crystal_alternatives)
        p.keys['crystal']=0
        observe_keys(p,s)
        self.assertFalse(p.resolved_crystal_alternatives)  # Target still out of vision.
        next(t for t in s['map']['cells'] if t['cell']==30)['visible']=True
        observe_keys(p,s)
        self.assertEqual(p.resolved_crystal_alternatives,{57,60})
        self.assertNotIn(68,p.resolved_crystal_alternatives)

    def test_two_keys_do_not_write_off_the_other_choice(self):
        s,p=self.room();p.keys['crystal']=2
        record_spend(p,s,30,'door',{57})
        p.keys['crystal']=1;p.tiles[30]['terrain']=6
        next(t for t in s['map']['cells'] if t['cell']==30)['visible']=True
        observe_keys(p,s)
        self.assertFalse(p.resolved_crystal_alternatives)

    def test_newly_found_crystal_key_reopens_previous_alternative(self):
        s,p=self.room()
        p.crystal_key_count=0;p.resolved_crystal_alternatives={57}
        observe_keys(p,s)
        self.assertFalse(p.resolved_crystal_alternatives)

    def test_regular_lock_is_proactively_routed_with_an_iron_not_crystal_key(self):
        s,p=arena();p.tiles[41]['terrain']=10
        p.keys={'iron':0,'crystal':1}
        self.assertIsNone(locked_room_route(p,s))
        p.keys['iron']=1
        action=locked_room_route(p,s)
        self.assertEqual(action.action['cell'],41)

    def test_crystal_chest_selection_is_not_recorded_as_collection(self):
        s,p=arena();p.keys['crystal']=1
        p.loot={42:{'cell':42,'name':'crystal chest','description':'You can see a wand inside.'},
                43:{'cell':43,'name':'crystal chest','description':'You can see a ring inside.'}}
        prepare_containers(p,s)
        self.assertIn(42,p.allowed_chests)
        self.assertEqual(p.crystal_spend_plans[42]['alternatives'],{43})
        self.assertFalse(p.resolved_crystal_alternatives)


class TrinketCraftingTests(unittest.TestCase):
    def test_catalyst_recipe_cost_and_urgent_food_precedence(self):
        s,p=arena();s['inventory']=[item('magical catalyst')]
        brew=plan_brew(s)
        self.assertEqual(brew.ingredients,('magical catalyst',))
        self.assertEqual(brew.output,'trinket');self.assertEqual(brew.energy,6)
        s['inventory'].append(item('mystery meat'))
        self.assertEqual(plan_brew(s).output,'stewed meat')

    def policy(self):
        brew=Brew(('magical catalyst',),'trinket','craft catalyst',6)
        p=AlchemyPolicy(brew)
        p.alchemy_plan.update(stage='slot',index=1,reserve=2,
                             inventory_before={'magical catalyst':1,'trinket':0,'petrified seed':0})
        return p

    def test_requires_six_energy_plus_reserve(self):
        p=self.policy()
        action=alchemy_menu(p,scene('Craft: trinket','Back',ui={
            'texts':[],'buttons':[{'id':'craft','label':'Craft: trinket'},{'id':'back','label':'Back'}],
            'energy_text':'Energy: 7'}))
        self.assertEqual(action,{'type':'button','id':'back'})
        self.assertIsNone(p.alchemy_plan)

    def test_full_observed_craft_choice_confirmation_and_receipt_sequence(self):
        p=self.policy()
        def menu(labels,texts=(),inventory=None):
            extra={'ui':{'texts':list(texts),'buttons':[{'id':str(i),'label':label} for i,label in enumerate(labels)],
                         'energy_text':'Energy: 10'}}
            if inventory is not None:extra['inventory']=inventory
            return scene(**extra)
        self.assertEqual(alchemy_menu(p,menu(['Craft: trinket','Back'])),{'type':'button','id':'0'})
        self.assertNotIn('alchemy_receipt',p.planner.report)
        offered=menu(['mimic tooth','salt cube','petrified seed','random trinket'],['Create a Trinket'])
        self.assertEqual(alchemy_menu(p,offered),{'type':'button','id':'2'})
        confirm=menu(['Confirm','Cancel'],['Petrified Seed','Drops runestones instead of seeds.'])
        self.assertEqual(alchemy_menu(p,confirm),{'type':'button','id':'0'})
        self.assertNotIn('alchemy_receipt',p.planner.report)
        alchemy_menu(p,menu(['Back'],inventory=[item('petrified seed')]))
        self.assertEqual(p.planner.report['alchemy_receipt']['output'],'petrified seed')
        self.assertTrue(p.planner.report['alchemy_receipt']['ingredients_consumed'])
        self.assertTrue(p.planner.report['alchemy_receipt']['output_inventory_increased'])

    def test_wrong_confirmation_never_claims_or_clicks_reward(self):
        p=self.policy();p.alchemy_plan.update(stage='trinket-confirm',trinket='petrified seed')
        with self.assertRaises(AssertionError):
            alchemy_menu(p,scene('Confirm','Cancel',ui={
                'texts':['Mimic tooth'],'buttons':[{'id':'confirm','label':'Confirm'}]}))
        self.assertNotIn('alchemy_receipt',p.planner.report)

    def test_confirmation_is_never_retried_when_choice_window_persists(self):
        p=self.policy();p.alchemy_plan.update(stage='done',trinket_confirmed=True)
        with self.assertRaises(AssertionError):
            alchemy_menu(p,scene('petrified seed',ui={
                'texts':['Create a Trinket'],'buttons':[{'id':'seed','label':'petrified seed'}]}))

    def test_unknown_only_offers_stop_instead_of_random_choice(self):
        p=self.policy();p.alchemy_plan['stage']='done'
        with self.assertRaises(AssertionError):
            alchemy_menu(p,scene('random trinket','unknown trinket',ui={
                'texts':['Create a Trinket'],'buttons':[{'id':'random','label':'random trinket'}]}))

    def test_missing_inventory_after_selection_never_fabricates_receipt(self):
        p=self.policy();p.alchemy_plan.update(stage='done',crafted_output='petrified seed',
                                             before_counts={'magical catalyst':1,'petrified seed':0})
        alchemy_menu(p,scene('Back'))
        self.assertNotIn('alchemy_receipt',p.planner.report)

    def test_all_seventeen_pinned_trinkets_have_unique_ranks(self):
        self.assertEqual(len(TRINKETS),17)
        self.assertEqual(len(set(TRINKETS.values())),17)
        self.assertGreater(TRINKETS['petrified seed'],TRINKETS['mimic tooth'])


if __name__=='__main__':
    unittest.main()
