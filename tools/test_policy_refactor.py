"""Architecture contracts and a deterministic pre-refactor decision fingerprint."""
import contextlib
import copy
from dataclasses import fields
import hashlib
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from tools.policy_decision import Decision, Finished, Intent
from tools.policy_interaction import MenuPhase, MENU_HANDLERS
from tools.policy_memory import PolicyMemory
from tools.policy_runtime import Context, Leaf, Selector, Transaction
from tools.policy_runner import run, rejected_before_execution
from tools.player_api import PlayerAPIError
from tools.survival_policy import SurvivalPolicy, NavigationLoopGuard, MenuLoopGuard
from tools.test_survival_bot import state, fully_known


def observations():
    """Synthetic observations, not a simulator or a claim about win rates."""
    rng = random.Random(20261112)
    names = ["marsupial rat", "sewer snake", "wraith", "sewer crab", "skeleton", "necromancer", "gnoll shaman"]
    for index in range(192):
        s = fully_known(state())
        s["depth"] = rng.choice([1, 2, 4, 5, 6, 11])
        s["hero"]["hp"] = rng.randint(1, 20)
        buff = rng.choice([None, "hungry", "starving", "caustic ooze", "invisibility", "burning"])
        s["hero"]["buffs"] = [{"name": buff}] if buff else []
        count = rng.randrange(5)
        s["inventory"][0]["status"] = f"{count}/4"
        if count == 0:
            s["inventory"][0]["actions"] = ["IMBUE"]
        extras = [("ration of food", ["EAT"]), ("potion of healing", ["DRINK"]),
                  ("scroll of upgrade", ["READ"]), ("potion of strength", ["DRINK"])]
        for number, (name, actions) in enumerate(extras):
            if rng.choice([False, True]):
                s["inventory"].append({"id": f"extra-{number}", "name": name, "actions": actions})
        for cell in rng.sample([16, 17, 18, 23, 25, 26, 30, 31, 32], rng.randrange(4)):
            s["objects"].append({"cell": cell, "name": rng.choice(names),
                                 "sleeping": rng.randrange(4) == 0, "health_bar": [rng.randint(1, 10), 10]})
        if s["depth"] == 5 and index % 2:
            s["objects"] = [{"cell": 26, "name": "goo", "health_bar": [8, 10]}]
            s["boss_health_text"] = "80/100"
        for tile in s["map"]["cells"]:
            if tile["cell"] in {16, 32}:
                tile["terrain"] = 29
            if tile["cell"] == 40:
                tile["terrain"] = 8
        if index % 7 == 0:
            s["danger_cells"] = [24, 25]
        if index % 11 == 0:
            s["hero"]["talents"] = [{"name": "backup barrier", "points": 0, "max_points": 2, "available": 1}]
        yield s


def decision_matrix(policy_class=SurvivalPolicy, finished_class=Finished):
    records = []
    for engine in ("legacy", "planner"):
        for observation in observations():
            policy = policy_class(engine=engine)
            for step in range(3):
                try:
                    d = policy.choose(copy.deepcopy(observation))
                    result = {"action": d.action, "reason": d.reason}
                except finished_class as done:
                    result = {"outcome": done.outcome, "reason": done.reason}
                result["memory"] = [policy.rests, policy.searches, policy.critical_retreats,
                                     policy.necro_moves, policy.combat_approach_target,
                                     policy.combat_approach_steps, policy.target]
                if hasattr(policy, "floor_recovery"):
                    result["challenge_recovery"] = policy.floor_recovery
                records.append(result)
                if "outcome" in result:
                    break
    return records


class SelectorTests(unittest.TestCase):
    def test_priority_short_circuit_and_trace(self):
        context = Context(None, {})
        decision = Decision({"type": "wait"}, "display text")
        tree = Selector("root", (Leaf("decline", lambda c: None),
                                 Leaf("select", lambda c: decision),
                                 Leaf("never", lambda c: self.fail("lower priority ran"))))
        self.assertIs(decision, tree(context))
        self.assertEqual("select", decision.controller)
        self.assertEqual([{"node": "decline", "selected": False},
                          {"node": "select", "selected": True}], context.trace)

    def test_reactive_safety_preempts_previous_selection(self):
        s, p = state(), SurvivalPolicy()
        first = p.choose(s)
        self.assertEqual("exploration", first.controller)
        s["hero"]["hp"] = 3
        s["inventory"].append({"id": "heal", "name": "potion of healing", "actions": ["DRINK"]})
        self.assertEqual("emergency-healing", p.choose(s).controller)

    def test_stop_is_not_a_declined_leaf(self):
        def stop(c):
            raise Finished("blocked", "unsafe")
        with self.assertRaises(Finished):
            Selector("root", (Leaf("stop", stop), Leaf("never", lambda c: self.fail())))(Context(None, {}))

    def test_pre_refactor_decision_matrix_for_both_engines(self):
        # Captured from the original policy before refactoring. Includes action,
        # reason, stop outcome and selected tactic counters across repeated ticks.
        records = decision_matrix()
        self.assertEqual(1096, len(records))
        digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        self.assertEqual("0f367fbf956455d0e207f86c84d364590edff348d237278487de5e453bedf8ee", digest)

    def test_pre_refactor_nine_challenge_matrix_for_both_engines(self):
        from tools.nine_challenge import NineChallengePolicy

        def verified(engine):
            p = NineChallengePolicy(engine=engine)
            p.challenges_verified = p.challenge_window_opened = True
            return p

        # Preserve the historical refactor baseline with the newly authorized
        # resource-aware exploration branch disabled; dedicated tests cover it.
        with patch('tools.mage_policy.selective_descent',return_value=None), \
                patch('tools.mage_policy.exploration_pressure',return_value=None), \
                patch('tools.mage_policy.starving_food',return_value=None), \
                patch.object(NineChallengePolicy,'systematic_exploration_enabled',return_value=False):
            records = decision_matrix(verified)
        self.assertEqual(1072, len(records))
        digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        self.assertEqual("844c1ccab436bbbfa1f393620cea423695bdde82fbe6d5458b0fdea8591f819a", digest)


class MemoryTests(unittest.TestCase):
    def test_all_aliases_have_one_owner_and_independent_defaults(self):
        a, b = SurvivalPolicy(), SurvivalPolicy()
        for group in fields(PolicyMemory):
            owner = getattr(a.memory, group.name)
            for item in fields(owner):
                self.assertIs(getattr(a, item.name), getattr(owner, item.name))
        a.blocked.add(25)
        self.assertFalse(b.blocked)
        a.memory.combat.critical_retreats = 3
        self.assertEqual(3, a.critical_retreats)
        a.critical_retreats = 4
        self.assertEqual(4, a.memory.combat.critical_retreats)

    def test_floor_lifetimes_are_declared_at_the_owner(self):
        p = SurvivalPolicy()
        p.blocked.add(25)
        p.seed_plan = {"stage": "activate"}
        p.purchases.append({"name": "food"})
        p.tested_scrolls.add("rune")
        p.memory.reset_floor(9)
        self.assertFalse(p.blocked)
        self.assertIsNone(p.seed_plan)
        self.assertEqual(9, p.entrance_cell)
        self.assertEqual([{"name": "food"}], p.purchases)
        self.assertEqual({"rune"}, p.tested_scrolls)

    def test_menu_phases_are_validated_and_have_handlers(self):
        p = SurvivalPolicy()
        p.menu_plan = "upgrade-select"
        self.assertIs(MenuPhase.UPGRADE_SELECT, p.menu_plan)
        self.assertEqual(set(MenuPhase), set(MENU_HANDLERS))
        with self.assertRaises(ValueError):
            p.menu_plan = "guess-a-purchase"
        with self.assertRaises(ValueError):
            p.memory.interaction.menu_plan = "guess-a-purchase"

    def test_transaction_restores_nested_memory_new_fields_and_aliases(self):
        p, guard = SurvivalPolicy(), NavigationLoopGuard()
        p.extra = p.blocked
        transaction = Transaction(p, guard)
        p.blocked.add(25)
        p.new_tactic = [1]
        guard.history.append("rejected")
        transaction.rollback()
        self.assertFalse(p.blocked)
        self.assertIs(p.extra, p.blocked)
        self.assertFalse(hasattr(p, "new_tactic"))
        self.assertFalse(guard.history)


class SemanticTests(unittest.TestCase):
    def test_navigation_loop_detection_ignores_changing_prose(self):
        p, s = NavigationLoopGuard(repetitions=2), state()
        p.visited.add((1, 0, 24))
        p.check(s, Decision({"type": "cell", "cell": 25}, "one", Intent.LOOT))
        with self.assertRaises(Finished):
            p.check(s, Decision({"type": "cell", "cell": 25}, "entirely different", Intent.LOOT))

    def test_menu_loop_detection_ignores_changing_prose(self):
        guard, s = MenuLoopGuard(repetitions=2), state()
        guard.check(s, Decision({"type": "back"}, "one"))
        with self.assertRaises(Finished):
            guard.check(s, Decision({"type": "back"}, "two"))

    def test_descent_progress_does_not_require_stairs_wording(self):
        p, s = SurvivalPolicy(), state()
        p.update(s)
        p.cell(25, "go down", intent=Intent.DESCEND)
        s["depth"] = 2
        p.update(s)
        self.assertEqual([1], p.cleared_floors)

    def test_prose_cannot_forge_descent(self):
        p, s = SurvivalPolicy(), state()
        p.update(s)
        p.cell(25, "stairs: this is only text")
        s["depth"] = 2
        p.update(s)
        self.assertFalse(p.cleared_floors)

    def test_planner_goals_use_intent_not_prose(self):
        p, s = SurvivalPolicy(engine="planner"), state()
        p.update(s)
        p.toward(s, 25, "get supplies", intent=Intent.LOOT)
        self.assertEqual("loot", p.planner.goal.kind)
        p.toward(s, 26, "shop: unrelated text", intent=Intent.EXPLORE)
        self.assertEqual("explore", p.planner.goal.kind)


class RunnerContracts(unittest.TestCase):
    def test_only_explicit_pre_execution_rejections_are_retryable(self):
        self.assertTrue(rejected_before_execution(PlayerAPIError(409, "stale observation")))
        self.assertTrue(rejected_before_execution(PlayerAPIError(400, "Button is no longer available")))
        self.assertTrue(rejected_before_execution(PlayerAPIError(400, "A menu requires input")))
        self.assertFalse(rejected_before_execution(PlayerAPIError(400, "invalid action")))
        self.assertFalse(rejected_before_execution(PlayerAPIError(500, "unknown execution status")))

    def test_rejected_actions_do_not_consume_new_tactic_budget(self):
        class Policy:
            def __init__(self):
                self.new_budget = []

            def choose(self, observation):
                self.new_budget.append("step")
                return Decision({"type": "button", "id": "retry"}, "test")

        class API:
            observation = state()
            calls = 0

            def state(self):
                return self.observation

            def step(self, action):
                self.calls += 1
                if self.calls < 10:
                    raise PlayerAPIError(409, "stale observation")
                return self.observation

        p = Policy()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "run.jsonl"
            result = run(API(), p, 10, 0, path, bounded=True)
            self.assertEqual(1, result["actions"])
            self.assertEqual(10, result["attempts"])
            self.assertEqual(["step"], p.new_budget)

    def test_timeout_is_not_retried_or_rolled_back(self):
        class Policy:
            steps = 0

            def choose(self, observation):
                self.steps += 1
                return Decision({"type": "wait"}, "test")

        class API:
            observation = state()
            calls = 0

            def step(self, action):
                self.calls += 1
                raise TimeoutError("unknown execution status")

        p, api = Policy(), API()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(TimeoutError):
                run(api, p, 3, 0, Path(directory) / "run.jsonl", bounded=True)
        self.assertEqual(1, p.steps)
        self.assertEqual(1, api.calls)

    def test_logs_include_selected_controller_and_priority_trace(self):
        class API:
            observation = state()

            def step(self, action):
                return self.observation

        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "run.jsonl"
            run(API(), SurvivalPolicy(), 1, 0, path, bounded=True)
            record = json.loads(path.read_text().splitlines()[0])
        self.assertEqual("exploration", record["controller"])
        self.assertEqual("explore", record["intent"])
        self.assertTrue(record["controllers"][-1]["selected"])

    def test_terminal_stop_retains_public_policy_diagnostics_without_an_action(self):
        class Blocked(SurvivalPolicy):
            def choose(self,observation):
                self.update(observation)
                self.planner.report["blocker"]={"active_foes":3}
                raise Finished("blocked","no safe route")
        class API:
            observation=state()
        with tempfile.TemporaryDirectory() as directory:
            result=run(API(),Blocked(),1,0,Path(directory)/"run.jsonl")
        self.assertEqual(3,result["terminal_policy_report"]["blocker"]["active_foes"])
        self.assertEqual(0,result["actions"])


if __name__ == "__main__":
    unittest.main()
