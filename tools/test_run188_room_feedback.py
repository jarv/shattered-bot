"""Reduced public mechanics/selector fixtures, not a changed-policy gameplay replay."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.hidden_doors import special_room_walls,seek_required_corridor_tip
from tools.keyed_rooms import crystal_keys_ready,observe
from tools.policy_geometry import distance
from tools.ghost_quest import seek_quest_foe
from tools.inventory_tactics import choose,sale_menu,observe_accepted,candidates
from tools.puzzle_supplies import safe_test_bank
from tools.policy_geometry import neighbors
from tools.wooden_barrier import known_burn
from tools.test_consumable_tactics import potion


class CrystalRoomTests(unittest.TestCase):
    def test_room_walls_override_dead_end_without_disabling_other_rooms(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        for c in (38,39,40,41,42):p.tiles[c]['terrain']=1
        p.tiles[49]['terrain']=31
        s['hero']['cell']=40
        self.assertIn(37,special_room_walls(p,s))
        self.assertIsNone(seek_required_corridor_tip(p,s,[],distance))
        p.tiles[49]['terrain']=4
        self.assertFalse(special_room_walls(p,s))
        self.assertIsNotNone(seek_required_corridor_tip(p,s,[],distance))

    def test_crystal_chest_exempts_only_its_door_delimited_interior(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        for c in (38,39,41,42):p.tiles[c]['terrain']=1
        p.tiles[40]['terrain']=6
        p.loot[38]={'name':'crystal chest'}
        walls=special_room_walls(p,s)
        self.assertIn(37,walls)
        self.assertNotIn(43,walls)
        observe(p,s)
        p.loot.clear()
        self.assertIn(37,special_room_walls(p,s))

    def test_three_keys_before_first_six_door_path_spend_and_receipted_total_afterward(self):
        s,p=arena();p.crystal_doors_seen={10,11,12,13,14,15}
        p.crystal_key_requirement=3  # Previously observed six doors sharing one vestibule.
        p.keys['crystal']=1
        self.assertFalse(crystal_keys_ready(p))
        p.tiles[41]['terrain']=31
        self.assertFalse(p.walkable(41))
        p.keys['crystal']=3
        observe(p,s)
        self.assertTrue(crystal_keys_ready(p))
        self.assertTrue(p.walkable(41))
        p.keys['crystal']=2
        observe(p,s)
        self.assertTrue(crystal_keys_ready(p))
        p.keys['crystal']=0
        observe(p,s)
        self.assertEqual(3,p.crystal_keys_collected)

    def test_one_key_choice_is_not_mistaken_for_three_key_path(self):
        s,p=arena();p.crystal_doors_seen={10,11};p.keys['crystal']=1
        self.assertTrue(crystal_keys_ready(p))

    def test_key_requirement_comes_from_local_geometry_and_resets_on_new_floor(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        for c in (39,40,41):p.tiles[c]['terrain']=1
        for c in (30,31,32,48,49,50):p.tiles[c]['terrain']=31
        observe(p,s)
        self.assertEqual(3,p.crystal_key_requirement)
        p.memory.reset_floor(40)
        self.assertEqual(1,p.crystal_key_requirement)
        self.assertFalse(p.crystal_room_search_walls)

    def test_six_disconnected_doors_do_not_establish_a_three_key_room(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        for c in (12,13,30,31,48,49):p.tiles[c]['terrain']=31
        observe(p,s)
        self.assertEqual(1,p.crystal_key_requirement)


class GhostContinuationTests(unittest.TestCase):
    def setup_quest(self):
        s,p=arena();s['depth']=2
        p.ghost_quest={'stage':'active','depth':2,'target':'fetid rat'}
        return s,p

    def test_accepted_quest_searches_instead_of_immediately_descending(self):
        s,p=self.setup_quest()
        a=seek_quest_foe(p,s,[])
        self.assertIsNotNone(a)
        self.assertIn('seek accepted Sad Ghost foe',a.reason)
        self.assertNotEqual(s['hero']['cell'],a.action['cell'])
        self.assertFalse(p.ghost_quest['hunt_visited'])

    def test_hunt_yields_to_threats_low_health_and_wrong_floor(self):
        s,p=self.setup_quest()
        self.assertIsNone(seek_quest_foe(p,s,[{'name':'rat','cell':41}]))
        s['hero']['hp']=1
        self.assertIsNone(seek_quest_foe(p,s,[]))
        s['hero']['hp']=s['hero']['max_hp'];s['depth']=3
        self.assertIsNone(seek_quest_foe(p,s,[]))

    def test_hunt_has_explicit_budget_not_starvation_waits(self):
        s,p=self.setup_quest();p.ghost_quest['hunt_steps']=64
        self.assertIsNone(seek_quest_foe(p,s,[]))
        self.assertEqual('exhausted',p.planner.report['ghost_hunt']['status'])
        self.assertEqual('active',p.ghost_quest['stage'])


class GooSaleTests(unittest.TestCase):
    def test_stack_sale_requires_quote_inventory_removal_and_gold_receipt(self):
        s,p=arena()
        goo={'id':'goo','name':'blob of goo x2','quantity':2,'identified':True,'actions':['DROP']}
        s['inventory'].append(goo)
        self.assertNotIn(goo,candidates(p,s,'DROP'))
        s['objects']=[{'name':'shopkeeper','cell':41}]
        self.assertIsNotNone(choose(p,s,[]))
        p.sell_plan['stage']='select';s['modal']=True
        s['ui']={'texts':['Sell an item'],'buttons':[{'id':'goo-button','label':'blob of goo x2'}]}
        self.assertEqual('goo-button',sale_menu(p,s).action['id'])
        s['ui']={'texts':['blob of goo'],'buttons':[{'id':'one','label':'Sell 1 for 30g'},
                                                     {'id':'all','label':'Sell all for 60g'}]}
        a=sale_menu(p,s)
        self.assertEqual('one',a.action['id'])
        after=copy.deepcopy(s)
        after['inventory'][-1].update(name='blob of goo',quantity=1)
        after['hero']['gold']=s['hero'].get('gold',0)+30
        events=observe_accepted(p,s,a,after)
        self.assertEqual('sold',events[0]['kind'])
        self.assertEqual(1,events[0]['quantity'])

    def test_goo_is_not_dropped_without_a_shop(self):
        s,p=arena()
        s['inventory'].append({'id':'goo','name':'blob of goo','identified':True,'actions':['DROP']})
        self.assertIsNone(choose(p,s,[]))


class NarrowPuzzleEntranceTests(unittest.TestCase):
    def test_known_flame_uses_two_square_isolated_corridor_bank(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        p.tiles[40]['terrain']=13
        p.tiles[41]['terrain']=20
        p.tiles[42]['terrain']=20
        p.tiles[43]['terrain']=5
        p.tiles[44]['terrain']=1
        s['hero']['cell']=42
        s['inventory'].append(potion('potion of liquid flame'))
        a=known_burn(p,s,[])
        self.assertEqual('THROW',a.action['action'])
        self.assertEqual(40,p.target)
        self.assertEqual('verify-wood',p.wood_burn_plan['phase'])
        self.assertFalse(p.completed_room_rewards)

    def test_flame_does_not_treat_exposed_door_or_valuable_loot_as_safe(self):
        for kind in ('door','loot'):
            s,p=arena()
            for t in p.tiles.values():t['terrain']=4
            for c in (41,42,43):p.tiles[c]['terrain']=20
            p.tiles[40]['terrain']=13
            s['hero']['cell']=42
            s['inventory'].append(potion('potion of liquid flame'))
            if kind=='door':p.tiles[41]['terrain']=5
            else:p.loot[41]={'name':'scroll of upgrade'}
            self.assertIsNone(known_burn(p,s,[]))

    def test_water_flight_alcove_requires_observed_continuing_retreat(self):
        s,p=arena()
        for t in p.tiles.values():t['terrain']=4
        for c in (40,31,22):p.tiles[c]['terrain']=29
        p.tiles[49]['terrain']=5
        p.tiles[41]['terrain']=0
        self.assertFalse(safe_test_bank(p,s,40,distance,neighbors,allow_dry=True,flight_bank=True))
        p.flight_entrance_receipts.add((s['depth'],s.get('branch',0),49))
        self.assertTrue(safe_test_bank(p,s,40,distance,neighbors,allow_dry=True,flight_bank=True))
        self.assertFalse(safe_test_bank(p,s,40,distance,neighbors,allow_dry=True))
        p.tiles[22]['visible']=False
        self.assertFalse(safe_test_bank(p,s,40,distance,neighbors,allow_dry=True,flight_bank=True))


if __name__=='__main__':
    unittest.main()
