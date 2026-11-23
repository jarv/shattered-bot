"""Run 000165: collected pool rewards must not reserve another invisibility dose."""
import copy
import unittest

from tools.loot_completion import observe_collected
from tools.piranha_tactics import pending
from tools.policy_decision import Decision, Intent
from tools.policy_geometry import distance
from tools.puzzle_supplies import demands
from tools.room_supplies import requirements
from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena


WATER = {667, 668, 669, 670, 671, 700, 701, 702, 703, 704,
         733, 734, 735, 736, 737, 766, 767, 769, 770}


def pool_pickup():
    # Minimal public geometry from decisions 112-116. This is a fixture,
    # not reconstructed runtime memory. Opening a chest is not collection.
    s, _ = arena()
    s["hero"].update(cell=768, hp=20, max_hp=20)
    s["map"] = {"width": 33, "height": 34, "cells": [
        {"cell": c, "terrain": 29 if c in WATER else 11,
         "visible": True, "observed": True}
        for c in sorted(WATER | {768})]}
    fish = [{"cell": c, "name": "giant piranha", "sleeping": True}
            for c in (670, 737, 769)]
    s["objects"] = fish + [{"cell": 768, "name": "Chest"}]
    p = verified()
    p.update(s)
    before = copy.deepcopy(s)
    before["objects"] = fish + [{"cell": 768, "name": "bolas x3",
                                "top_item": {"name": "bolas x3", "quantity": 3}}]
    p.update(before)
    after = copy.deepcopy(before)
    after["objects"] = fish
    after["inventory"].append({"id": "bolas", "name": "bolas x3",
                               "quantity": 3, "actions": ["THROW", "DROP"]})
    return before, after, p


class CollectedPoolSupplyTests(unittest.TestCase):
    def test_accepted_reward_pickup_releases_supply_but_not_habitat(self):
        before, after, p = pool_pickup()
        self.assertIn(768, pending(p))
        self.assertTrue(any(d.kind == "pool" for d in demands(p, before, distance)))
        observe_collected(p, before, Decision({"type": "cell", "cell": 768},
                          "collect reward", Intent.LOOT), after)
        p.update(after)
        self.assertNotIn(768, pending(p))
        blocked = set(p.room_blocked)
        actors = copy.deepcopy(p.room_actors)
        self.assertFalse(any(d.kind == "pool" for d in requirements(p, after)))
        self.assertEqual(blocked, p.room_blocked)
        self.assertEqual(actors, p.room_actors)
        self.assertTrue(WATER <= p.room_blocked)
        self.assertFalse(p.walkable(670))

    def test_reward_absence_without_inventory_receipt_keeps_reservation(self):
        before, after, p = pool_pickup()
        after["inventory"] = before["inventory"]
        observe_collected(p, before, Decision({"type": "cell", "cell": 768},
                          "collect reward", Intent.LOOT), after)
        p.update(after)
        self.assertIn(768, pending(p))
        self.assertTrue(any(d.kind == "pool" for d in requirements(p, after)))

    def test_unassociated_fish_still_requires_supply(self):
        before, after, p = pool_pickup()
        p.piranha_rooms[768]["collected"] = True
        p.room_actors[100] = {"cell": 100, "name": "giant piranha"}
        self.assertTrue(any(d.kind == "pool" and d.cell == 100
                            for d in demands(p, after, distance)))

    def test_pending_reward_in_same_habitat_keeps_reservation(self):
        before, after, p = pool_pickup()
        p.piranha_rooms[768]["collected"] = True
        p.piranha_rooms[733] = {"water": set(WATER), "collected": False}
        self.assertTrue(any(d.kind == "pool" for d in requirements(p, after)))


if __name__ == "__main__":
    unittest.main()
