"""Planner exhaustion is a terminal failure, never an invitation to starve."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.policy_decision import Decision, Finished, GameplayBlocked, PlannerStuck
from tools.policy_runner import run
from tools.test_continuation import DamageAPI
from tools.test_until_death import StalledPolicy


class StuckPlannerTests(unittest.TestCase):
    def test_terminal_keeps_structured_blockers_after_transaction_rollback(self):
        from tools.objective_planning import publish, Result, Status
        class BlockedObjective(StalledPolicy):
            def choose(self, state):
                publish(self, "discovery", Result(Status.BLOCKED, "no stash",
                    prerequisites=[{"objective": "inventory-protection", "status": "blocked"}]))
                raise PlannerStuck("discovery prerequisites exhausted")
        result, log = self.execute(DamageAPI(), BlockedObjective())
        self.assertEqual("stuck-planner", result["outcome"])
        terminal = next(row for row in log if "planner_failure" in row)
        attempt = terminal["policy_report"]["failed_objective_attempt"]["objectives"]["discovery"]
        self.assertEqual("inventory-protection", attempt["prerequisites"][0]["objective"])

    def execute(self, api, policy):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            result = run(api, policy, 10, 0, path)
            return result, [json.loads(line) for line in path.read_text().splitlines()]

    def test_run29_style_pending_room_ends_without_any_wait_or_fake_death(self):
        class PendingPool(StalledPolicy):
            def choose(self, state):
                raise GameplayBlocked("Piranha-room chest remains uncollected")
        api = DamageAPI()
        api.observation["depth"] = 7
        api.observation["hero"]["buffs"] = [{"name": "starving"}]
        result, log = self.execute(api, PendingPool())
        self.assertEqual("stuck-planner", result["outcome"])
        self.assertEqual("stuck planner (bot unable to proceed)", result["death_reason"])
        self.assertEqual(3, result["hero"]["hp"])
        self.assertEqual(0, result["actions"])
        self.assertFalse(api.actions)
        terminal = next(row for row in log if "planner_failure" in row)
        self.assertIn("Piranha-room chest", terminal["planner_failure"]["reason"])
        self.assertEqual("high", terminal["planner_failure"]["review_priority"])
        self.assertIn("state", terminal)
        self.assertIn("policy_report", terminal)
        self.assertFalse(any("accepted_transition" in row for row in log))

    def test_existing_rescue_is_executed_before_terminal_exhaustion(self):
        api = DamageAPI()
        with patch("tools.until_death.best_effort", side_effect=[
                Decision({"type": "cell", "cell": 25}, "admitted retreat"), None]):
            result, _ = self.execute(api, StalledPolicy())
        self.assertEqual([{"type": "cell", "cell": 25}], api.actions)
        self.assertEqual("stuck-planner", result["outcome"])
        self.assertEqual(2, result["hero"]["hp"])

    def test_failed_rescue_preserves_original_and_rescue_blockers(self):
        with patch("tools.until_death.best_effort", side_effect=GameplayBlocked("rescue route unsafe")):
            result, _ = self.execute(DamageAPI(), StalledPolicy())
        self.assertIn("Exploration exhausted", result["planner_failure"]["reason"])
        self.assertIn("rescue route unsafe", result["planner_failure"]["reason"])

    def test_real_death_and_technical_pause_are_not_relabelled(self):
        class Stop(StalledPolicy):
            def choose(self, state):
                raise Finished(self.ending, "test stop")
        for ending in ("dead", "blocked"):
            policy = Stop()
            policy.ending = ending
            result, _ = self.execute(DamageAPI(), policy)
            self.assertEqual(ending, result["outcome"])
            self.assertNotIn("planner_failure", result)
