import copy
import unittest

from tools.decision_engine import DecisionEngine, Goal, RiskModel, source_revision
from tools.survival_bot import SurvivalPolicy, Finished, Intent, distance, line_clear, neighbors
from tools.test_survival_bot import state, fully_known


class DecisionEngineTests(unittest.TestCase):
    def test_survival_is_default_and_legacy_comparator_remains_available(self):
        self.assertEqual("survival", SurvivalPolicy().goal)
        self.assertEqual("planner", SurvivalPolicy(engine="planner").engine)
        with self.assertRaises(ValueError):
            SurvivalPolicy(engine="other")

    def test_ordinary_combat_uses_scored_candidates_and_explains_alternatives(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        s["objects"] = [{"cell": 25, "name": "gnoll scout"}]
        d = p.choose(s)
        self.assertTrue(d.reason.startswith("combat: planner"), d.reason)
        self.assertIn("risk", p.planner.report)
        self.assertGreater(len(p.planner.report["alternatives"]), 1)

    def test_risk_accounts_for_low_hp_and_action_duration_without_enemy_stats(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        enemies = [{"cell": 25, "name": "gnoll scout"}]
        p.update(s)
        healthy = RiskModel(p, s, enemies, distance, line_clear)
        s["hero"]["hp"] = 4
        wounded = RiskModel(p, s, enemies, distance, line_clear)
        self.assertGreater(wounded.cost(24), healthy.cost(24))
        self.assertGreater(wounded.cost(24, 2), wounded.cost(24))

    def test_private_looking_extra_fields_do_not_change_policy_choice(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "gnoll scout"}]
        a = SurvivalPolicy(engine="planner").choose(s)
        modified = copy.deepcopy(s)
        modified["objects"][0].update(hp=9999, attack_damage=9999, alignment="friendly")
        b = SurvivalPolicy(engine="planner").choose(modified)
        self.assertEqual(a.action, b.action)

    def test_combat_goal_survives_visibility_loss_and_nearby_loot(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        s["objects"] = [{"cell": 26, "name": "gnoll scout"}]
        p.update(s)
        p.planner.goal = Goal("combat", 26, 1, "explore: continue last-seen combat approach")
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = False
        s["objects"] = [{"cell": 23, "name": "potion", "top_item": {"name": "potion"}}]
        d = p.choose(s)
        self.assertEqual("explore: continue last-seen combat approach", d.reason)
        self.assertEqual(Intent.EXPLORE, d.intent)
        self.assertEqual(1, distance(d.action["cell"], 26, 7))
        self.assertIsNone(p.target)
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = True
        p.choose(s)
        self.assertNotEqual("combat", p.planner.goal.kind if p.planner.goal else None)

    def test_goal_navigation_has_a_budget_and_does_not_cross_floors(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        p.update(s)
        p.planner.goal = Goal("explore", 26, 1, "explore: frontier", remaining=0)
        self.assertIsNone(p.planner.continue_navigation(p, s, []))
        p.planner.goal = Goal("explore", 26, 2, "explore: frontier")
        self.assertIsNone(p.planner.continue_navigation(p, s, []))

    def test_goal_continuation_never_opens_an_unplanned_purchase(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        s["objects"] = [{"cell": 25, "name": "potion of healing", "for_sale": True,
                         "top_item": {"name": "potion of healing"}, "price": 100}]
        p.update(s)
        p.planner.goal = Goal("shop", 25, 1, "shop: buy priority supplies")
        self.assertIsNone(p.planner.continue_navigation(p, s, []))

    def test_recovery_feeds_wounded_hungry_hero_before_more_exploration(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        s["hero"].update(hp=10, buffs=[{"name": "hungry"}])
        s["inventory"].append({"id": "food", "name": "ration of food", "actions": ["EAT"]})
        self.assertEqual("food", p.choose(s).action["id"])
        self.assertEqual("recover: planned meal before further exploration", p.last_decision.reason)

    def test_recovery_budget_is_per_floor_not_reset_by_navigation(self):
        s, p = fully_known(state()), SurvivalPolicy(engine="planner")
        s["hero"]["hp"] = 10
        p.update(s)
        for _ in range(80):
            self.assertEqual("wait", p.planner.recover(p, s, []).action["type"])
        self.assertIsNone(p.planner.recover(p, s, []))
        s["depth"] = 2
        p.update(s)
        self.assertEqual(0, p.planner.recovery_waits)

    def test_unknown_wand_charges_are_not_counted_as_known_reserves(self):
        s, p = state(), SurvivalPolicy(engine="planner")
        s["inventory"][0]["status"] = "?/4"
        ledger = DecisionEngine.resources(p, s)
        self.assertEqual(0, ledger["known_usable_charges"])
        self.assertEqual(1, ledger["unknown_charge_wands"])

    def test_boss_charge_safety_preempts_the_new_planner(self):
        s = state()
        s.update(depth=5, boss_health_text="40/100", danger_cells=[23, 24, 25])
        s["objects"] = [{"cell": 25, "name": "Goo"}]
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in {24, 25} else 4, "visible": True}
                             for c in range(49)]
        with self.assertRaises(Finished):
            SurvivalPolicy(engine="planner").choose(s)

    def test_revision_is_stable_for_unchanged_source(self):
        self.assertEqual(source_revision(), source_revision())
        self.assertEqual(16, len(source_revision()))


if __name__ == "__main__":
    unittest.main()
