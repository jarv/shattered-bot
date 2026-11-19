import contextlib
import copy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.continuation import best_effort
from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision, Finished, TacticalBlocked
from tools.policy_runner import run
from tools.ranged_tactics import choose
from tools.test_regular_feedback import arena
from tools.test_survival_bot import fully_known, state
from tools.toxic_escape import escape, in_toxic_gas

GAS = "A greenish cloud of toxic gas is swirling here."


def gas_corridor():
    s = fully_known(state())
    s["hero"].update(cell=24, hp=1, strength=12)
    for tile in s["map"]["cells"]:
        tile.update(terrain=1 if tile["cell"] in {24, 25, 26} else 4,
                    effects=[GAS] if tile["cell"] in {24, 25} else [], observed=True)
    return s


class ToxicGasTests(unittest.TestCase):
    def policy(self, s):
        p = MagePolicy(engine="planner")
        p.challenges_verified = True
        p.update(s)
        return p

    def test_gas_escape_preempts_recovery_and_food_even_at_one_hp(self):
        s = gas_corridor()
        s["inventory"].append({"id":"food", "name":"ration of food", "actions":["EAT"]})
        p = self.policy(s)
        p.ranged_plan = {"mode":"cover", "goal":24}
        a = p.choose(s)
        self.assertEqual({"type":"cell", "cell":25}, a.action)
        self.assertEqual("toxic-gas-escape", a.controller)
        self.assertEqual(2, p.planner.report["toxic_gas_escape"]["route_steps"])
        self.assertIsNone(p.ranged_plan)
        self.assertEqual("cell", best_effort(p, s, []).action["type"])

    def test_poison_buff_or_stale_ui_text_is_not_current_toxic_gas(self):
        s = state()
        s["hero"]["buffs"] = [{"name":"poisoned"}]
        s["ui"]["texts"] = ["A hidden toxic gas trap activates!"]
        self.assertFalse(in_toxic_gas(s))
        self.assertIsNone(escape(self.policy(s), s))

    def test_do_not_escape_through_unknown_tiles_traps_fire_or_rendered_warnings(self):
        for obstruction in ("unknown", "trap", "fire", "warning", "rooted"):
            s = gas_corridor()
            tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
            if obstruction == "unknown": tile["observed"] = False
            if obstruction == "trap": tile.update(terrain=18, trap="toxic gas trap")
            if obstruction == "fire": tile["effects"].append("A fire is raging here.")
            if obstruction == "warning": s["danger_cells"] = [25]
            if obstruction == "rooted": s["hero"]["buffs"] = [{"name":"rooted"}]
            with self.subTest(obstruction=obstruction), self.assertRaises(Finished) as stopped:
                escape(self.policy(s), s)
            self.assertEqual("blocked", stopped.exception.outcome)

    def test_past_clear_ground_is_not_claimed_currently_visible_or_safe(self):
        s = gas_corridor()
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = False
        p = self.policy(s)
        self.assertEqual(25, escape(p, s).action["cell"])
        self.assertFalse(p.planner.report["toxic_gas_escape"]["target_currently_visible"])

    def test_final_runner_guard_replaces_direct_and_exception_recovery_waits(self):
        class WaitPolicy(MagePolicy):
            def choose(self, s):
                return self.decision({"type":"wait"}, "recovery: recharge")
        class RecoveryPolicy(WaitPolicy):
            def choose(self, s):
                raise TacticalBlocked("navigation-loop", "declined route")
            def recover_tactical_block(self, s, error):
                return self.decision({"type":"wait"}, "recovery: break rejected navigation cycle")
        for policy in (WaitPolicy(), RecoveryPolicy()):
            s = gas_corridor()
            actions = []
            def step(a):
                actions.append(a)
                after = copy.deepcopy(s)
                after["hero"]["cell"] = a["cell"]
                return after
            api = SimpleNamespace(observation=s, step=step)
            with TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
                result = run(api, policy, 1, 0, Path(temp)/"trace.jsonl", bounded=True)
            self.assertEqual("limit", result["outcome"])
            self.assertEqual([{"type":"cell", "cell":25}], actions)

    def test_trapped_fallback_stops_without_a_wait_or_an_uncaught_exception(self):
        class BlockedPolicy(MagePolicy):
            def choose(self, s):
                from tools.policy_decision import GameplayBlocked
                raise GameplayBlocked("No admitted route")
        s = gas_corridor()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 4
        api = SimpleNamespace(observation=s, step=lambda a: self.fail("Trapped gas must not dispatch a wait"))
        with TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            result = run(api, BlockedPolicy(), 1, 0, Path(temp)/"trace.jsonl")
        self.assertEqual("blocked", result["outcome"])
        self.assertIn("refusing recovery waits", result["reason"])
        self.assertEqual(0, result["actions"])

    def test_private_run46_gas_snapshots_select_escape_not_recovery_wait(self):
        path = os.environ.get("SHATTERED_RUN46_FIXTURE")
        if not path:
            self.skipTest("optional private recording")
        records = json.loads(Path(path).read_text())
        p = MagePolicy(engine="planner")
        p.challenges_verified = True
        checked = []
        for row in records["late"]:
            s = row["state"]
            p.update(s)
            if row["index"] in {927, 930, 945, 949}:
                a = p.choose(s)
                self.assertNotEqual({"type":"wait"}, a.action)
                self.assertEqual("cell", a.action["type"])
                self.assertEqual("toxic-gas-escape", a.controller)
                checked.append(row["index"])
        self.assertEqual([927, 930, 945, 949], checked)


class TricksterRangedTests(unittest.TestCase):
    def setup_foe(self, cell=43):
        s, p = arena()
        foe = {"name":"gnoll trickster", "cell":cell}
        s["objects"] = [foe]
        p.update(s)
        return s, p, foe

    def test_ranged_damage_precedes_cover_and_adjacent_melee(self):
        for cell in (41, 43):
            s, p, foe = self.setup_foe(cell)
            a = choose(p, s, [foe])
            self.assertEqual("ZAP", a.action["action"])
            self.assertIn("prioritize ranged damage", a.reason)
            self.assertTrue(p.trickster_reposition)
            self.assertIsNone(p.best_attack(s, foe, allowed_kinds={"melee"}))

    def test_shoot_then_seek_cover_and_shoot_again_from_cover(self):
        s, p, foe = self.setup_foe()
        with patch.object(p, "enemy_can_see", side_effect=lambda state, enemy, cell: cell != 39), \
                patch("tools.ranged_tactics.exposure", return_value={"exposure":0}):
            self.assertEqual("ZAP", choose(p, s, [foe]).action["action"])
            a = choose(p, s, [foe])
            self.assertEqual({"type":"cell", "cell":39}, a.action)
            self.assertEqual("cover", p.ranged_plan["mode"])
            s["hero"]["cell"] = 39
            p.update(s)
            self.assertEqual("ZAP", choose(p, s, [foe]).action["action"])

    def test_spent_wand_without_cover_does_not_start_melee_chase(self):
        s, p, foe = self.setup_foe()
        s["inventory"][0]["status"] = "0/4"
        with patch.object(p, "enemy_can_see", return_value=True), self.assertRaises(Finished):
            choose(p, s, [foe])
        self.assertIsNone(p.ranged_plan)

    def test_critical_health_prioritizes_line_break_before_optional_shot(self):
        s, p, foe = self.setup_foe()
        s["hero"]["hp"] = 4
        with patch.object(p, "enemy_can_see", side_effect=lambda state, enemy, cell: cell != 39), \
                patch("tools.ranged_tactics.exposure", return_value={"exposure":0}):
            self.assertEqual({"type":"cell", "cell":39}, choose(p, s, [foe]).action)

    def test_remembered_target_never_receives_a_blind_ranged_attack(self):
        s, p, foe = self.setup_foe()
        s["objects"] = []
        p.recent_threats[foe["cell"]] = foe
        with patch.object(p, "best_attack", side_effect=AssertionError("memory is not a live target")), \
                patch.object(p, "enemy_can_see", return_value=False), \
                patch("tools.ranged_tactics.exposure", return_value={"exposure":0}):
            a = choose(p, s, [])
        self.assertEqual({"type":"wait"}, a.action)


if __name__ == "__main__":
    unittest.main()
