"""Run 54 public geometry and synthetic random outcomes, never a game replay."""
import copy
import unittest
from unittest.mock import patch

from tools.vertigo_tactics import choose, observe, MAX_MOVES, MAX_WAITS
from tools.policy_decision import PlannerStuck, Decision
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state, fully_known


GAS = "A cloud of confusion gas is swirling here."


def vertigo(turns=2):
    return {"name": "vertigo", "description": f"Turns of vertigo remaining: {turns}."}


def run54():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=790, hp=30, max_hp=30, buffs=[{"name": "hungry"}, vertigo()])
    # All eight neighbors from the first gas observation at decision 651.
    terrain = {743: 4, 744: 1, 745: 4, 789: 4, 790: 19, 791: 1, 835: 4, 836: 4, 837: 1}
    s["map"] = {"width": 46, "height": 28, "cells": [
        {"cell": c, "terrain": t, "visible": True, "observed": True,
         "effects": [GAS] if c in {744, 790, 791} else [],
         **({"trap": "confusion gas trap"} if c == 790 else {})} for c, t in terrain.items()]}
    p = verified()
    p.update(s)
    return s, p


def clear_room():
    s = fully_known(state())
    s["hero"]["buffs"] = [vertigo()]
    p = verified()
    p.update(s)
    return s, p


class VertigoResponseTests(unittest.TestCase):
    def test_policy_tree_selects_vertigo_before_optional_preparation(self):
        s, p = run54()
        action = p.choose(s)
        self.assertEqual("vertigo-response", action.controller)
        self.assertEqual({"type": "cell", "cell": 837}, action.action)

    def test_run54_first_gas_observation_selects_single_escape_not_forty_waits(self):
        s, p = run54()
        action = choose(p, s)
        self.assertEqual({"type": "cell", "cell": 837}, action.action)
        self.assertEqual([744, 791, 837], p.planner.report["vertigo_response"]["possible_landings"])
        self.assertTrue(p.planner.report["vertigo_response"]["random_direction"])
        self.assertFalse(action.movement_batch)
        self.assertEqual(0, p.vertigo_plan["moves"])

    def test_every_possible_direction_is_checked_not_only_the_requested_exit(self):
        for kind in ("pit", "trap", "toxic", "plant", "unknown", "door", "warning"):
            s, p = run54()
            tile = p.tiles[791]
            if kind == "pit": tile.update(terrain=0, effects=[])
            elif kind == "trap": tile.update(terrain=18, trap="dart trap")
            elif kind == "toxic": tile["effects"] = ["A cloud of toxic gas"]
            elif kind == "plant": tile["plant"] = "stormvine"
            elif kind == "unknown": tile["visible"] = False
            elif kind == "door": tile.update(terrain=5, effects=[])
            else: s["danger_cells"] = [791]
            with self.assertRaises(PlannerStuck, msg=kind):
                choose(p, s)

    def test_accepted_unexpected_landing_and_wall_bump_are_not_miscredited(self):
        for landing in (744, 790):
            s, p = run54()
            action = choose(p, s)
            after = copy.deepcopy(s)
            after["hero"]["cell"] = landing
            receipt = observe(p, s, action, after)
            self.assertFalse(receipt["moved_as_requested"])
            self.assertEqual(landing, receipt["actual_cell"])
            self.assertEqual(1, receipt["moves"])
            self.assertEqual(0, p.visits[837])
            self.assertIsNone(observe(p, s, action, after))

    def test_rejected_proposal_and_floor_reset_do_not_spend_escape_budget(self):
        s, p = run54()
        transaction = Transaction(p)
        choose(p, s)
        transaction.rollback()
        self.assertIsNone(p.vertigo_plan)
        self.assertIsNone(p.vertigo_pending)
        choose(p, s)
        p.memory.reset_floor(3)
        self.assertIsNone(p.vertigo_plan)

    def test_outside_gas_waits_for_observed_declining_duration_then_resumes(self):
        s, p = clear_room()
        for remaining in (1, 0):
            action = choose(p, s)
            self.assertEqual("wait", action.action["type"])
            after = copy.deepcopy(s)
            after["hero"]["buffs"] = [vertigo(remaining)] if remaining else []
            observe(p, s, action, after)
            s = after
        self.assertIsNone(choose(p, s))
        self.assertIsNone(p.vertigo_plan)

    def test_two_refreshes_outside_reported_gas_trigger_reassessment_not_idle_loop(self):
        s, p = clear_room()
        for _ in range(2):
            action = choose(p, s)
            self.assertEqual("wait", action.action["type"])
            observe(p, s, action, copy.deepcopy(s))
        self.assertEqual("cell", choose(p, s).action["type"])

    def test_unknown_duration_waits_and_random_escape_both_have_finite_budgets(self):
        s, p = run54()
        for _ in range(MAX_MOVES):
            action = choose(p, s)
            observe(p, s, action, copy.deepcopy(s))
        with self.assertRaises(PlannerStuck):
            choose(p, s)
        s, p = clear_room()
        s["hero"]["buffs"] = [{"name": "vertigo"}]
        for _ in range(MAX_WAITS):
            action = choose(p, s)
            self.assertEqual("wait", action.action["type"])
            observe(p, s, action, copy.deepcopy(s))
        self.assertNotEqual("wait", choose(p, s).action["type"])

    def test_known_purity_is_used_but_immunity_is_not_inferred_from_the_proposal(self):
        s, p = run54()
        s["inventory"].append({"id": "purity", "name": "potion of purity", "quantity": 2, "actions": ["DRINK"]})
        action = choose(p, s)
        self.assertEqual({"type": "item", "id": "purity", "action": "DRINK"}, action.action)
        self.assertEqual("emergency", action.potion_purpose)
        self.assertFalse(p.vertigo_plan["waits"])
        s["hero"]["buffs"].append({"name": "purification barrier", "description": "Turns remaining: 20."})
        self.assertEqual("wait", choose(p, s).action["type"])

    def test_safe_short_residual_vertigo_does_not_waste_blink(self):
        s, p = clear_room()
        s["inventory"].append({"id": "blink", "name": "stone of blink", "actions": ["THROW"]})
        self.assertEqual("wait", choose(p, s).action["type"])

    def test_reserved_purity_is_preserved_for_free_escape_and_receipted_as_emergency_otherwise(self):
        for blocked in (False, True):
            s, p = run54()
            s["inventory"].append({"id": "purity", "name": "potion of purity", "actions": ["DRINK"]})
            if blocked:
                p.tiles[791]["terrain"] = 0
            # Model the shared reservation veto; only the explicit emergency
            # permit may bypass it, never a guessed room-completion flag.
            with patch.object(p, "item_action_allowed", side_effect=lambda *_: bool(p.room_supply_permit)):
                action = choose(p, s)
            self.assertEqual("item" if blocked else "cell", action.action["type"])
            if blocked:
                self.assertEqual("emergency", action.potion_purpose)
            self.assertFalse(p.room_supply_spent_elsewhere)

    def test_unknown_potions_do_not_become_escape_items(self):
        s, p = run54()
        p.tiles[791]["terrain"] = 0
        s["inventory"].append({"id": "unknown", "name": "azure potion", "actions": ["DRINK"]})
        with self.assertRaises(PlannerStuck):
            choose(p, s)

    def test_mixed_damaging_cloud_is_never_a_random_walk_or_safe_wait(self):
        s, p = run54()
        p.tiles[790]["effects"].append("A cloud of toxic gas")
        with self.assertRaises(PlannerStuck):
            choose(p, s)

    def test_changed_or_cancelled_action_is_not_an_escape_receipt(self):
        s, p = run54()
        choose(p, s)
        self.assertIsNone(observe(p, s, Decision({"type": "back"}, "cancel"), copy.deepcopy(s)))
        self.assertEqual(0, p.vertigo_plan["moves"])
