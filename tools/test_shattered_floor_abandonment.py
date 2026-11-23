"""Bounded optional-work recovery preserves original incidents and hard gates."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.test_shattered_strength_before_descent import ready
from tools.floor_abandonment import FloorAbandonment
from tools.policy_decision import PlannerStuck, Finished, Intent
from tools.policy_runner import run


FAILURE = "Piranha-room chest remains uncollected: seek/test this floor invisibility supply"


def fixture():
    s, p = ready()
    s["map"]["cells"][93]["terrain"] = 8
    p.update(s)
    p.strength_identified = True
    p.loot.clear()
    return s, p, FloorAbandonment(p)


class FloorAbandonmentTests(unittest.TestCase):
    def start(self, s, recovery):
        return recovery.start(s, PlannerStuck(FAILURE,kind="optional-work-exhausted"), {"objectives": {"pool": "exhausted"}}, 42)

    def test_sequence_requires_actual_transition_and_leaves_loot_unfinished(self):
        s, p, recovery = fixture()
        p.loot[20] = dict(cell=20, name="Chest")
        s["objects"] = [p.loot[20]]
        action = self.start(s, recovery)
        self.assertIsNotNone(action)
        self.assertEqual(Intent.DESCEND, action.intent)
        self.assertEqual(0, recovery.incidents[0]["accepted_actions"])
        self.assertFalse(p.descent_counts_as_clear())
        self.assertIn(20, p.loot)
        self.assertFalse(p.completed_room_rewards)
        for _ in range(10):
            after = copy.deepcopy(s)
            after["evaluation_stats"] = {"elapsed_turns": s.get("evaluation_stats", {}).get("elapsed_turns", 0)+1}
            if action.action["cell"] == 93:
                after["depth"] += 1
            else:
                after["hero"]["cell"] = action.action["cell"]
            recovery.observe(s, action, after)
            s = after
            if recovery.active is None:
                break
            action = recovery.next(s)
        self.assertEqual("descended", recovery.incidents[0]["status"])
        self.assertFalse(recovery.incidents[0]["collection_credited"])
        self.assertEqual(FAILURE, recovery.incidents[0]["reason"])

    def test_hard_gates_cannot_be_overridden(self):
        for kind in ("discovery", "held-strength", "stash", "trap-return", "journey", "priority",
                     "quest-reward", "strict", "threat", "no-exit", "hazard-exit"):
            s, p, recovery = fixture()
            if kind == "discovery": p.strength_identified = False
            elif kind == "held-strength":
                s["inventory"].append(dict(id="str", name="potion of strength", actions=["DRINK"]))
            elif kind == "stash": p.potion_stash = {"phase": "retrieve"}
            elif kind == "trap-return": p.trap_payload_return = {"cell": 20}
            elif kind == "journey": p.room_journey = object()
            elif kind == "priority":
                p.loot[20] = dict(cell=20, name="potion of strength", top_item=dict(name="potion of strength"))
                s["objects"] = [p.loot[20]]
            elif kind == "quest-reward": p.ghost_quest["stage"] = "reward"
            elif kind == "strict": p.stop_on_incomplete_loot = True
            elif kind == "threat": s["objects"] = [dict(cell=61, name="marsupial rat")]
            elif kind == "no-exit":
                s["map"]["cells"][93]["terrain"] = 1
            else: s["map"]["cells"][93]["trap"] = "poison trap"
            self.assertIsNone(self.start(s, recovery), kind)
            self.assertEqual("declined", recovery.incidents[0]["status"])

    def test_survival_preempts_and_new_route_hazards_abort(self):
        s, p, recovery = fixture()
        self.start(s, recovery)
        s["objects"] = [dict(cell=61, name="marsupial rat")]
        self.assertIsNone(recovery.next(s))
        s["objects"] = []
        s["map"]["cells"][93]["effects"] = ["fire"]
        with self.assertRaises(PlannerStuck):
            recovery.next(s)
        self.assertIsNone(recovery.active)

    def test_no_progress_budget_and_one_episode_per_floor(self):
        s, p, recovery = fixture()
        action = self.start(s, recovery)
        for _ in range(8):
            recovery.observe(s, action, copy.deepcopy(s))
        with self.assertRaises(PlannerStuck):
            recovery.next(s)
        self.assertEqual("exhausted", recovery.incidents[0]["status"])
        self.assertIsNone(self.start(s, recovery))
        self.assertIn("already used", recovery.incidents[-1]["recovery_reason"])

    def test_api_rejection_is_not_an_accepted_progress_receipt(self):
        s, p, recovery = fixture()
        self.start(s, recovery)
        recovery.rejected()
        self.assertEqual(0, recovery.incidents[0]["accepted_actions"])
        self.assertEqual("rejected", recovery.incidents[0]["status"])

    def test_survival_interruptions_are_bounded_and_loading_does_not_invent_progress(self):
        s, p, recovery = fixture()
        action = self.start(s, recovery)
        self.assertIsNone(recovery.next({"status": "loading"}))
        for _ in range(5):
            recovery.next(s)  # Proposals alone spend no accepted budget.
        self.assertEqual(0, recovery.active["accepted_actions"])
        recovery.active["accepted_actions"] = 64
        with self.assertRaises(PlannerStuck):
            recovery.next(s)

    def test_unknown_stairs_and_unknown_ui_are_not_eligible(self):
        s, p, recovery = fixture()
        s["map"]["cells"][93]["observed"] = False
        p.update(s)
        self.assertIsNone(self.start(s, recovery))
        s, p, recovery = fixture()
        self.assertIsNone(recovery.start(s, PlannerStuck("Ranged exposure: no verified cover"), {}, 4))

    def test_escape_reversal_is_still_forbidden(self):
        s, p, recovery = fixture()
        action = self.start(s, recovery)
        step = action.action["cell"]
        p.escape_commitment = dict(edges=[(step, s["hero"]["cell"])], hp=30, charges=0, age=0)
        # Other routes may exist, but no proposal may reverse the protected edge.
        try:
            alternative = recovery.next(s)
        except PlannerStuck:
            alternative = None
        if alternative:
            self.assertNotEqual(step, alternative.action["cell"])

    def test_runner_records_recovered_failure_and_eventual_outcome_separately(self):
        s, p, _ = fixture()
        cls = type(p)
        class StuckPolicy(cls):
            def choose(self, state):
                self.update(state)
                if state["depth"] > 1:
                    raise Finished("won", "Synthetic test endpoint")
                raise PlannerStuck(FAILURE,kind="optional-work-exhausted")
        policy = StuckPolicy()
        policy.update(s)
        policy.strength_identified = True
        class API:
            observation = s
            def state(self): return self.observation
            def step(self, action):
                after = copy.deepcopy(self.observation)
                if action["cell"] == 93:
                    after["depth"] = 2
                else: after["hero"]["cell"] = action["cell"]
                self.observation = after
                return after
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"decisions.jsonl"
            result = run(API(), policy, 20, 0, path)
            self.assertEqual("won", result["outcome"])
            self.assertEqual(1, result["planner_recoveries_succeeded"])
            self.assertEqual(1, result["planner_incident_count"])
            self.assertNotIn(1, result.get("cleared_floors", []))
            incidents = [json.loads(line) for line in path.read_text().splitlines()
                         if "planner_incident" in json.loads(line)]
            self.assertEqual(0, incidents[0]["index"])
            self.assertEqual(FAILURE, incidents[0]["planner_incident"]["reason"])
