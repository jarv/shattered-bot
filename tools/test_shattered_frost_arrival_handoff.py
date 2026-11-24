"""Reduced public run 000245 D510 arrival; no gameplay or runtime-memory replay."""
import unittest

from tools.policy_geometry import distance, neighbors
from tools.priority_resources import choose, targets
from tools.puzzle_supplies import prepare_supplies
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def arrival():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=337, hp=24, max_hp=25, strength=11, buffs=[])
    # Observed throwing bank and fire face at D510 (log line 1401).
    terrain = {
        152: 14, 153: 14, 154: 1, 155: 1, 156: 1,
        196: 14, 197: 14, 198: 14, 199: 1, 200: 1, 201: 1,
        241: 14, 242: 14, 243: 14, 244: 1, 245: 1, 246: 1,
        286: 14, 287: 14, 288: 14, 289: 1, 290: 1, 291: 1,
        331: 14, 332: 14, 333: 14, 334: 29, 335: 1, 336: 1,
        337: 6, 338: 29, 339: 29,
        376: 14, 377: 14, 378: 14, 379: 29, 380: 29, 381: 29,
    }
    fires = {198, 243, 288, 333, 378}
    s["map"] = {"width": 45, "height": 33, "cells": [
        dict(cell=c, terrain=t, observed=True,
             visible=c in fires or c in {334, 335, 336, 337, 338, 339},
             effects=["A wall of magical fire"] if c in fires else [])
        for c, t in terrain.items()]}
    s["objects"] = []
    s["inventory"] = [dict(id="item-10", name="potion of frost",
                           identified=True, quantity=1,
                           actions=["DROP", "THROW", "DRINK"]),
                      dict(id="item-0", name="staff of magic missile +1",
                           identified=True, equipped=True, status="3/5",
                           actions=["ZAP", "IMBUE"])]
    p = verified()
    p.update(s)
    # Explicit reduced bookkeeping, not originally recorded memory. Public
    # pasty sighting is cached; its pickup is still excluded by the fire.
    p.loot[152] = dict(cell=152, name="pasty",
                       top_item=dict(name="pasty", identified=True))
    p.room_attempts.add((2, "puzzle-meal"))
    return s, p


class FrostArrivalHandoffTests(unittest.TestCase):
    def test_priority_food_preparation_finishes_at_visible_fire(self):
        s, p = arrival()
        self.assertIn(152, targets(p))
        self.assertNotIn(152, p.paths(s))
        d = choose(p, s, [])
        self.assertIsNotNone(d, "Known-frost scouting must hand off to the visible-fire throw")
        self.assertEqual(dict(type="item", id="item-10", action="THROW"), d.action)
        self.assertEqual(198, p.target)
        self.assertGreaterEqual(distance(337, p.target, 45), 3)
        self.assertTrue(p.shot_clear(s, p.target))
        self.assertIn(152, p.loot)
        self.assertFalse(p.cleared_floors)
        self.assertFalse(p.barrier_followup.get("cleared"))
        self.assertNotIn(198, p.paths(s))

    def test_supply_leaf_also_hands_off_without_claiming_pickup(self):
        s, p = arrival()
        d = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(d)
        self.assertEqual("THROW", d.action["action"])
        self.assertIn(152, p.loot)

    def test_full_selector_uses_priority_preparation_at_arrival(self):
        s, p = arrival()
        d = p.choose(s)
        self.assertEqual(dict(type="item", id="item-10", action="THROW"), d.action)
        self.assertEqual("priority-progression-pickup", d.controller)
        self.assertIn(152, p.loot)

    def test_existing_safety_and_workflow_gates_remain(self):
        for condition in ("enemy", "recent", "danger", "unknown", "shot",
                          "burning", "probe", "stash", "journey", "budget"):
            with self.subTest(condition=condition):
                s, p = arrival()
                enemies = []
                if condition == "enemy":
                    enemies = [dict(name="marsupial rat", cell=338)]
                elif condition == "recent":
                    p.recent_threats[338] = dict(name="marsupial rat", cell=338)
                elif condition == "danger":
                    s["danger_cells"] = [337]
                elif condition == "unknown":
                    s["inventory"][0].update(name="turquoise potion", identified=False,
                                              actions=["THROW"])
                elif condition == "shot":
                    p.shot_clear = lambda *args: False
                elif condition == "burning":
                    s["hero"]["buffs"] = [dict(name="burning")]
                elif condition == "budget":
                    p.puzzle_revisit_steps["frost"] = 48
                else:
                    setattr(p, {"probe": "puzzle_probe", "stash": "potion_stash",
                                "journey": "room_journey"}[condition], {"active": True})
                self.assertIsNone(choose(p, s, enemies))
                self.assertIn(152, p.loot)
                self.assertIsNone(p.target)


if __name__ == "__main__":
    unittest.main()
