import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance,neighbors
from tools.potion_discovery import room_ready
from tools.hidden_doors import observe_secret_discovery
from tools.environment_tactics import clear_blocking_trap,cold_trigger_safe
from tools.garden_tactics import choose as garden,GARDEN_DESCRIPTION
from tools.freezing_food import choose as freeze
from tools.ghost_quest import quest_menu
from tools.seed_tactics import choose_seed
from tools import test_hidden_doors
from tools.challenge_rules import ChallengeRules


def arena():
    s=state();s['hero'].update(cell=40,strength=12)
    s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':1 if 0<c%9<8 and 0<c//9<8 else 4,
              'visible':True,'observed':True} for c in range(81)]}
    p=verified();p.update(s)
    return s,p


class RegularFeedbackTests(unittest.TestCase):
    def test_potion_testing_waits_for_room_loot_and_unseen_room_edges(self):
        s,p=arena();p.visits.update(p.tiles.keys());p.exhausted.update(p.tiles)
        self.assertTrue(room_ready(p,s))
        p.loot[10]={'name':'torch','top_item':{'name':'torch'}}
        self.assertFalse(room_ready(p,s));p.loot.clear()
        saved=p.tiles.pop(0)
        self.assertFalse(room_ready(p,s));p.tiles[0]=saved

    def test_observed_special_room_preserves_unknown_potions(self):
        s,p=arena();p.tiles[20].update(terrain=13)
        self.assertFalse(room_ready(p,s))

    def test_only_a_previously_seen_wall_becoming_a_door_marks_discovery(self):
        s,p=arena();before=copy.deepcopy(s)
        old=next(t for t in before['map']['cells'] if t['cell']==30);old['terrain']=4
        after=copy.deepcopy(before);next(t for t in after['map']['cells'] if t['cell']==30)['terrain']=5
        observe_secret_discovery(p,before,after);self.assertTrue(p.secret_area_found)
        p.memory.reset_floor(40);self.assertFalse(p.secret_area_found)
        old['visible']=False
        observe_secret_discovery(p,before,after);self.assertFalse(p.secret_area_found)

    def test_dead_end_search_is_still_allowed_after_secret_discovery(self):
        from tools.hidden_doors import seek_corridor_end
        s,p=test_hidden_doors.HiddenDoorTests().corridor();p.secret_area_found=True
        self.assertEqual('search',seek_corridor_end(p,s,[],distance).action['type'])

    def test_general_search_stops_after_one_secret_but_not_exploration(self):
        fixture=test_hidden_doors.HiddenDoorTests();s=fixture.room();p=fixture.policy(s)
        p.secret_area_found=True
        self.assertEqual('descend',p.explore(s,[]).intent)

    def test_blocking_cold_trap_can_be_pressed_under_an_ordinary_chest(self):
        s,p=arena();trap=43
        for c in p.tiles:p.tiles[c]['terrain']=4
        for c in (40,41,42,43,44,34,35,25):p.tiles[c]['terrain']=1
        p.tiles[trap].update(terrain=18,trap='chilling trap')
        skin={'id':'skin','name':'waterskin','actions':['THROW']};s['inventory'].append(skin)
        chest={'cell':trap,'name':'Chest'};p.loot[trap]=chest;s['objects']=[chest]
        action=clear_blocking_trap(p,s,[],distance,neighbors)
        self.assertIsNotNone(action);self.assertEqual(trap,p.target)
        self.assertEqual('THROW',action.action['action'])
        self.assertEqual(18,p.tiles[trap]['terrain'])  # Evaluation never pretends disarm happened.
        self.assertEqual('chilling trap',p.tiles[trap]['trap'])

    def test_trap_trigger_rejects_darts_locked_chests_friends_and_cold_radius(self):
        for case in ('dart','locked','friend','near','unseen'):
            s,p=arena();trap=43;p.tiles[trap].update(terrain=18,trap='chilling trap')
            if case=='dart':p.tiles[trap]['trap']='poison dart trap'
            if case=='locked':p.loot[trap]={'cell':trap,'name':'Locked chest'}
            if case=='friend':s['objects']=[{'cell':44,'name':'sad ghost'}]
            if case=='near':s['hero']['cell']=42
            if case=='unseen':p.tiles[44]['visible']=False
            self.assertFalse(cold_trigger_safe(p,s,trap,distance,neighbors),case)

    def test_natural_healing_budget_does_not_reset_when_a_room_is_reentered(self):
        s,p=arena();s['hero']['hp']=8
        s['inventory'].append({'name':'ration of food','actions':['EAT']})
        self.assertEqual(48,p.recovery_limit(s,False))
        p.natural_healing_waits=48;p.rests=0
        self.assertEqual(0,p.recovery_limit(s,False))
        s['hero']['buffs']=[{'name':'starving'}]
        self.assertEqual(0,p.recovery_limit(s,True))

    def test_garden_flavor_is_passable_but_fire_and_gas_are_not(self):
        s,p=arena();t=next(t for t in s['map']['cells'] if t['cell']==42)
        t.update(terrain=15,effects=[GARDEN_DESCRIPTION]);p.update(s)
        self.assertTrue(p.walkable(42));self.assertNotIn(42,p.room_blocked)
        action=garden(p,s,[]);self.assertIsNotNone(action)
        self.assertIn('garden:',action.reason)
        self.assertFalse(p.harmless_effect('A fire is raging here.'))
        self.assertFalse(p.harmless_effect('A cloud of toxic gas is swirling here.'))

    def test_garden_is_not_misclassified_as_smoke_for_champion_vision(self):
        s,p=arena();p.tiles[41]['effects']=[GARDEN_DESCRIPTION]
        p.challenge_combat.observe(p,s,[],lambda *a:True)
        self.assertIsNone(p.challenge_combat.vision_tiles)

    def test_sungrass_is_used_before_long_natural_recovery(self):
        s,p=arena();s['hero']['hp']=15
        s['inventory'].append({'id':'sungrass','name':'seed of sungrass','actions':['PLANT']})
        action=choose_seed(p,s,[],distance,neighbors)
        self.assertEqual('PLANT',action.action['action'])

    def test_known_slow_approach_can_use_mobility_or_blessing_seed(self):
        for name,hp in (('swiftthistle',10),('starflower',15)):
            s,p=arena();s['hero'].update(cell=20,hp=hp)
            enemy={'cell':60,'name':'gnoll scout'};s['objects']=[enemy]
            s['inventory'].append({'id':name,'name':'seed of '+name,'actions':['PLANT']})
            p.update(s)
            self.assertEqual(name,choose_seed(p,s,[enemy],distance,neighbors).action['id'])

    def test_batch_can_use_an_existing_cold_trap_without_planting(self):
        s,_=arena();p=verified(ChallengeRules(barren_land=True))
        next(t for t in s['map']['cells'] if t['cell']==41).update(terrain=18,trap='chilling trap')
        s['inventory'] += [{'id':'raw','name':'mystery meat x3','quantity':3,'actions':['DROP']},
                           {'id':'skin','name':'waterskin','actions':['THROW']}]
        p.update(s)
        self.assertEqual('DROP',freeze(p,s,[]).action['action'])
        self.assertEqual('trap',p.food_freeze_plan['kind'])
        self.assertEqual(41,p.food_freeze_plan['actuator'])

    def test_full_stack_freezing_drops_once_and_triggers_from_outside_radius(self):
        s,p=arena()
        meat={'id':'meat','name':'mystery meat x3','quantity':3,'actions':['DROP','THROW']}
        ice={'id':'ice','name':'seed of icecap','actions':['THROW']}
        skin={'id':'skin','name':'waterskin','actions':['THROW']}
        s['inventory'] += [meat,ice,skin]
        action=freeze(p,s,[]);self.assertEqual('DROP',action.action['action'])
        cell=s['hero']['cell'];s['inventory'].remove(meat)
        p.loot[cell]={'cell':cell,'name':meat['name'],'top_item':meat}
        for _ in range(6):
            action=freeze(p,s,[])
            if action.action.get('action')=='THROW':break
            s['hero']['cell']=action.action['cell']
        self.assertEqual('ice',action.action['id'])
        self.assertGreaterEqual(distance(s['hero']['cell'],cell,9),2)
        p.tiles[cell]['plant']='Icecap';s['inventory'].remove(ice)
        action=freeze(p,s,[])
        self.assertEqual('skin',action.action['id'])
        self.assertEqual(cell,p.target)
        p.tiles[cell].pop('plant');p.tiles[cell]['effects']=['Unnaturally frigid air swirls here.']
        self.assertEqual('wait',freeze(p,s,[]).action['type'])
        p.tiles[cell]['effects']=[]
        s['inventory'].append({'name':'frozen carpaccio x3','quantity':3,'actions':['EAT']})
        self.assertIsNone(freeze(p,s,[]));self.assertIsNone(p.food_freeze_plan)
        self.assertEqual(3,p.planner.report['food_freezing']['returned_frozen_units'])

    def test_food_drop_failure_is_logged_not_claimed_as_frozen(self):
        s,p=arena();s['inventory'] += [
            {'id':'raw','name':'mystery meat x3','quantity':3,'actions':['DROP']},
            {'id':'ice','name':'seed of icecap','actions':['THROW']},
            {'id':'skin','name':'waterskin','actions':['THROW']}]
        self.assertEqual('DROP',freeze(p,s,[]).action['action'])
        self.assertIsNone(freeze(p,s,[]))
        self.assertEqual('food-drop-unconfirmed',p.continuation_errors[-1]['kind'])
        self.assertIsNone(p.food_freeze_plan)

    def test_ghost_prefers_parsed_armor_even_over_a_strong_melee_reward(self):
        s,p=arena();p.ghost_menu={'stage':'preview','steps':0,'options':['sword','cloth armor'],'index':0,'scores':[]}
        s['ui']={'texts':['This melee weapon deals 30-50 damage and requires 10 strength'],
                 'buttons':[{'id':'cancel','label':'Cancel'}]}
        quest_menu(p,s)
        choices=[{'id':'weapon','label':'sword'},{'id':'armor','label':'cloth armor'}]
        s['ui']={'texts':['DEFEATED RAT'],'buttons':choices};quest_menu(p,s)
        s['ui']={'texts':['This armor blocks 0-2 damage and requires 10 strength'],
                 'buttons':[{'id':'cancel','label':'Cancel'}]};quest_menu(p,s)
        s['ui']={'texts':['DEFEATED RAT'],'buttons':choices}
        self.assertEqual('armor',quest_menu(p,s).action['id'])
