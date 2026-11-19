import collections
import contextlib
import copy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.boss_strategies import TenguStrategy
from tools.fallback_progress import FallbackProgress
from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision
from tools.policy_geometry import distance, neighbors
from tools.policy_runner import run
from tools.test_survival_bot import fully_known, state
from tools.test_continuation import DamageAPI
from tools.test_until_death import StalledPolicy


class ChangedDoorTests(unittest.TestCase):
    def prepared(self):
        s = fully_known(state())
        s["depth"] = 10
        p = MagePolicy(engine="planner")
        p.update(s)
        p.visits[25] = 4
        return s, p

    def test_new_door_on_visited_floor_rearms_without_erasing_visit_history(self):
        s, p = self.prepared()
        p.blocked.add(25)
        p.exhausted.add(25)
        p.failed_moves[25] = 3
        s = copy.deepcopy(s)
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        p.update(s)
        self.assertEqual(4, p.visits[25])
        self.assertNotIn(25, p.blocked)
        self.assertIn(25, p.exhausted)  # Explicit door work overrides old frontier exhaustion.
        self.assertNotIn(25, p.failed_moves)
        self.assertIn(25, p.exploration_report(s, p.paths(s))["unopened_doors"])
        p.update(copy.deepcopy(s))
        self.assertIn(25, p.changed_door_cells)

    def test_normal_door_reclosing_does_not_rearm_exploration(self):
        s, p = self.prepared()
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        tile["terrain"] = 6
        p.update(copy.deepcopy(s))
        tile["terrain"] = 5
        p.update(copy.deepcopy(s))
        self.assertNotIn(25, p.changed_door_cells)
        self.assertNotIn(25, p.exploration_report(s, p.paths(s))["unopened_doors"])

    def test_opening_new_door_consumes_obligation_and_depth_change_resets_it(self):
        s, p = self.prepared()
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        tile["terrain"] = 5
        p.update(copy.deepcopy(s))
        self.assertIn(25, p.changed_door_cells)
        tile["terrain"] = 6
        p.update(copy.deepcopy(s))
        self.assertNotIn(25, p.changed_door_cells)
        p.changed_door_cells.add(25)
        s["depth"] = 11
        p.update(copy.deepcopy(s))
        self.assertFalse(p.changed_door_cells)

    def test_unobserved_mapping_is_not_a_confirmed_new_door(self):
        s, p = self.prepared()
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        tile.update(terrain=5, observed=False, visible=False, mapped=True)
        p.update(copy.deepcopy(s))
        self.assertNotIn(25, p.changed_door_cells)


class TenguTransitionTests(unittest.TestCase):
    def prepared(self):
        s = fully_known(state())
        s["depth"] = 10
        p = MagePolicy(engine="planner")
        p.update(s)
        p.visits[25] = 1
        boss = TenguStrategy()
        s["boss_health_text"] = "102/200"
        self.assertFalse(boss.victory(p, s))
        s = copy.deepcopy(s)
        s["boss_health_text"] = None
        s["ui"]["texts"] = ['Tengu: "Let\'s make this interesting..."']
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        p.update(s)
        self.assertFalse(boss.victory(p, s))
        return s, p, boss

    def test_public_transition_prioritizes_reachable_changed_door(self):
        s, p, boss = self.prepared()
        action = boss.choose(p, s, [], distance, neighbors)
        self.assertIsNotNone(action)
        self.assertEqual({"type": "cell", "cell": 25}, action.action)
        self.assertIn("observed transition door", action.reason)
        self.assertEqual([25], p.planner.report["boss_transition"]["observed_doors"])

    def test_policy_arbitration_selects_transition_before_generic_exploration(self):
        s, p, boss = self.prepared()
        p.boss_strategies["tengu"] = boss
        p.challenges_verified = True
        action = p.choose(s)
        self.assertEqual("boss-combat", action.controller)
        self.assertIn("observed transition door", action.reason)

    def test_disappearing_bar_without_transition_dialogue_is_not_a_phase_oracle(self):
        s, p, _ = self.prepared()
        boss = TenguStrategy()
        boss.victory(p, dict(s, boss_health_text="150/200"))
        s["ui"]["texts"] = []
        self.assertFalse(boss.victory(p, s))
        self.assertIsNone(boss.transition(p, s, []))

    def test_visible_danger_or_enemies_prevent_transition_traversal(self):
        s, p, boss = self.prepared()
        self.assertIsNone(boss.transition(p, s, [{"name": "Tengu", "cell": 26}]))
        s["danger_cells"] = [25]
        self.assertIsNone(boss.transition(p, s, []))
        s["danger_cells"] = []
        s["objects"] = [{"name": "Tengu", "cell": 26}]
        self.assertIsNone(boss.transition(p, s, []))  # Filtered engagement list is not enough.

    def test_real_victory_or_new_boss_bar_ends_transition(self):
        for victory in (False, True):
            s, p, boss = self.prepared()
            if victory:
                s["inventory"].append({"name": "Tengu's mask"})
            else:
                s["boss_health_text"] = "100/200"
            self.assertEqual(victory, boss.victory(p, s))
            self.assertFalse(boss.transitioning)

    def test_private_recorded_snapshots_reconsider_actual_door_without_live_game(self):
        path = os.environ.get("SHATTERED_TENGU_FIXTURE")
        if not path:
            self.skipTest("optional private sparse recording")
        records = json.loads(Path(path).read_text())
        for ident, index in (("000030", 4813), ("000034", 4078)):
            with self.subTest(run=ident):
                p = MagePolicy(engine="planner")
                boss = TenguStrategy()
                selected = None
                for sample in records[ident]["samples"]:
                    row = sample["row"]
                    if row["index"] > index:
                        break
                    s = row["state"]
                    p.update(s)
                    p.visits.update(collections.Counter(sample["positions_before"]))
                    boss.victory(p, s)
                    if row["index"] == index:
                        selected = boss.choose(p, s, [], distance, neighbors)
                        self.assertIn(266, p.exploration_report(s, p.paths(s))["unopened_doors"])
                self.assertIsNotNone(selected)
                self.assertIn("observed transition door", selected.reason)
                self.assertIn(266, p.planner.report["boss_transition"]["observed_doors"])


class FallbackProgressTests(unittest.TestCase):
    def wait(self):
        return Decision({"type": "wait"}, "last resort: advance time and accept damage; no verified safe action")

    def test_clock_recharge_and_visibility_flicker_do_not_hide_fallback_stall(self):
        guard = FallbackProgress(limit=3)
        s = state()
        for turn in range(3):
            after = copy.deepcopy(s)
            after["evaluation_stats"] = {"elapsed_turns": turn + 1}
            after["inventory"][0]["status"] = f"{turn}/9"
            after["map"]["cells"][0]["visible"] = not s["map"]["cells"][0]["visible"]
            self.assertEqual(turn == 2, guard.observe(s, self.wait(), after))
            s = after

    def test_damage_movement_map_change_and_tactical_waits_reset_guard(self):
        for change in ("damage", "move", "map", "boss", "tactical"):
            guard = FallbackProgress(limit=2)
            s = state()
            self.assertFalse(guard.observe(s, self.wait(), s))
            after = copy.deepcopy(s)
            decision = self.wait()
            if change == "damage":
                after["hero"]["hp"] -= 1
            elif change == "move":
                after["hero"]["cell"] += 1
            elif change == "map":
                after["map"]["cells"][0]["terrain"] = 5
            elif change == "boss":
                after["boss_health_text"] = "100/200"
            else:
                decision.reason = "boss: tengu bounded hold outside advertised hazards"
            self.assertFalse(guard.observe(s, decision, after))
            self.assertEqual(0, guard.waits)

    def test_runner_stops_locked_floor_stall_even_when_game_turns_advance(self):
        api = DamageAPI()
        api.observation["depth"] = 10
        api.observation["evaluation_stats"] = {"elapsed_turns": 0}
        api.observation["hero"]["buffs"] = [{"name": "floor is locked"}]
        def step(action):
            api.actions.append(action)
            api.observation = copy.deepcopy(api.observation)
            api.observation["evaluation_stats"]["elapsed_turns"] += 1
            return api.observation
        api.step = step
        with TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            result = run(api, StalledPolicy(), 1, 0, Path(temp)/"trace.jsonl")
        self.assertEqual("blocked", result["outcome"])
        self.assertEqual(128, result["actions"])
        self.assertEqual(128, result["fallback_waits_without_progress"])
        self.assertEqual(128, len(api.actions))


if __name__ == "__main__":
    unittest.main()
