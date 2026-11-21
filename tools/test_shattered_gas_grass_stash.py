"""Run 79 D276: observed corridor/grass pocket, with unknown omitted terrain.

Synthetic subsequent observations exercise stash bookkeeping; they are not a
replay or a claim that an unknown color is purity.
"""
import copy
import unittest

from tools.test_shattered_strength_before_descent import ready
from tools.test_survival_bot import state
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.potion_stash import (stash_cells, stash_paths, can_protect_potions,
    protect_potions, advance_stash, fire_reaches_stash, storage_safe)
from tools.puzzle_supplies import safe_test_bank
from tools.policy_decision import Finished


def corridor():
    s = state()
    s["hero"].update(cell=241, hp=25, max_hp=25, strength=10, buffs=[])
    groups = {
        4: [211,212,213,214,242,267,268,270,326,328,354,356,382,384,410,412,438,440,466,468],
        5: [239],
        1: [240,241,269,299,495],
        2: [297,298,327,355,383,411],
        15: [439,467],
    }
    visible = {211,212,213,214,239,240,241,242,267,268,269,270,297,298,299,326,327,328,355,356}
    s["map"] = dict(width=28, height=48, cells=[
        dict(cell=c, terrain=t, visible=c in visible, observed=True, effects=[])
        for t, cells in groups.items() for c in cells])
    s["inventory"] = [
        dict(id="jade", name="jade potion", quantity=1, identified=False, actions=["DRINK", "DROP"]),
        dict(id="turquoise", name="turquoise potion x2", quantity=2, identified=False, actions=["DRINK", "DROP"]),
    ]
    s["objects"] = []
    p = verified()
    p.update(s)
    return s, p


class GasGrassStashTests(unittest.TestCase):
    def test_recorded_bank_keeps_drink_checks_but_accepts_fire_isolated_storage(self):
        s, p = corridor()
        self.assertTrue(safe_test_bank(p,s,241,distance,neighbors,allow_dry=True))
        self.assertFalse(safe_test_bank(p,s,327,distance,neighbors,allow_dry=True))
        self.assertTrue(storage_safe(p,s,241,327))
        self.assertFalse(fire_reaches_stash(p,s,241,327))
        cells = stash_cells(p,s,distance,neighbors,safe_test_bank)
        self.assertEqual([327,355], cells)
        self.assertEqual([241,269,298,327], p.route(stash_paths(p,s),327))
        self.assertTrue(can_protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank))
        self.assertFalse(p.strength_identified)

    def test_unknown_or_flammable_firebreak_is_not_certified(self):
        for kind in ("grass", "unknown", "plant"):
            s,p = corridor()
            if kind == "grass": p.tiles[299]["terrain"] = 2
            elif kind == "unknown": del p.tiles[299]
            else: p.tiles[299]["plant"] = "sungrass"
            self.assertTrue(fire_reaches_stash(p,s,241,327), kind)
            self.assertNotIn(327, stash_cells(p,s,distance,neighbors,safe_test_bank), kind)

    def test_hazardous_unseen_occupied_or_threatened_storage_is_rejected(self):
        for kind in ("trap", "plant", "effects", "unseen", "room", "danger", "actor", "loot"):
            s,p = corridor()
            if kind in ("trap", "plant", "effects"):
                p.tiles[327][kind] = ["fire"] if kind == "effects" else "hazard"
            elif kind == "unseen": p.tiles[327]["visible"] = False
            elif kind == "room": p.room_blocked.add(327)
            elif kind == "danger": s["danger_cells"] = [327]
            elif kind == "actor": s["objects"] = [dict(cell=355, name="marsupial rat")]
            else: p.loot[327] = dict(cell=327, name="gold")
            self.assertFalse(storage_safe(p,s,241,327), kind)

    def test_drop_whole_other_color_return_test_and_retrieve_without_crediting_identity(self):
        s,p = corridor()
        action = protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank)
        for _ in range(12):
            after = copy.deepcopy(s)
            if action.action["type"] == "cell":
                after["hero"]["cell"] = action.action["cell"]
            else:
                self.assertEqual("DROP", action.action["action"])
                item = next(i for i in after["inventory"] if i["id"] == action.action["id"])
                self.assertEqual("turquoise", item["id"])
                self.assertEqual(2, item["quantity"])
                after["inventory"].remove(item)
                after["objects"] = [dict(cell=327, name=item["name"], top_item=item)]
            p.update(after)
            s = after
            action = advance_stash(p,s,[],distance)
            if action is None:
                break
        self.assertEqual(241,s["hero"]["cell"])
        self.assertEqual("ready",p.potion_stash["phase"])
        self.assertEqual({"turquoise potion":2},p.potion_stash["dropped"])
        self.assertEqual(["jade"],[i["id"] for i in s["inventory"]])
        self.assertIsNone(protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank))
        # A synthetic failed test consumes jade, not the remote turquoise.
        s["inventory"] = []
        p.potion_stash["phase"] = "retrieve"
        p.update(s)
        for _ in range(8):
            action = advance_stash(p,s,[],distance)
            if action is None:
                break
            after = copy.deepcopy(s)
            after["hero"]["cell"] = action.action["cell"]
            if after["hero"]["cell"] == 327:
                after["inventory"] = [after["objects"][0]["top_item"]]
                after["objects"] = []
            p.update(after)
            s = after
        self.assertIsNone(p.potion_stash)
        self.assertEqual(2,s["inventory"][0]["quantity"])
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.room_journey)

    def test_new_arrival_hazard_or_new_fire_path_prevents_drop_or_test(self):
        s,p = corridor()
        protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank)
        s["hero"]["cell"] = 327
        p.tiles[327]["effects"] = ["fire"]
        with self.assertRaises(Finished):
            advance_stash(p,s,[],distance)
        s,p = corridor()
        p.potion_stash = dict(depth=1,bank=241,cell=327,candidate="jade potion",
                             phase="ready",steps=0,dropped={"turquoise potion":2},pending=None)
        s["inventory"] = s["inventory"][:1]
        p.tiles[299]["terrain"] = 2
        self.assertFalse(can_protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank))
        with self.assertRaises(Finished):
            protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank)

    def test_isolated_stack_remains_explicit_not_a_general_room_safety_bypass(self):
        s,p = corridor()
        candidate = s["inventory"][1]
        self.assertFalse(can_protect_potions(p,s,candidate,distance,neighbors,safe_test_bank))
        self.assertTrue(can_protect_potions(p,s,candidate,distance,neighbors,safe_test_bank,isolated_stack=True))
