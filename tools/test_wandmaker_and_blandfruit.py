import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_challenge_systems import item
from tools.wandmaker_quest import choose, observe, menu, ritual, ember_combat
from tools.blandfruit_tactics import choose as fruit, recipe
from tools.alchemy_tactics import plan_brew, alchemy_menu, Brew
from tools.special_rooms import assess
from tools.room_completion import obligations


def quest(variant='berry'):
    s,p=arena()
    p.wandmaker_quest={'variant':variant,'stage':'active','cell':10,'depth':s['depth']}
    return s,p


class WandmakerTests(unittest.TestCase):
    def test_detects_observed_npc_without_assuming_quest(self):
        s,p=arena();s['objects']=[{'name':'old wandmaker','cell':41}]
        observe(p,s)
        self.assertNotIn('variant',p.wandmaker_quest)
        self.assertEqual(41,choose(p,s,[]).action['cell'])

    def test_dialogue_recognizes_all_three_variants(self):
        for text,kind in [('some _corpse dust._','dust'),('some _fresh embers_','ember'),
                          ('a _rotberry plant,_','berry')]:
            s,p=arena();p.wandmaker_menu={'steps':0}
            s['ui']={'texts':[text],'buttons':[]}
            self.assertEqual('back',menu(p,s).action['type'])
            self.assertEqual(kind,p.wandmaker_quest['variant'])

    def test_dust_return_requires_carried_objective(self):
        s,p=quest('dust')
        observe(p,s);self.assertEqual('active',p.wandmaker_quest['stage'])
        s['inventory'].append(item('corpse dust',''))
        observe(p,s);self.assertEqual('return',p.wandmaker_quest['stage'])
        self.assertIsNone(p.preparation(s,[]))
        self.assertIsNotNone(choose(p,s,[]))

    def test_embers_use_actual_public_inventory_name(self):
        s,p=quest('ember');s['inventory'].append(item('elemental embers','DROP'))
        observe(p,s);self.assertEqual('return',p.wandmaker_quest['stage'])

    def test_lashers_are_never_attack_targets(self):
        s,p=quest()
        lasher={'name':'rot lasher','cell':43};s['objects']=[lasher]
        with patch.object(p,'best_attack',side_effect=AssertionError('must bypass lasher')):
            self.assertIsNone(choose(p,s,[]))
        for name in ('wand of frost','throwing knife','wand of magic missile'):
            self.assertFalse(p.target_allowed(item(name,'ZAP'),lasher))

    def test_active_rot_garden_allows_bypass_but_keeps_lasher_buffer(self):
        s,p=quest();actors={43:{'name':'rot lasher','cell':43},24:{'name':'rot heart','cell':24}}
        blocked,skipped,_=assess(p.tiles,actors,{},9,9,rot_quest=True)
        self.assertIn(42,blocked);self.assertIn(43,blocked);self.assertIn(24,blocked)
        self.assertNotIn(40,blocked);self.assertNotIn(40,skipped)

    def test_fire_cannot_destroy_rotberry_seed(self):
        s,p=quest();heart={'name':'rot heart','cell':24}
        for name in ('wand of fireblast','potion of liquid flame','firefruit','seed of firebloom'):
            self.assertFalse(p.item_action_allowed(item(name,'THROW'),'THROW'))
            self.assertFalse(p.target_allowed(item(name,'ZAP'),heart))
        self.assertTrue(p.target_allowed(item('wand of frost','ZAP'),heart))

    def test_only_heart_receives_ranged_attack(self):
        s,p=quest();s['objects']=[{'name':'rot lasher','cell':43},{'name':'rot heart','cell':22}]
        p.shot_clear=lambda *a:True
        with patch.object(p,'best_attack',return_value=p.cell(22,'test')) as attack:
            self.assertIn('Rot Heart',choose(p,s,[]).reason)
            self.assertEqual('rot heart',attack.call_args.args[1]['name'])
            self.assertEqual({'magic','thrown'},attack.call_args.kwargs['allowed_kinds'])

    def test_bypass_route_stays_outside_lasher_range(self):
        from tools.policy_geometry import distance
        s,p=quest();s['objects']=[{'name':'rot lasher','cell':43},{'name':'rot heart','cell':16}]
        p.update(s)
        p.shot_clear=lambda state,target:state['hero']['cell']==31
        with patch.object(p,'best_attack',return_value=None):
            action=choose(p,s,[])
        self.assertIn('bypass lashers',action.reason)
        self.assertEqual(31,action.action['cell'])
        self.assertTrue(all(distance(c,43,9)>1 for c in p.route(p.paths(s),31)))

    def test_optional_fire_preparers_respect_quest_veto(self):
        from tools.resource_tactics import prepare_meat
        from tools.room_tactics import controlled_burn
        from tools.policy_geometry import distance,neighbors
        s,p=quest();s['inventory']=[item('seed of firebloom','THROW'),item('mystery meat','THROW'),
                                  item('potion of liquid flame','THROW')]
        self.assertIsNone(prepare_meat(p,s,[],distance,neighbors))
        p.tiles[42]['terrain']=13
        self.assertIsNone(controlled_burn(p,s,[],distance,neighbors))

    def test_seed_return_and_obligation(self):
        s,p=quest();s['inventory'].append(item('seed of rotberry','THROW'))
        observe(p,s)
        self.assertEqual('return',p.wandmaker_quest['stage'])
        self.assertTrue(any(o['kind']=='Wandmaker quest/reward' for o in obligations(p,s)))

    def test_reward_hand_in_is_not_collection(self):
        s,p=quest('dust');q=p.wandmaker_quest
        q.update(stage='claiming',selected='wand of frost',count_before=0)
        observe(p,s);self.assertEqual('collect_dropped',q['stage'])
        s['inventory'].append(item('wand of frost +1','ZAP'))
        observe(p,s);self.assertEqual('done',q['stage'])

    def test_preview_and_confirm_only_matching_wand(self):
        s,p=quest('dust');p.wandmaker_quest['stage']='return'
        p.wandmaker_menu={'steps':0,'stage':'dialogue'}
        s['ui']={'texts':[],'buttons':[{'id':'a','label':'wand of frost +1'},{'id':'b','label':'wand of magic missile +1'}]}
        self.assertEqual('a',menu(p,s).action['id'])
        s['ui']={'texts':['wand of frost +1'],'buttons':[{'id':'cancel','label':'Cancel'}]}
        self.assertEqual('cancel',menu(p,s).action['id'])
        s['ui']['buttons']=[{'id':'a','label':'wand of frost +1'},{'id':'b','label':'wand of magic missile +1'}]
        self.assertEqual('b',menu(p,s).action['id'])

    def ritual_arena(self):
        s,p=quest('ember');s['hero']['cell']=58
        s['inventory']=[item('ceremonial candle','THROW',quantity=4),item('potion of frost','THROW')]
        for c in (30,31,32,39,40,41,48,49,50):p.tiles[c]['name']='ritual marker'
        return s,p

    def test_partial_marker_never_guesses_center(self):
        s,p=self.ritual_arena();p.tiles[30].pop('name')
        self.assertIsNone(ritual(p,s,p.paths(s)))

    def test_no_cold_no_summoning(self):
        s,p=self.ritual_arena();s['inventory'].pop()
        self.assertIsNone(ritual(p,s,p.paths(s)))

    def test_pending_candle_is_not_rethrown(self):
        s,p=self.ritual_arena()
        a=ritual(p,s,p.paths(s))
        self.assertEqual('THROW',a.action.get('action'))
        self.assertIsNone(ritual(p,s,p.paths(s)))
        observe(p,s)
        self.assertIn('candle_pending',p.wandmaker_quest)
        cell=p.wandmaker_quest['candle_pending']['cell']
        s['inventory'][0]['quantity']=3
        p.loot[cell]={'name':'ceremonial candle'}
        observe(p,s)
        self.assertIn(cell,p.wandmaker_quest['placed'])
        self.assertIn(cell,p.room_blocked)

    def test_elemental_gets_known_frost_not_unknown_color(self):
        s,p=quest('ember');foe={'name':'newborn fire elemental','cell':22}
        s['objects']=[foe];s['inventory']=[item('potion of frost','THROW')]
        self.assertEqual('potion of frost',ember_combat(p,s,[foe]).action['id'])
        s['inventory']=[item('blue potion','THROW')]
        a=ember_combat(p,s,[foe]);self.assertIsNone(a)

    def test_icecap_requires_payload_and_observed_activation(self):
        s,p=quest('ember');foe={'name':'newborn fire elemental','cell':22}
        s['objects']=[foe];s['inventory']=[item('seed of icecap','THROW'),item('waterskin','THROW')]
        a=ember_combat(p,s,[foe]);self.assertEqual('seed of icecap',a.action['id'])
        cell=p.target;p.tiles[cell]['plant']='icecap'
        a=ember_combat(p,s,[foe]);self.assertEqual('waterskin',a.action['id'])
        self.assertFalse(p.trap_payload_return['disarm_required'])

    def test_water_side_combat_position(self):
        s,p=quest('ember');foe={'name':'newborn fire elemental','cell':16}
        s['objects']=[foe];s['inventory']=[]
        p.tiles[58]['terrain']=29
        a=ember_combat(p,s,[foe])
        self.assertIn('near water',a.reason)

    def test_icecap_does_not_assume_flying_enemy_trigger(self):
        s,p=quest('ember');foe={'name':'newborn fire elemental','cell':22}
        s['objects']=[foe];s['inventory']=[item('seed of icecap','THROW')]
        self.assertIsNone(ember_combat(p,s,[foe]))
        self.assertNotIn('icecap',p.wandmaker_quest)


class BlandfruitTests(unittest.TestCase):
    def test_known_seed_recipe_and_quest_seed_protection(self):
        self.assertIsNone(recipe({'blandfruit':1,'seed of rotberry':1},()))
        self.assertEqual((('blandfruit','seed of mageroyal'),'dreamfruit'),
                         recipe({'blandfruit':1,'seed of mageroyal':1},()))
        self.assertIsNone(recipe({'blandfruit':1,'seed of sungrass':1},()))
        self.assertIsNone(recipe({'blandfruit':1,'seed of icecap':1},('frost',)))

    def test_alchemy_plans_actual_cooked_output(self):
        s,p=arena();s['inventory']=[item('blandfruit','EAT'),item('seed of icecap','THROW')]
        brew=plan_brew(s)
        self.assertEqual('icefruit',brew.output)
        self.assertEqual(('blandfruit','seed of icecap'),brew.ingredients)

    def test_alchemy_receipt_needs_observed_output_not_just_spent_inputs(self):
        s,p=arena()
        for output,expected in [([],False),([item('dreamfruit','EAT')],True)]:
            p.alchemy_plan={'brew':Brew(('blandfruit','seed of mageroyal'),'dreamfruit','test'),
                'stage':'done','steps':6,'crafted_output':'dreamfruit',
                'before_counts':{'blandfruit':1,'seed of mageroyal':1,'dreamfruit':0}}
            s['inventory']=output;s['ui']={'texts':[],'buttons':[]}
            alchemy_menu(p,s)
            self.assertEqual(expected,p.planner.report['alchemy_receipt']['output_inventory_increased'])
            self.assertTrue(p.planner.report['alchemy_receipt']['ingredients_consumed'])

    def test_harmful_fruit_never_eaten_and_chunks_are_food(self):
        s,p=arena();s['inventory']=[item(n,'EAT') for n in (
            'blandfruit','earthfruit','sorrowfruit','icefruit','firefruit','stormfruit','blandfruit chunks','dreamfruit')]
        self.assertEqual(['blandfruit chunks','dreamfruit'],[i['name'] for i in p.food_items(s)])

    def test_bush_harvesting_and_combat_deferral(self):
        s,p=arena();p.tiles[41]['plant']='blandfruit'
        self.assertIn('harvest',fruit(p,s,[]).reason)
        self.assertIsNone(fruit(p,s,[{'name':'skeleton','cell':22}]))

    def test_carried_seed_uses_real_name_and_no_repeat(self):
        s,p=arena();s['inventory']=[item('seed of blandfruit','PLANT')]
        self.assertEqual('PLANT',fruit(p,s,[]).action['action'])
        self.assertIsNone(fruit(p,s,[]))

    def test_icefruit_throw_avoids_hero_and_allies(self):
        s,p=arena();s['inventory']=[item('icefruit','THROW')]
        foe={'name':'skeleton','cell':22};s['objects']=[foe]
        self.assertIsNone(fruit(p,s,[foe]))  # Two cells away: conservative splash margin.
        foe['cell']=13
        self.assertEqual('THROW',fruit(p,s,[foe]).action['action'])
        s['objects'].append({'name':'sad ghost','cell':14})
        self.assertIsNone(fruit(p,s,[foe]))


if __name__=='__main__':unittest.main()
