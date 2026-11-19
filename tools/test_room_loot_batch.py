import unittest
from tools.room_loot import before_room_exit
from tools.policy_decision import Decision,Intent,TacticalBlocked
from tools.policy_runtime import Transaction
from tools.test_challenge_systems import ready,item


class RoomLootBatchTests(unittest.TestCase):
    def encounter(self):
        s,p=ready()
        p.tiles={c:{'cell':c,'terrain':6 if c==25 else 1,'visible':True} for c in (22,23,24,25,26)}
        for c in (22,23):p.loot[c]={'name':'seed of stormvine','top_item':item('seed of stormvine','THROW')}
        return s,p

    def test_next_pile_precedes_intermediate_exit_route_step(self):
        s,p=self.encounter()
        a=before_room_exit(p,s,Decision({'type':'cell','cell':25},'exit',Intent.DESCEND))
        self.assertEqual(23,a.action['cell'])
        s['hero']['cell']=23;p.loot.pop(23)
        a=before_room_exit(p,s,Decision({'type':'cell','cell':24},'resume distant stairs',Intent.DESCEND))
        self.assertEqual(22,a.action['cell'])
        self.assertEqual(Intent.LOOT,a.intent)

    def test_batch_collects_same_two_items_in_five_moves_with_no_exit_roundtrip(self):
        s,p=self.encounter();route=[24];pickups=[]
        for _ in range(10):
            pos=s['hero']['cell'];decision=Decision({'type':'cell','cell':pos+1},'exit',Intent.DESCEND)
            a=before_room_exit(p,s,decision) or decision
            cell=a.action['cell'];route.append(cell);s['hero']['cell']=cell
            if cell in p.loot:pickups.append(cell);p.loot.pop(cell)
            if cell==25:break
        self.assertEqual([24,23,22,23,24,25],route)
        self.assertEqual([23,22],pickups)

    def test_new_threat_suspends_batch(self):
        s,p=self.encounter();before_room_exit(p,s,Decision({'type':'cell','cell':25},'exit',Intent.DESCEND))
        s['hero']['cell']=23;p.loot.pop(23);p.recent_threats[22]={'cell':22,'name':'rat'}
        self.assertIsNone(before_room_exit(p,s,Decision({'type':'cell','cell':24},'exit',Intent.DESCEND)))

    def test_deferred_pickup_is_not_reopened_by_batch(self):
        s,p=self.encounter();before_room_exit(p,s,Decision({'type':'cell','cell':25},'exit',Intent.DESCEND))
        s['hero']['cell']=23;p.loot.pop(23);p.combat_deferred_loot.add(22)
        self.assertIsNone(before_room_exit(p,s,Decision({'type':'cell','cell':24},'exit',Intent.DESCEND)))
        self.assertIn(22,p.loot)

    def test_cumulative_budget_does_not_reset_on_next_pile(self):
        s,p=self.encounter();before_room_exit(p,s,Decision({'type':'cell','cell':25},'exit',Intent.DESCEND))
        p.room_loot_plan['steps']=32;s['hero']['cell']=23;p.loot.pop(23)
        with self.assertRaises(TacticalBlocked):before_room_exit(p,s,Decision({'type':'cell','cell':24},'exit',Intent.DESCEND))

    def test_rejected_next_target_rolls_back_owned_plan(self):
        s,p=self.encounter();before_room_exit(p,s,Decision({'type':'cell','cell':25},'exit',Intent.DESCEND))
        s['hero']['cell']=23;p.loot.pop(23);tx=Transaction(p)
        before_room_exit(p,s,Decision({'type':'cell','cell':24},'exit',Intent.DESCEND));tx.rollback()
        self.assertEqual(23,p.room_loot_plan['target'])
