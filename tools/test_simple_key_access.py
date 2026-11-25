import copy
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.simple_navigation import choose, before_descent, accepted, observe
from tools.policy_decision import Decision, Intent
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state


def rooms(kind="iron"):
    s = state()
    w = 11
    floor = {r*w+c for r in range(2, 5) for c in (1, 2, 3, 5, 6, 7)}
    floor.add(37)  # Door in dividing wall (row 3, column 4).
    s["map"] = {"width": w, "height": 7, "cells": [
        {"cell": c, "terrain": (10 if kind == "iron" else 31) if c == 37 else 8 if c == 23
         else 1 if c in floor else 4, "observed": True, "visible": True}
        for c in range(77)]}
    s["hero"].update(cell=36, level=2)
    s["keys"] = [{"name": f"{kind} key", "depth": 1, "quantity": 1}]
    s["objects"] = []
    p = MagePolicy(profile="simple-bot")
    p.challenges_verified = True
    p.update(s)
    s["hero"]["level"] = 3
    p.update(s)
    return s, p


def unlock(s, p):
    action = choose(p, s, [])
    assert action.action == {"type": "cell", "cell": 37}
    after = copy.deepcopy(s)
    after["keys"] = []
    next(t for t in after["map"]["cells"] if t["cell"] == 37)["terrain"] = 5
    accepted(p, s, action, after)
    p.update(after)
    return after


class SimpleKeyAccessTests(unittest.TestCase):
    def test_unlock_then_enter_then_inside_then_loot_before_descent(self):
        for kind in ("iron", "crystal"):
            s, p = rooms(kind)
            after = unlock(s, p)
            self.assertEqual(36, after["hero"]["cell"])  # Unlock did not move.
            entry = before_descent(p, after, Decision({"type": "cell", "cell": 23},
                                                     "leave", Intent.DESCEND))
            self.assertEqual(37, entry.action["cell"])
            self.assertIn("enter and inspect", entry.reason)
            crossed = copy.deepcopy(after)
            crossed["hero"]["cell"] = 37
            next(t for t in crossed["map"]["cells"] if t["cell"] == 37)["terrain"] = 6
            accepted(p, after, entry, crossed)
            p.update(crossed)
            inside = choose(p, crossed, [])
            self.assertNotEqual(Intent.DESCEND, inside.intent)
            self.assertIn(inside.action["cell"], {27, 38, 49})
            reached = copy.deepcopy(crossed)
            reached["hero"]["cell"] = inside.action["cell"]
            reached["objects"] = [{"name": "gold", "cell": 39, "top_item": {"name": "gold"}}]
            accepted(p, crossed, inside, reached)
            p.update(reached)
            self.assertEqual(Intent.LOOT, choose(p, reached, []).intent)
            reached["objects"] = []
            p.update(reached)
            p.loot.clear()
            p.unconfirmed_loot.clear()
            self.assertEqual(Intent.DESCEND, choose(p, reached, []).intent)

    def test_rejected_unlock_has_no_entry_receipt_and_transaction_rolls_back(self):
        s, p = rooms()
        action = choose(p, s, [])
        accepted(p, s, action, s)
        self.assertFalse(observe(p, s).get("key_entries"))
        transaction = Transaction(p)
        unlock(s, p)
        transaction.rollback()
        self.assertFalse(observe(p, s).get("key_entries"))

    def test_held_key_requests_bounded_ordinary_exploration_after_level_gain(self):
        s, p = rooms()
        p.tiles[37]["terrain"] = 4
        p.tiles[35]["terrain"] = 5
        p.visits[35] = 0
        action = choose(p, s, [])
        self.assertIn("seek ordinary matching lock", action.reason)
        self.assertEqual(Intent.EXPLORE, action.intent)
        observe(p, s)["key_search_inputs"] = 64
        self.assertEqual(Intent.DESCEND, choose(p, s, []).intent)

    def test_blocked_new_room_is_logged_not_claimed_entered(self):
        s, p = rooms()
        after = unlock(s, p)
        p.blocked.add(37)
        with patch("tools.descent_potions.begin", return_value=None):
            action = before_descent(p, after, Decision(
                {"type": "cell", "cell": 23}, "leave", Intent.DESCEND))
        self.assertEqual(Intent.DESCEND, action.intent)
        plan = observe(p, after)["key_entries"][0]
        self.assertFalse(plan["inside"])
        self.assertIn("deferred", plan["result"])
        self.assertTrue(p.deferred_obligations)
