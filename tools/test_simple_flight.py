import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.simple_navigation import paths, observe, accepted
from tools.simple_flight import choose, recover
from tools.policy_decision import Finished
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state


def corridor():
    s = state()
    s["hero"].update(cell=36, hp=20, max_hp=20, buffs=[])
    s["inventory"].append({"id": "flight", "name": "potion of levitation", "actions": ["DRINK"]})
    s["map"] = {"width": 11, "height": 7, "cells": [
        {"cell": c, "terrain": 18 if c in {37, 38, 39} else 5 if c == 41
         else 1 if 34 <= c <= 40 else 4, "visible": True, "observed": True,
         **({"trap": "burning trap"} if c in {37, 38, 39} else {})} for c in range(77)]}
    s["objects"] = []
    p = MagePolicy(profile="simple-bot")
    p.challenges_verified = True
    p.update(s)
    return s, p


class SimpleFlightTests(unittest.TestCase):
    def test_known_potion_only_then_witnessed_buff_before_every_step(self):
        s, p = corridor()
        floor = observe(p, s)
        a = choose(p, s, [], floor, paths(p, s))
        self.assertEqual({"type": "item", "id": "flight", "action": "DRINK"}, a.action)
        self.assertEqual([36, 37, 38, 39, 40], floor["flight_transit"]["route"])
        self.assertEqual(0, floor["flight_transit"]["inputs"])
        with self.assertRaises(Finished):
            recover(p, s, [])
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 20."}]
        for cell in (37, 38, 39, 40):
            a = recover(p, s, [])
            self.assertEqual(cell, a.action["cell"])
            after = copy.deepcopy(s)
            after["hero"]["cell"] = cell
            accepted(p, s, a, after)
            s = after
            p.update(s)
        self.assertIsNone(recover(p, s, []))
        self.assertIsNone(floor["flight_transit"])
        self.assertFalse(p.loot_collection_receipts)

    def test_rejection_rolls_back_plan_and_unknown_potion_is_not_assumed_flight(self):
        s, p = corridor()
        transaction = Transaction(p)
        choose(p, s, [], observe(p, s), paths(p, s))
        transaction.rollback()
        self.assertFalse(observe(p, s).get("flight_transit"))
        s["inventory"][-1]["name"] = "silver potion"
        self.assertIsNone(choose(p, s, [], observe(p, s), paths(p, s)))

    def test_summoning_traps_unknown_landing_collateral_and_impairment_veto(self):
        for case in ("summoning", "unknown", "loot", "actor", "duration", "slow"):
            s, p = corridor()
            if case == "summoning":
                p.tiles[38]["trap"] = "summoning trap"
            elif case == "unknown":
                p.tiles[40]["observed"] = False
            elif case == "loot":
                p.loot[38] = {"name": "scroll of upgrade"}
            elif case == "actor":
                s["objects"] = [{"name": "sad ghost", "cell": 38}]
            if case in {"duration", "slow"}:
                choose(p, s, [], observe(p, s), paths(p, s))
                s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 1." if case == "duration"
                                      else "Turns remaining: 20."}]
                if case == "slow":s["hero"]["buffs"].append({"name": "slowed"})
                with self.assertRaises(Finished, msg=case):
                    recover(p, s, [])
            else:
                self.assertIsNone(choose(p, s, [], observe(p, s), paths(p, s)), case)

    def test_new_enemy_returns_to_bank_without_unprotected_trap_step(self):
        s, p = corridor()
        choose(p, s, [], observe(p, s), paths(p, s))
        s["hero"].update(cell=37, buffs=[{"name": "levitating", "description": "Turns remaining: 16."}])
        a = recover(p, s, [{"name": "rat", "cell": 41}])
        self.assertEqual(36, a.action["cell"])
        s["hero"]["cell"] = 36
        self.assertIsNone(recover(p, s, []))
