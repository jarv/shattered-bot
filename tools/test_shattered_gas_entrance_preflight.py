"""Reduced public gas-room geometry from run 000051, decisions 132-134.

Independent selector fixtures, not game replay or recorded runtime memory.
"""
import copy
import unittest

from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import stage_known_gas, prepare_supplies
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def approach(pos=166, door_visible=True, door_terrain=5):
    s = state()
    s["hero"].update(cell=pos, strength=10)
    gas = {80,81,82,83,84,106,107,108,109,110,132,133,134,135,136}
    s["map"] = {"width":26, "height":55, "cells":[
        {"cell":c, "terrain":t, "visible":v, "observed":True,
         "effects":["A greenish cloud of toxic gas is swirling here."] if c in gas else []}
        for c,t,v in ([(c,1,False) for c in sorted(gas)] +
                      [(111,door_terrain,door_visible)] +
                      [(c,29,True) for c in (112,138,139,140,166,192,218)])]}
    s["inventory"].append({"id":"purity", "name":"potion of purity",
        "identified":True, "quantity":1, "actions":["DROP","THROW","DRINK"]})
    p = verified()
    p.update(s)
    # Previously observed public chest, still unresolved behind remembered gas.
    p.loot[133] = {"cell":133, "name":"Chest"}
    return s,p


class GasEntrancePreflightTests(unittest.TestCase):
    def select(self,s,p):
        return stage_known_gas(p,s,s["inventory"][-1],neighbors)

    def assert_unspent(self,s,p,before):
        self.assertEqual(before,s)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        self.assertFalse(p.completed_room_rewards)
        self.assertIn(133,p.loot)
        self.assertIsNone(p.room_supply_permit)

    def test_bank_must_be_able_to_open_the_planned_entrance(self):
        s,p=approach()
        before=copy.deepcopy(s)
        d=self.select(s,p)
        self.assertIsNotNone(d, "Do not stop at bank 166 with an unactionable door")
        self.assertEqual({"type":"cell","cell":139},d.action)
        self.assert_unspent(s,p,before)

    def test_preparation_chain_does_not_fall_through_to_reverse_exploration(self):
        s,p=approach()
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(d)
        self.assertEqual({"type":"cell","cell":139},d.action)
        self.assertIsNone(p.room_journey)

    def test_adjacent_bank_opens_before_spending_purity(self):
        s,p=approach(pos=112)
        before=copy.deepcopy(s)
        d=self.select(s,p)
        self.assertEqual({"type":"cell","cell":111},d.action)
        self.assert_unspent(s,p,before)

    def test_unseen_entrance_declines_without_futile_staging(self):
        s,p=approach(pos=192,door_visible=False)
        before=copy.deepcopy(s)
        self.assertIsNone(self.select(s,p))
        self.assertEqual(0,p.puzzle_revisit_steps["gas"])
        self.assert_unspent(s,p,before)

    def test_trapped_entrance_is_not_a_staging_candidate(self):
        s,p=approach()
        p.tiles[111]["trap"]="burning trap"
        before=copy.deepcopy(s)
        self.assertIsNone(self.select(s,p))
        self.assert_unspent(s,p,before)

    def test_open_entrance_retains_existing_budget_and_actual_buff_requirement(self):
        s,p=approach(door_terrain=6)
        d=self.select(s,p)
        self.assertEqual({"type":"item","id":"purity","action":"DRINK"},d.action)
        self.assertEqual("gas",p.room_journey.kind)
        self.assertIn(133,p.loot)
        self.assertFalse(p.completed_room_rewards)
        # Selection is not a receipt of protection or reward acquisition.
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)
        self.assertIn(133,p.loot)


if __name__ == "__main__":
    unittest.main()
