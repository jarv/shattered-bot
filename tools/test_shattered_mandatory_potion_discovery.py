"""Run 57: no descent fall-through; isolate colors, including whole stacks."""
import copy
import unittest
from unittest.mock import patch

from tools.descent_potions import begin, advance, observe, PURPOSE
from tools.potion_stash import potions, can_protect_potions
from tools.policy_decision import Decision, Intent, PlannerStuck
from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.survival_policy import SurvivalPolicy
from tools.puzzle_supplies import Demand, safe_test_bank
from tools.test_consumable_tactics import potion
from tools.test_shattered_strength_before_descent import ready
from tools.challenge_rules import ChallengeRules
from tools.test_challenge_rules import verified


class MandatoryDiscoveryTests(unittest.TestCase):
    def test_stack_exception_does_not_weaken_room_specific_testing(self):
        s, p = ready(bag=False)
        s["inventory"][-1]["quantity"] = 2
        candidate = s["inventory"][-1]
        self.assertFalse(can_protect_potions(p, s, candidate, distance, neighbors, safe_test_bank))
        self.assertTrue(can_protect_potions(p, s, candidate, distance, neighbors, safe_test_bank,
                                            isolated_stack=True))

    def test_wait_proposal_rollback_does_not_spend_accepted_recovery_budget(self):
        s, p = ready()
        s["hero"]["buffs"] = [{"name": "levitating"}]
        transaction = Transaction(p)
        begin(p, s)
        transaction.rollback()
        self.assertIsNone(p.descent_potion_plan)
        action = begin(p, s)
        self.assertEqual(0, p.descent_potion_plan["waits"])
        observe(p, s, Decision({"type": "back"}, "cancel"), copy.deepcopy(s))
        self.assertEqual(0, p.descent_potion_plan["waits"])
        observe(p, s, action, copy.deepcopy(s))
        self.assertEqual(1, p.descent_potion_plan["waits"])

    def test_run57_levitation_preserves_plan_waits_and_resumes_before_exit(self):
        s, p = ready()
        s["inventory"].append(dict(potion("golden potion"), quantity=2, actions=["DRINK", "DROP"]))
        p.update(s)
        p.consumable_sources["azure potion"] = {1, 2, 3, 4}
        first = begin(p, s)
        after = copy.deepcopy(s)
        after["inventory"].remove(next(i for i in after["inventory"] if i["id"] == first.action["id"]))
        after["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 12."}]
        observe(p, s, first, after)
        p.puzzle_probe = None
        p.update(after)
        plan = p.descent_potion_plan
        action = begin(p, after)
        self.assertEqual({"type": "wait"}, action.action)
        self.assertIs(plan, p.descent_potion_plan)
        self.assertEqual(0, plan["waits"])
        observe(p, after, action, copy.deepcopy(after))
        self.assertEqual(1, plan["waits"])
        after["hero"]["buffs"] = []
        resumed = begin(p, after)
        self.assertEqual("DRINK", resumed.action.get("action"))
        self.assertEqual("golden potion", resumed.action["id"])

    def test_nonexpiring_effect_hits_accepted_wait_budget_instead_of_descending(self):
        s, p = ready()
        s["hero"]["buffs"] = [{"name": "levitating"}]
        for _ in range(64):
            action = begin(p, s)
            observe(p, s, action, copy.deepcopy(s))
        with self.assertRaises(PlannerStuck):
            begin(p, s)

    def test_actual_descent_gate_does_not_fall_through_on_unsafe_test_bank(self):
        s, p = ready(water=False)
        descent = Decision({"type": "cell", "cell": 93}, "stairs: descend", Intent.DESCEND)
        with patch.object(SurvivalPolicy, "choose", return_value=descent):
            with self.assertRaises(PlannerStuck) as raised:
                p.choose(s)
        self.assertIn("Cannot descend before potion discovery", raised.exception.blocker)

    def test_known_room_supply_does_not_blanket_block_other_unknown_colors(self):
        s, p = ready()
        s["inventory"].append(dict(potion("potion of liquid flame"), actions=["DRINK", "DROP"]))
        p.update(s)
        with patch("tools.descent_potions.requirements", return_value=[Demand("flame", "potion of liquid flame", 90)]):
            action = begin(p, s)
        self.assertEqual("azure potion", action.action["id"])
        self.assertEqual("DRINK", action.action["action"])
        self.assertFalse(p.room_supply_spent_elsewhere)

    def test_identify_scroll_precedes_risky_drinking_or_missing_room_supply_block(self):
        s, p = ready()
        s["inventory"].append({"id": "identify", "name": "scroll of identify", "actions": ["READ"]})
        with patch("tools.descent_potions.requirements", return_value=[Demand("gas", "potion of purity", 90)]):
            action = begin(p, s)
        self.assertEqual({"type": "item", "id": "identify", "action": "READ"}, action.action)
        self.assertEqual("discover-scroll", p.menu_plan)

    def test_pharmacophobia_can_identify_without_being_forced_to_drink(self):
        s, p = ready()
        p = verified(ChallengeRules(pharmacophobia=True))
        p.update(s)
        s["inventory"].append({"id": "identify", "name": "scroll of identify", "actions": ["READ"]})
        self.assertEqual("READ", begin(p, s).action["action"])

    def test_isolated_stacked_candidate_drops_every_other_color_and_retrieves_all(self):
        for frost in (False, True):
            s, p = ready(bag=False)
            s["inventory"][-1]["quantity"] = 2
            s["inventory"].append(dict(potion("yellow potion"), quantity=3, actions=["DRINK", "DROP"]))
            p.update(s)
            p.consumable_sources["azure potion"] = {1, 4}
            action = begin(p, s)
            drank = False
            for _ in range(60):
                if action is None:
                    action = advance(p, s)
                    if action is None:
                        break
                after = copy.deepcopy(s)
                if action.action["type"] == "cell":
                    after["hero"]["cell"] = action.action["cell"]
                    ground = next((o for o in after["objects"] if o["cell"] == after["hero"]["cell"]), None)
                    if ground:
                        after["inventory"].append(ground["top_item"])
                        after["objects"].remove(ground)
                elif action.action.get("action") == "DROP":
                    item = next(i for i in after["inventory"] if i["id"] == action.action["id"])
                    self.assertEqual("yellow potion", item["name"])
                    self.assertEqual(3, item["quantity"])
                    after["inventory"].remove(item)
                    after["objects"].append({"cell": after["hero"]["cell"], "name": item["name"], "top_item": item})
                elif action.action.get("action") == "DRINK":
                    if drank:
                        item = next(i for i in after["inventory"] if i["id"] == action.action["id"])
                        self.assertEqual("potion of strength", item["name"])
                        after["inventory"].remove(item)
                        p.update(after)
                        s = after
                        break
                    # Only the tested color remains; no imaginary split action.
                    self.assertEqual([("azure potion", 2)], [(i["name"], i["quantity"]) for i in potions(s)])
                    self.assertGreaterEqual(distance(s["hero"]["cell"], s["objects"][0]["cell"], 11), 3)
                    self.assertEqual(PURPOSE, action.potion_purpose)
                    item = next(i for i in after["inventory"] if i["id"] == action.action["id"])
                    if frost:
                        after["inventory"].remove(item)  # Worst case: remaining same-color frost also breaks.
                    else:
                        item.update(name="potion of strength", identified=True, quantity=1)
                        after["hero"]["strength"] = 11
                    self.assertFalse(observe(p, s, action, after)["collection_credited"])
                    p.puzzle_probe = None
                    drank = True
                else:
                    self.fail(str(action.action))
                p.update(after)
                s = after
                if drank and not p.potion_stash:
                    break
                action = None
            self.assertTrue(drank)
            self.assertIsNone(p.potion_stash)
            self.assertEqual(3, next(i["quantity"] for i in s["inventory"] if i["name"] == "yellow potion"))

    def test_remaining_known_strength_doses_cannot_be_carried_through_descent(self):
        s, p = ready()
        s["inventory"][-1].update(name="potion of strength", identified=True, quantity=2)
        p.update(s)
        self.assertTrue(p.strength_identified)
        action = begin(p, s)
        self.assertEqual("DRINK", action.action["action"])
        self.assertNotEqual(Intent.DESCEND, action.intent)
