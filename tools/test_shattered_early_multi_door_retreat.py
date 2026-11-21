"""Run 56: escape converging fronts before optional setup and open-room trading."""
import copy
import unittest

from tools import multi_enemy_tactics as multi
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena
from tools.test_survival_bot import state
from tools.test_unit_strategies import enemy
from tools.test_multi_enemy_and_fly_feedback import choke


def run56():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=1164, hp=23, max_hp=30, buffs=[])
    # Reduced observed approach to door 945 at decision 284. Unlisted cells
    # stay unknown; no far-side holding geometry or future enemy actions inferred.
    terrain = {1164: 6, 1163: 1, 1126: 1, 1089: 1, 1052: 1, 1015: 1, 980: 1,
               945: 5, 1053: 1, 1168: 1, 1169: 1}
    s["map"] = {"width": 36, "height": 43, "cells": [
        {"cell": c, "terrain": t, "visible": True, "observed": True, "effects": []}
        for c, t in terrain.items()]}
    s["objects"] = [enemy("gnoll scout", 1053), enemy("marsupial rat", 1168), enemy("marsupial rat", 1169)]
    p = verified()
    p.update(s)
    return s, p


class EarlyDoorRetreatTests(unittest.TestCase):
    def test_policy_tree_selects_retreat_before_charge_conservation(self):
        s, p = run56()
        action = p.choose(s)
        self.assertEqual("multi-threat-retreat", action.controller)
        self.assertEqual({"type": "cell", "cell": 1163}, action.action)

    def test_run56_converging_foes_trigger_retreat_before_two_attackers_are_adjacent(self):
        s, p = run56()
        self.assertEqual(0, sum(multi.can_attack(p, s, e, 1164) for e in s["objects"]))
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))
        action = multi.choose(p, s, s["objects"])
        self.assertEqual({"type": "cell", "cell": 1163}, action.action)
        self.assertEqual(Intent.RETREAT, action.intent)
        self.assertEqual(945, p.multi_door_plan["door"])
        self.assertIsNone(p.doorway_hold)

    def test_rule_preparation_yields_before_loot_ambush_or_charge_conservation(self):
        s, p = run56()
        self.assertIsNone(p.preparation(s, s["objects"]))
        self.assertIsNone(p.doorway_hold)
        self.assertIsNone(p.multi_door_plan)  # Arbitration is not a second hidden retreat selection.

    def test_nearest_admissible_door_is_preferred_over_open_room_retreat(self):
        s, p = arena()
        s["objects"] = [enemy("gnoll scout", 41), enemy("marsupial rat", 49)]
        for cell in (31, 10):
            next(t for t in s["map"]["cells"] if t["cell"] == cell)["terrain"] = 5
        p.update(s)
        action = multi.choose(p, s, s["objects"])
        self.assertEqual(31, p.multi_door_plan["door"])
        self.assertEqual({"type": "cell", "cell": 31}, action.action)
        self.assertIsNone(p.doorway_hold)

    def test_hazardous_nearest_door_is_not_selected_just_because_it_is_closest(self):
        s, p = arena()
        s["objects"] = [enemy("gnoll scout", 41), enemy("marsupial rat", 49)]
        for cell in (31, 10):
            next(t for t in s["map"]["cells"] if t["cell"] == cell)["terrain"] = 5
        p.update(s)
        p.tiles[31]["trap"] = "burning trap"
        action = multi.choose(p, s, s["objects"])
        self.assertIsNotNone(action)
        if p.multi_door_plan:
            self.assertEqual(10, p.multi_door_plan["door"])
        self.assertNotEqual(31, action.action.get("cell"))

    def test_accepted_opening_counts_but_proposals_and_rejections_do_not(self):
        s, p = arena()
        s["objects"] = [enemy("gnoll scout", 41), enemy("marsupial rat", 49)]
        next(t for t in s["map"]["cells"] if t["cell"] == 31)["terrain"] = 5
        p.update(s)
        tx = Transaction(p)
        multi.choose(p, s, s["objects"])
        tx.rollback()
        self.assertIsNone(p.multi_door_plan)
        action = multi.choose(p, s, s["objects"])
        action.controller = "multi-threat-retreat"
        self.assertEqual(0, p.multi_door_plan["steps"])
        after = copy.deepcopy(s)
        next(t for t in after["map"]["cells"] if t["cell"] == 31)["terrain"] = 6
        self.assertIsNotNone(multi.observe_accepted(p, s, action, after))
        self.assertEqual(1, p.multi_door_plan["steps"])
        self.assertIsNone(p.doorway_hold)

    def test_verified_single_file_hold_is_not_abandoned_for_another_door(self):
        s, p, foes = choke()
        s["hero"]["cell"] = 31
        self.assertTrue(multi.single_file(p, s, foes, 31))
        self.assertFalse(multi.needs_retreat(p, s, foes))

    def test_sleepers_and_distant_foes_do_not_start_unnecessary_flight(self):
        s, p = arena()
        for pos, foes in ((40, [enemy("gnoll scout", 41), enemy("marsupial rat", 49, sleeping=True)]),
                          (70, [enemy("gnoll scout", 10), enemy("marsupial rat", 16)])):
            s["hero"]["cell"] = pos
            self.assertFalse(multi.needs_retreat(p, s, foes))
