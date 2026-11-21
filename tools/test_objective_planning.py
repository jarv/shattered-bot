"""Multi-input scheduling contracts; synthetic outcomes are not gameplay replay."""
import copy
import unittest
from unittest.mock import patch

from tools.objective_planning import Result, Status, available, resolve, mark, observe, exhausted
from tools.policy_decision import Decision, Intent, PlannerStuck
from tools.policy_runtime import Transaction
from tools.test_shattered_strength_before_descent import ready
from tools.test_shattered_descent_bank_revisit import fixture
from tools.descent_potions import begin, revisit_bank, potion_inventory
from tools.shop_tactics import visit_entrance_shop, ShopVisitBlocked
from tools.policy_geometry import neighbors
from tools.preparation_prerequisites import reconnaissance
from tools.puzzle_supplies import Demand
from tools.test_survival_bot import state
from tools.test_challenge_rules import verified


class ObjectiveContracts(unittest.TestCase):
    def test_declined_provider_cannot_leave_resource_claims_for_next_provider(self):
        _, p = ready()
        def declined():
            p.mapping_attempts.add(1)
            p.potion_stash = {"candidate": "uncommitted"}
            return Result(Status.BLOCKED, "route failed")
        def next_provider():
            self.assertFalse(p.mapping_attempts)
            self.assertIsNone(p.potion_stash)
            return Result(Status.BLOCKED, "resource unavailable")
        self.assertIsNone(resolve(p, "prepare", [("first", declined), ("second", next_provider)]))
        self.assertEqual(2, len(p.objective_results["prepare"]["prerequisites"]))

    def test_dependencies_report_declines_and_choose_next_admitted_action(self):
        s, p = ready()
        d = Decision({"type": "wait"}, "bounded recovery")
        result = resolve(p, "discovery", [
            ("stash", lambda: Result(Status.BLOCKED, "no route")),
            ("recover", lambda: available(d, "temporary effect")),
            ("unused", lambda: self.fail("do not plan beyond selected action")),
        ])
        self.assertIs(d, result)
        self.assertEqual(["blocked", "ready"],
                         [r["status"] for r in p.objective_results["discovery"]["prerequisites"]])

    def test_cycle_is_reported_without_recursion_or_success_credit(self):
        _, p = ready()
        def cycle():
            action = resolve(p, "a", [])
            return available(action, "cyclic dependency")
        self.assertIsNone(resolve(p, "a", [("b", cycle)]))
        self.assertEqual("blocked", p.objective_results["a"]["status"])
        self.assertFalse(p.objective_stack)

    def test_preempted_rejected_and_duplicate_inputs_do_not_spend_progress(self):
        s, p = ready()
        s["observation_id"] = 1
        tx = Transaction(p)
        d = mark(p, s, Decision({"type": "cell", "cell": 61}, "travel"), "travel", 62, [60, 61, 62])
        tx.rollback()
        self.assertFalse(p.objective_progress)
        after = copy.deepcopy(s)
        after["hero"]["cell"] = 61
        after["observation_id"] = 2
        self.assertIsNone(observe(p, s, Decision({"type": "wait"}, "combat preempted"), after))
        receipt = observe(p, s, d, after)
        self.assertEqual(1, receipt["accepted"])
        self.assertTrue(receipt["advanced"])
        self.assertIsNone(observe(p, s, d, after))
        self.assertEqual(1, p.objective_progress["travel"]["accepted"])

    def test_no_progress_and_total_budgets_are_independent_and_floor_scoped(self):
        s, p = ready()
        for i in range(8):
            d = mark(p, s, Decision({"type": "cell", "cell": 61}, "travel"), "travel", 62, [60, 61, 62])
            after = copy.deepcopy(s)
            after["observation_id"] = i+1
            observe(p, s, d, after)
        self.assertTrue(exhausted(p, "travel", 64))
        self.assertEqual(8, p.objective_progress["travel"]["accepted"])
        s["depth"] += 1
        p.update(s)
        self.assertFalse(p.objective_progress)
        self.assertFalse(p.objective_results)

    def test_opening_a_door_counts_as_progress_without_movement_or_completion(self):
        s, p = ready()
        s["map"]["cells"][61]["terrain"] = 5
        d = mark(p, s, Decision({"type": "cell", "cell": 61}, "open"), "travel", 62, [60, 61, 62])
        after = copy.deepcopy(s)
        after["map"]["cells"][61]["terrain"] = 6
        receipt = observe(p, s, d, after)
        self.assertTrue(receipt["opened"])
        self.assertFalse(receipt["advanced"])
        self.assertEqual(0, receipt["stagnant"])
        self.assertNotIn("complete", receipt)

    def test_missing_room_supplies_keep_exact_dependency_diagnostics(self):
        s, p = ready()
        with patch("tools.descent_potions.requirements", return_value=[Demand("gas", "potion of purity", 90)]), \
                patch("tools.puzzle_supplies.prepare_supplies", return_value=None):
            with self.assertRaises(PlannerStuck):
                begin(p, s)
        result = p.objective_results["potion-discovery"]
        self.assertEqual("exhausted", result["status"])
        self.assertEqual("potion of purity", result["prerequisites"][-1]["missing_supplies"][0]["potion"])
        self.assertEqual(0, result["prerequisites"][-1]["missing_supplies"][0]["held"])
        self.assertFalse(p.strength_identified)


class PreparationTransitTests(unittest.TestCase):
    def corridor(self):
        s = state()
        s["hero"].update(cell=26, hp=30, max_hp=30, buffs=[])
        s["map"] = dict(width=25, height=5, cells=[
            dict(cell=c, terrain=1 if 1 <= c % 25 <= 23 and c // 25 == 1 else 4,
                 observed=True, visible=True, effects=[]) for c in range(125)])
        s["inventory"] = [dict(id="golden", name="golden potion", quantity=1,
                               identified=False, actions=["DRINK", "DROP"])]
        p = verified()
        p.update(s)
        p.descent_potion_plan = dict(depth=s["depth"], steps=0, waits=0,
                                    candidate=None, bank=None, pending=False)
        p.descent_potion_bank_receipt = (s["depth"], 0, 46, potion_inventory(s))
        return s, p

    def test_long_transit_is_rechecked_one_input_at_a_time_then_requires_fresh_bank(self):
        s, p = self.corridor()
        for _ in range(20):
            d = revisit_bank(p, s, p.paths(s))
            self.assertIsNotNone(d)
            self.assertEqual(s["hero"]["cell"]+1, d.action["cell"])
            self.assertEqual("cell", d.action["type"])
            after = copy.deepcopy(s)
            after["hero"]["cell"] = d.action["cell"]
            observe(p, s, d, after)
            # Mirrors the existing accepted descent feedback's transit count.
            p.descent_potion_plan["return_steps"] = p.descent_potion_plan.get("return_steps", 0)+1
            p.update(after)
            s = after
        self.assertEqual(46, s["hero"]["cell"])
        self.assertFalse(p.strength_identified)
        # Remembered feasibility is never a licence to drink at this synthetic
        # arrival: it has no water and fails fresh admission.
        with self.assertRaises(PlannerStuck):
            begin(p, s)

    def test_transit_declines_when_hazard_or_resource_budget_changes(self):
        for kind in ("hazard", "hunger", "stagnation"):
            s, p = self.corridor()
            if kind == "hazard":
                p.tiles[27]["effects"] = ["toxic gas"]
                self.assertIsNone(revisit_bank(p, s, p.paths(s)))
            elif kind == "hunger":
                with patch("tools.hunger_budget.admits", return_value=False):
                    self.assertIsNone(revisit_bank(p, s, p.paths(s)))
            else:
                p.objective_progress["discovery-transit"] = dict(accepted=8, stagnant=8)
                self.assertIsNone(revisit_bank(p, s, p.paths(s)))

    def test_reconnaissance_is_a_prerequisite_not_hidden_identity_or_room_clearance(self):
        s, p = ready()
        p.tiles.pop(62)
        s["inventory"].append(dict(id="stone", name="stone of clairvoyance", actions=["THROW"]))
        action = reconnaissance(p, s)
        self.assertEqual({"type": "item", "id": "stone", "action": "THROW"}, action.action)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(reconnaissance(p, s))  # Bounded information resource use.


class PersistentShopTests(unittest.TestCase):
    def fixture(self):
        s, p = ready()
        s["depth"] = 6
        s["hero"]["cell"] = 60
        p.update(s)
        p.entrance_cell = 60
        p.shop_search_target = dict(target=64, reason="shop: reveal entrance chamber doors")
        return s, p

    def test_interrupted_search_retains_target_and_spends_only_accepted_inputs(self):
        s, p = self.fixture()
        action = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual(64, action.navigation_route[-1])
        self.assertEqual(0, p.entrance_visit_steps)
        after = copy.deepcopy(s)
        after["hero"]["cell"] = action.action["cell"]
        observe(p, s, action, after)
        p.update(after)
        self.assertEqual(1, p.entrance_visit_steps)
        # A combat input intervenes; it is not counted as shop exploration.
        observe(p, after, Decision({"type": "wait"}, "combat"), copy.deepcopy(after))
        resumed = visit_entrance_shop(p, after, p.paths(after), neighbors)
        self.assertEqual(64, resumed.navigation_route[-1])
        self.assertEqual(1, p.entrance_visit_steps)
        self.assertFalse(p.shop_visited_floors)

    def test_failed_target_replans_but_does_not_reset_total_budget(self):
        s, p = self.fixture()
        p.objective_progress["shop-target:64"] = dict(accepted=6, stagnant=6)
        p.entrance_visit_steps = 79
        p.tiles[62]["terrain"] = 5
        action = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertIn(64, p.shop_search_failed)
        self.assertEqual(79, p.entrance_visit_steps)
        after = copy.deepcopy(s)
        after["hero"]["cell"] = action.action["cell"]
        observe(p, s, action, after)
        p.update(after)
        with self.assertRaises(ShopVisitBlocked):
            visit_entrance_shop(p, after, p.paths(after), neighbors)
        self.assertEqual("exhausted", p.objective_results["entrance-shop"]["status"])

    def test_current_hazard_invalidates_commitment_instead_of_forcing_step(self):
        s, p = self.fixture()
        p.tiles[61]["effects"] = ["fire"]
        p.tiles[64]["effects"] = ["fire"]
        p.tiles[62]["terrain"] = 5
        action = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertNotEqual(61, action.action["cell"])
        self.assertNotEqual(64, p.shop_search_target["target"])
