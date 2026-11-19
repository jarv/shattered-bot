import copy
from itertools import permutations
import unittest
from unittest.mock import patch

from tools.loot_route import shortest_tour,TourTooLarge
from tools.loot_completion import required_loot,missing_keys,observe_collected,remember_missing,pending_collections
from tools.room_loot import before_room_exit
from tools.room_completion import obligations
from tools.policy_decision import Decision,Intent,Finished
from tools.policy_runtime import Transaction
from tools.policy_geometry import distance,neighbors
from tools.survival_policy import SurvivalPolicy
from tools.test_challenge_systems import ready,item


class ShortestLootTourTests(unittest.TestCase):
    def test_exact_tour_beats_repeated_nearest_pickup(self):
        order,cost=shortest_tour(24,[2,5,7,9],set(range(49)),7,7)
        self.assertEqual(9,cost)  # Greedy 24->9->2->7->5 costs ten movements.
        self.assertEqual({2,5,7,9},set(order))

    def test_cost_matches_bruteforce_with_and_without_exit(self):
        targets=[2,5,7,9,42]
        for end in (None,48):
            order,cost=shortest_tour(24,targets,set(range(49)),7,7,end)
            def route_cost(order):
                route=(24,)+order+((end,) if end is not None else ())
                return sum(distance(a,b,7) for a,b in zip(route,route[1:]))
            self.assertEqual(min(map(route_cost,permutations(targets))),cost)

    def test_path_distance_not_straight_line_and_no_exit_transit(self):
        # A wall forces a detour; adjacent Chebyshev distance is not a route.
        cells={0,1,2,7,12,11,10}
        self.assertEqual(4,shortest_tour(0,[10],cells,5,3)[1])
        # The optional exit cannot be used as a bridge between item piles.
        self.assertIsNone(shortest_tour(0,[2],{0,2},3,1,end=1))

    def test_disconnected_targets_are_not_silently_dropped(self):
        self.assertIsNone(shortest_tour(0,[1,8],{0,1,8},3,3))

    def test_large_exact_problem_is_not_mislabeled_as_optimal_greedy(self):
        with self.assertRaises(TourTooLarge):shortest_tour(0,range(15),set(range(25)),5,5)


class StrictLootTests(unittest.TestCase):
    def encounter(self):
        s,p=ready()
        p.tiles={c:{'cell':c,'terrain':1,'visible':True} for c in range(49)}
        s['map']={'width':7,'height':7,'cells':list(p.tiles.values())};s['hero']['cell']=24
        s['objects']=[]
        return s,p

    def test_ordinary_item_and_chest_block_explicit_descent(self):
        for obj in ({'name':'Chest'},{'name':'seed of icecap','top_item':item('seed of icecap','THROW')}):
            s,p=ready();p.loot[26]=dict(obj,cell=26)
            # Quiet-room routing is unavailable; the floor-level gate still holds.
            p.recent_threats[24]={'cell':24,'name':'rat'}
            with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'cell','cell':25},'descend',Intent.DESCEND)):
                with self.assertRaisesRegex(Finished,'Observed loot incomplete'):p.choose(s)
            self.assertFalse(p.descent_counts_as_clear())

    def test_visible_missing_golden_key_requires_search_even_under_pressure(self):
        s,p=ready();s['hero'].update(hp=5,buffs=[{'name':'starving'}]);s['inventory']=[]
        p.loot[26]={'cell':26,'name':'Locked chest'}
        self.assertEqual({'golden'},missing_keys(p))
        self.assertTrue(p.requires_key_search(s));self.assertGreaterEqual(p.search_limit(s,0,True),12)
        p.keys['golden']=1
        self.assertFalse(p.requires_key_search(s))

    def test_journal_keys_on_other_floor_do_not_unlock_required_chest(self):
        s,p=ready();s['keys']=[{'name':'golden key','depth':2,'quantity':1}];p.update(s)
        p.loot[26]={'cell':26,'name':'Locked chest'}
        self.assertEqual({'golden'},missing_keys(p))

    def test_worn_and_skeleton_locks_use_their_matching_journal_keys(self):
        s,p=ready();s['keys']=[{'name':'worn key','depth':1,'quantity':1},
                              {'name':'skeleton key','depth':1,'quantity':1}]
        p.update(s);p.tiles[25]['terrain']=21;p.tiles[26]['terrain']=38
        self.assertFalse(missing_keys(p))
        p.keys['worn']=0
        self.assertEqual({'worn'},missing_keys(p))

    def test_seen_key_is_selected_before_distant_unopened_chest(self):
        s,p=ready();p.loot[23]={'cell':23,'name':'Golden key','top_item':item('Golden key','THROW')}
        p.loot[26]={'cell':26,'name':'Locked chest'}
        action=p.systematic_exploration(s,p.paths(s),set())
        self.assertEqual(23,action.action['cell']);self.assertEqual(Intent.LOOT,action.intent)

    def test_all_room_piles_are_planned_together_not_only_at_exit(self):
        s,p=self.encounter()
        for c in (2,5,7,9):p.loot[c]={'cell':c,'name':'seed','top_item':item('seed','THROW')}
        action=before_room_exit(p,s,Decision({'type':'cell','cell':25},'explore',Intent.EXPLORE))
        self.assertEqual(Intent.LOOT,action.intent)
        self.assertEqual(9,p.room_loot_plan['cost'])
        self.assertEqual({2,5,7,9},set(p.room_loot_plan['order']))
        self.assertEqual('exact Held–Karp over observed safe BFS distances',p.planner.report['room_loot_route']['method'])

    def test_new_item_replans_and_combat_only_suspends_not_completes(self):
        s,p=self.encounter();p.loot[2]={'cell':2,'name':'seed','top_item':item('seed','THROW')}
        decision=Decision({'type':'cell','cell':25},'explore',Intent.EXPLORE)
        before_room_exit(p,s,decision)
        p.loot[7]={'cell':7,'name':'seed','top_item':item('seed','THROW')}
        before_room_exit(p,s,decision)
        self.assertEqual({2,7},set(p.room_loot_plan['order']))
        p.recent_threats[9]={'cell':9,'name':'rat'}
        self.assertIsNone(before_room_exit(p,s,decision));self.assertEqual({2,7},set(required_loot(p)))

    def test_entire_room_tour_executes_optimal_movement_count(self):
        s,p=self.encounter()
        for c in (2,5,7,9):p.loot[c]={'cell':c,'name':'seed','top_item':item('seed','THROW')}
        moves=0
        while p.loot and moves<20:
            a=before_room_exit(p,s,Decision({'type':'cell','cell':25},'explore',Intent.EXPLORE))
            self.assertIsNotNone(a)
            s['hero']['cell']=a.action['cell'];p.loot.pop(a.action['cell'],None);moves+=1
        self.assertFalse(p.loot);self.assertEqual(9,moves)

    def test_room_tour_never_uses_sale_or_plant_as_transit(self):
        s,p=self.encounter();p.loot[2]={'cell':2,'name':'seed','top_item':item('seed','THROW')}
        p.tiles[16]['plant']='firebloom'
        p.loot[17]={'cell':17,'name':'ration','for_sale':True,'top_item':item('ration','EAT')}
        a=before_room_exit(p,s,Decision({'type':'cell','cell':25},'explore',Intent.EXPLORE))
        self.assertNotIn(a.action['cell'],{16,17})

    def test_deferrals_never_waive_completion_and_sales_are_not_pickups(self):
        s,p=ready();p.loot[26]={'cell':26,'name':'wand','top_item':item('wand','ZAP')}
        p.combat_deferred_loot.add(26);p.room_loot_deferred[26]=()
        self.assertIn(26,required_loot(p));self.assertFalse(p.descent_counts_as_clear())
        p.loot[26]['for_sale']=True
        self.assertFalse(required_loot(p))

    def test_mutually_exclusive_choice_is_exempt_not_other_loot(self):
        s,p=ready();p.loot[26]={'cell':26,'name':'Crystal chest'};p.resolved_crystal_alternatives.add(26)
        self.assertFalse(required_loot(p))
        p.loot[23]={'cell':23,'name':'Chest'}
        self.assertEqual({23},set(required_loot(p)))

    def test_revealed_mimic_does_not_erase_chest_reward_obligation(self):
        s,p=ready();p.mimic_obligations[26]={'status':'unconfirmed reward'}
        self.assertTrue(pending_collections(p));self.assertFalse(p.descent_counts_as_clear())

    def test_reusable_payload_or_stash_must_be_retrieved_before_descent(self):
        s,p=ready();p.trap_payload_return={'cell':26}
        self.assertTrue(pending_collections(p))
        p.trap_payload_return=None;p.potion_stash={'cell':23}
        self.assertTrue(pending_collections(p))

    def test_disappearance_without_inventory_evidence_is_still_unfinished(self):
        s,p=ready();old={23:{'cell':23,'name':'pasty','top_item':item('pasty','EAT')}}
        remember_missing(p,old)
        self.assertIn(23,required_loot(p));self.assertFalse(p.descent_counts_as_clear())
        self.assertIn('item disappeared without collection evidence',[o['kind'] for o in obligations(p,s)])

    def test_disappearing_chest_is_not_assumed_opened_and_collected(self):
        s,p=ready();remember_missing(p,{23:{'cell':23,'name':'Chest'}})
        self.assertIn(23,required_loot(p))

    def test_inventory_backed_pickup_resolves_missing_cell(self):
        s,p=ready();obj={'cell':23,'name':'pasty','top_item':item('pasty','EAT')};s['objects']=[obj]
        after=copy.deepcopy(s);after['objects']=[];after['inventory'].append(item('pasty','EAT'))
        observe_collected(p,s,Decision({'type':'cell','cell':23},'pickup',Intent.LOOT),after)
        remember_missing(p,{23:obj})
        self.assertFalse(required_loot(p))

    def test_key_receipt_requires_matching_current_floor_journal_increase(self):
        s,p=ready();obj={'cell':23,'name':'Golden key','top_item':item('Golden key','THROW')};s['objects']=[obj]
        after=copy.deepcopy(s);after['keys']=[{'name':'iron key','depth':1,'quantity':1}]
        action=Decision({'type':'cell','cell':23},'pickup',Intent.LOOT)
        observe_collected(p,s,action,after);self.assertFalse(p.loot_collection_receipts)
        after['keys']=[{'name':'golden key','depth':1,'quantity':1}]
        observe_collected(p,s,action,after);self.assertEqual({23},p.loot_collection_receipts)

    def test_rename_is_not_a_pickup_and_rejection_rolls_back_receipt(self):
        s,p=ready();obj={'cell':23,'name':'pasty','top_item':item('pasty','EAT')};s['objects']=[obj]
        s['inventory'].append(item('ration of food','EAT'))
        after=copy.deepcopy(s);after['inventory'][-1]['name']='pasty'
        action=Decision({'type':'cell','cell':23},'pickup',Intent.LOOT)
        observe_collected(p,s,action,after);self.assertFalse(p.loot_collection_receipts)
        after['inventory'].append(item('pasty','EAT'));tx=Transaction(p)
        observe_collected(p,s,action,after);tx.rollback();self.assertFalse(p.loot_collection_receipts)

    def test_floor_reset_clears_only_local_coverage_memory(self):
        s,p=ready();p.unconfirmed_loot[23]={'cell':23,'name':'pasty'};p.loot_collection_receipts.add(24)
        p.memory.reset_floor(1)
        self.assertFalse(p.unconfirmed_loot);self.assertFalse(p.loot_collection_receipts)


if __name__=='__main__':unittest.main()
