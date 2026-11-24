"""Run 37: honor potion targets in bags and identify strength before leaving."""
import copy
import unittest
from unittest.mock import patch

from tools.challenge_rules import ChallengeRules
from tools.consumable_tactics import discovery_menu, choose_consumable, learn_sources
from tools.descent_potions import begin, advance, observe, PURPOSE
from tools.policy_decision import Decision, Intent, GameplayBlocked, PlannerStuck
from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.potion_stash import advance_stash, observe_accepted
from tools.puzzle_supplies import Demand
from tools.survival_policy import SurvivalPolicy
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.test_survival_bot import state


def ready(*, bag=True, water=True):
    s = state()
    s["map"] = {"width": 11, "height": 11, "cells": [
        {"cell": c, "terrain": 4 if c % 11 in {0, 10} or c // 11 in {0, 10} else 1,
         "visible": True, "observed": True, "effects": []} for c in range(121)]}
    s["hero"].update(cell=60, hp=30, max_hp=30, strength=10)
    if water:
        s["map"]["cells"][60]["terrain"] = 29
    p = verified()
    p.update(s)  # Observe acquisition of the protective bag, not a snapshot assumption.
    if bag:
        s["inventory"].append({"id": "bag", "name": "potion bandolier", "identified": True, "actions": []})
    s["inventory"].append(dict(potion("azure potion"), actions=["DRINK", "THROW", "DROP"]))
    p.update(s)
    return s, p


class IdentifyBagPriorityTests(unittest.TestCase):
    def test_run37_opens_potion_bandolier_before_visible_unknown_scroll(self):
        s, p = ready()
        s["inventory"].append({"id": "scroll", "name": "scroll of ODAL", "identified": False, "actions": ["READ"]})
        s["ui"] = {"texts": ["Identify an item"], "buttons": [
            {"id": "scroll-button", "label": "scroll of ODAL"},
            {"id": "bag-button", "label": "Potion Bandolier"}, {"id": "backpack", "label": "Backpack"}]}
        action = discovery_menu(p, s)
        self.assertEqual("bag-button", action.action["id"])
        self.assertFalse(p.strength_identified)
        s["ui"]["buttons"] = [{"id": "target", "label": "azure potion"}, {"id": "backpack", "label": "Backpack"}]
        self.assertEqual("target", discovery_menu(p, s).action["id"])

    def test_missing_bag_does_not_spend_identify_on_lower_priority_item(self):
        s, p = ready()
        s["inventory"].append({"id": "scroll", "name": "scroll of ODAL", "identified": False})
        s["ui"] = {"texts": ["Identify an item"], "buttons": [{"id": "scroll", "label": "scroll of ODAL"}]}
        self.assertEqual({"type": "back"}, discovery_menu(p, s).action)

    def test_other_identify_targets_still_work_when_no_unknown_potion_is_held(self):
        s, p = ready()
        s["inventory"] = [{"id": "scroll", "name": "scroll of ODAL", "identified": False}]
        s["ui"] = {"texts": ["Identify an item"], "buttons": [{"id": "scroll", "label": "scroll of ODAL"}]}
        self.assertEqual("scroll", discovery_menu(p, s).action["id"])


class StrengthBeforeDescentTests(unittest.TestCase):
    def test_no_strength_drink_testing_during_ordinary_exploration(self):
        s, p = ready()
        self.assertIsNone(advance(p, s))
        self.assertIsNone(choose_consumable(p, s, [], distance, neighbors))
        self.assertIsNone(p.descent_potion_plan)

    def test_admitted_descent_starts_testing_even_with_unvisited_optional_tiles(self):
        s, p = ready()
        s["map"]["cells"][93]["terrain"] = 8
        p.update(s)
        self.assertTrue(p.exploration_report(s, p.paths(s))["unvisited_reachable"])
        descent = Decision({"type": "cell", "cell": 93}, "stairs: descend", Intent.DESCEND)
        with patch.object(SurvivalPolicy, "choose", return_value=descent):
            action = p.choose(s)
        self.assertEqual("DRINK", action.action.get("action"))
        self.assertEqual(PURPOSE, action.potion_purpose)
        self.assertEqual("azure potion", action.action["id"])

    def test_mandatory_progression_pickup_blocks_descent_before_discovery_starts(self):
        s, p = ready()
        p.loot[91] = {"cell": 91, "name": "potion of strength", "top_item": potion("potion of strength")}
        descent = Decision({"type": "cell", "cell": 93}, "stairs: descend", Intent.DESCEND)
        with patch.object(SurvivalPolicy, "choose", return_value=descent):
            try:
                action = p.choose(s)
            except GameplayBlocked as blocked:
                self.assertIn("resource remains uncollected", blocked.reason)
            else:
                self.assertNotEqual(Intent.DESCEND, action.intent)
                self.assertNotEqual("DRINK", action.action.get("action"))
        self.assertIsNone(p.descent_potion_plan)

    def test_strict_unfinished_loot_does_not_admit_the_discovery_phase(self):
        s, p = ready()
        p.stop_on_incomplete_loot = True
        p.loot[91] = {"cell": 91, "name": "Tomb"}
        self.assertIsNone(begin(p, s))
        self.assertIsNone(p.descent_potion_plan)

    def test_prefers_water_over_current_dry_ground(self):
        s, p = ready(water=False)
        s["map"]["cells"][61]["terrain"] = 29
        p.update(s)
        action = begin(p, s)
        self.assertEqual({"type": "cell", "cell": 61}, action.action)
        self.assertEqual(61, p.descent_potion_plan["bank"])

    def test_no_safe_water_escape_blocks_descent_without_drinking(self):
        for kind in ("no-water", "trap"):
            s, p = ready(water=kind != "no-water")
            if kind == "trap":
                for tile in s["map"]["cells"]:
                    if tile["terrain"] != 4:
                        tile["trap"] = "dart trap"
            p.update(s)
            with self.assertRaises(PlannerStuck, msg=kind):
                begin(p, s)
            self.assertIsNotNone(p.descent_potion_plan)

    def test_no_discovery_spends_an_unfinished_room_supply_even_if_room_was_deferred(self):
        for kind, name in [("pool", "potion of invisibility"), ("frost", "potion of frost"),
                           ("sentry", "potion of haste"), ("flame", "potion of liquid flame"),
                           ("gas", "potion of purity"), ("flight", "potion of levitation")]:
            s, p = ready()
            from tools.objective_planning import exhaust_preparation
            exhaust_preparation(p,s,"test: preparation exhausted")
            with patch("tools.descent_potions.requirements", return_value=[Demand(kind, name, 90)]):
                with self.assertRaises(PlannerStuck):
                    begin(p, s)
            self.assertIsNotNone(p.descent_potion_plan)

    def test_health_threats_and_challenge_checks_are_not_bypassed(self):
        for kind in ("wounded", "starving", "poison", "enemy", "recent", "danger", "unseen", "challenge"):
            s, p = ready()
            if kind == "wounded": s["hero"]["hp"] = 20
            elif kind in {"starving", "poison"}: s["hero"]["buffs"] = [{"name": kind}]
            elif kind == "enemy": s["objects"] = [{"name": "marsupial rat", "cell": 61}]
            elif kind == "recent": p.recent_threats[61] = {"name": "marsupial rat", "cell": 61}
            elif kind == "danger": s["danger_cells"] = [60]
            elif kind == "unseen": p.unseen_damage_turns = 2
            elif kind == "challenge":
                p = verified(ChallengeRules(pharmacophobia=True)); p.update(s)
            with self.assertRaises(PlannerStuck, msg=kind):
                begin(p, s)

    def test_proposals_do_not_confirm_consumption_and_rejection_rolls_back_plan(self):
        s, p = ready()
        transaction = Transaction(p)
        action = begin(p, s)
        self.assertEqual("DRINK", action.action["action"])
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)
        transaction.rollback()
        self.assertIsNone(p.descent_potion_plan)
        self.assertIsNone(p.puzzle_probe)

    def test_confirmed_non_strength_drink_continues_to_next_color(self):
        s, p = ready()
        s["inventory"].append(dict(potion("jade potion"), actions=["DRINK", "DROP"]))
        p.update(s)
        first = begin(p, s)
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i["id"] != first.action["id"]]
        feedback = observe(p, s, first, after)
        self.assertFalse(feedback["strength_identified"])
        self.assertFalse(feedback["collection_credited"])
        self.assertIn(first.action["id"], p.descent_potion_tests)
        p.puzzle_probe = None
        p.update(after)
        second = advance(p, after)
        self.assertEqual("DRINK", second.action["action"])
        self.assertNotEqual(first.action["id"], second.action["id"])

    def test_actual_strength_identification_stops_testing_and_survives_floor_change(self):
        s, p = ready()
        s["inventory"].append(dict(potion("jade potion"), actions=["DRINK", "DROP"]))
        p.update(s)
        first = begin(p, s)
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i["id"] != first.action["id"]]
        after["hero"]["strength"] = 11
        self.assertTrue(observe(p, s, first, after)["strength_identified"])
        p.puzzle_probe = None
        p.update(after)
        self.assertIsNone(advance(p, after))
        after["depth"] = 2
        p.update(after)
        self.assertTrue(p.strength_identified)
        self.assertIsNone(begin(p, after))

    def test_visible_known_strength_identifies_but_floor_color_and_stack_clues_do_not(self):
        s, p = ready()
        p.consumable_sources["azure potion"] = {1, 2, 3, 4}
        s["inventory"][-1]["quantity"] = 4
        learn_sources(p, s)
        self.assertFalse(p.strength_identified)
        s["objects"] = [{"cell": 91, "name": "potion of strength", "top_item": potion("potion of strength")}]
        learn_sources(p, s)
        self.assertTrue(p.strength_identified)

    def test_missing_consumption_or_cancel_does_not_identify_strength(self):
        s, p = ready()
        action = begin(p, s)
        after = copy.deepcopy(s)
        after["hero"]["strength"] = 11
        self.assertIsNone(observe(p, s, action, after))
        self.assertFalse(p.strength_identified)
        self.assertIsNone(observe(p, s, Decision({"type": "back"}, "cancel"), after))
        self.assertFalse(p.descent_potion_tests)
        with self.assertRaises(GameplayBlocked):
            advance(p, after)

    def test_incomplete_observation_or_adrenaline_is_not_strength_identification(self):
        for kind in ("missing-inventory", "missing-strength", "adrenaline"):
            s, p = ready()
            action = begin(p, s)
            after = copy.deepcopy(s)
            after["inventory"] = [i for i in after["inventory"] if i["id"] != action.action["id"]]
            after["hero"]["strength"] = 11
            if kind == "missing-inventory":
                del after["inventory"]
            elif kind == "missing-strength":
                after["hero"]["strength"] = None
            else:
                after["hero"]["buffs"] = [{"name": "adrenaline surge"}]
            observe(p, s, action, after)
            self.assertFalse(p.strength_identified, kind)

    def test_stash_protects_other_potions_and_is_required_to_be_retrieved_after_test(self):
        s, p = ready(bag=False)
        s["inventory"].append(dict(potion("jade potion"), actions=["DRINK", "DROP"]))
        p.update(s)
        first = begin(p, s)
        self.assertNotEqual("DRINK", first.action.get("action"))
        self.assertEqual(PURPOSE, p.potion_stash["purpose"])
        self.assertEqual("azure potion", p.potion_stash["candidate"])
        self.assertFalse(p.descent_potion_tests)

    def test_stashed_potions_are_retrieved_even_when_the_test_finds_strength(self):
        s, p = ready(bag=False)
        s["inventory"].append(dict(potion("jade potion"), actions=["DRINK", "DROP"]))
        p.update(s)
        action = begin(p, s)
        drank = False
        for _ in range(70):
            if action is None:
                action = advance(p, s) or advance_stash(p, s, [], distance)
                if action is None:
                    break
            after = copy.deepcopy(s)
            after["observation_id"]=s.get("observation_id",0)+1
            if action.action["type"] == "cell":
                after["hero"]["cell"] = action.action["cell"]
                picked = [o for o in after["objects"] if o["cell"] == after["hero"]["cell"]]
                for o in picked:
                    after["inventory"].append(o["top_item"])
                    after["objects"].remove(o)
            elif action.action.get("action") == "DROP":
                item = next(i for i in after["inventory"] if i["id"] == action.action["id"])
                after["inventory"].remove(item)
                after["objects"].append({"cell": after["hero"]["cell"], "name": item["name"], "top_item": item})
            elif action.action.get("action") == "DRINK":
                after["inventory"] = [i for i in after["inventory"] if i["id"] != action.action["id"]]
                after["hero"]["strength"] = 11
                observe(p, s, action, after)
                p.puzzle_probe = None  # Synthetic drink had no harmful effects to recover.
                drank = True
            else:
                self.fail(action)
            observe_accepted(p, s, action, after)
            s = after
            p.update(s)
            action = None
        else:
            self.fail("Stash/return workflow failed to terminate")
        self.assertTrue(drank)
        self.assertTrue(p.strength_identified)
        self.assertIsNone(p.descent_potion_plan)
        self.assertIsNone(p.potion_stash)
        self.assertTrue(any(i["name"] == "jade potion" for i in s["inventory"]))
        self.assertFalse(s["objects"])

    def test_strength_discovered_by_a_room_test_also_stops_future_descent_testing(self):
        s, p = ready()
        action = Decision({"type": "item", "id": "azure potion", "action": "DRINK"}, "room test")
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i["id"] != "azure potion"]
        after["hero"]["strength"] = 11
        self.assertTrue(observe(p, s, action, after)["strength_identified"])
        self.assertFalse(p.descent_potion_tests)

    def test_effect_recovery_prevents_back_to_back_unknown_drinks(self):
        s, p = ready()
        action = begin(p, s)
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i["id"] != action.action["id"]]
        observe(p, s, action, after)
        self.assertIsNone(advance(p, after))
        self.assertIsNotNone(p.puzzle_probe)
