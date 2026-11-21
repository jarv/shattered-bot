"""Reduced public geometry/inventory from run 000078, decision 275.

The sentry was observed at decision 109; the hero later carried clairvoyance
while departure discovery was vetoed by that still-incomplete enclosure.
No missing room tiles, reward or potion identities are supplied by this fixture.
"""
import copy
import unittest
from unittest.mock import patch

from tools.descent_potions import begin
from tools.policy_decision import PlannerStuck, Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.test_survival_bot import state


def incomplete_sentry():
    s = state()
    s["hero"].update(cell=516, hp=25, max_hp=25, strength=10, buffs=[])
    terrain = {516: 6, 477: 29, 438: 29, 439: 1,
               1194: 11, 1155: 14, 1116: 26, 1077: 26,
               1038: 26, 999: 26, 960: 25, 959: 1, 961: 1, 922: 6}
    s["map"] = {"width": 39, "height": 33, "cells": [
        dict(cell=c, terrain=t, observed=True, visible=c in {516, 477, 438, 439})
        for c, t in terrain.items()]}
    s["objects"] = []
    s["inventory"] += [
        dict(potion(name), id=f"color-{n}", actions=["DRINK", "DROP", "THROW"])
        for n, name in enumerate(("amber potion", "golden potion", "magenta potion"))]
    s["inventory"].append(dict(id="scry", name="stone of clairvoyance",
                               identified=True, quantity=1, actions=["THROW", "DROP"]))
    p = verified()
    p.update(s)
    # Remembered public actor, not a currently visible threat or a generated ID.
    p.room_actors[1194] = dict(cell=1194, name="red sentry")
    return s, p


def proposal(p, s):
    try:
        return begin(p, s)
    except PlannerStuck:
        return None


class SentryDiscoveryReconnaissanceTests(unittest.TestCase):
    def test_missing_room_supply_uses_known_reveal_instead_of_terminal_exhaustion(self):
        s, p = incomplete_sentry()
        before = copy.deepcopy(s)
        action = proposal(p, s)
        self.assertIsNotNone(action, "Incomplete sentry geometry must admit safe carried reconnaissance")
        self.assertEqual({"type": "item", "id": "scry", "action": "THROW"}, action.action)
        self.assertEqual(516, p.target)  # Stationary: no throw at a remembered actor.
        self.assertNotEqual(Intent.DESCEND, action.intent)
        self.assertEqual(before, s)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.mapped_floors)
        # A proposal with no new observation cannot spend more stones or drink.
        self.assertIsNone(proposal(p, s))

    def test_rollback_restores_reconnaissance_admission(self):
        s, p = incomplete_sentry()
        tx = Transaction(p)
        self.assertIsNotNone(proposal(p, s))
        tx.rollback()
        self.assertIsNotNone(proposal(p, s))

    def test_missing_resource_or_unsafe_current_state_stays_blocked(self):
        for kind in ("no-stone", "recent", "enemy", "danger", "damage",
                     "wounded", "immune", "invisible", "trap", "fire", "carpet"):
            with self.subTest(kind=kind):
                s, p = incomplete_sentry()
                if kind == "no-stone": s["inventory"].pop()
                elif kind == "recent": p.recent_threats[517] = {"cell": 517, "name": "marsupial rat"}
                elif kind == "enemy": s["objects"] = [{"cell": 517, "name": "marsupial rat"}]
                elif kind == "danger": s["danger_cells"] = [516]
                elif kind == "damage": p.unseen_damage_turns = 1
                elif kind == "wounded": s["hero"]["hp"] = 10
                elif kind in {"immune", "invisible"}:
                    s["hero"]["buffs"] = [{"name": "magic immunity" if kind == "immune" else "invisible"}]
                elif kind == "trap": p.tiles[516]["trap"] = "dart trap"
                elif kind == "fire": p.tiles[516]["effects"] = ["fire"]
                elif kind == "carpet": p.tiles[516]["terrain"] = 14
                self.assertIsNone(proposal(p, s))

    def test_no_reveal_when_complete_or_outside_conservative_reveal_radius(self):
        s, p = incomplete_sentry()
        with patch("tools.room_tactics.sentry_geometry", return_value=({1194}, 2)):
            self.assertIsNone(proposal(p, s))
        s, p = incomplete_sentry()
        s["hero"]["cell"] = 40
        p.tiles[40] = dict(cell=40, terrain=1, observed=True, visible=True)
        self.assertIsNone(proposal(p, s))


if __name__ == "__main__":
    unittest.main()
