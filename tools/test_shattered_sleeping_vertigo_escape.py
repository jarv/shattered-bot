"""Run 59 reduced public gas geometry, not reconstructed runtime memory."""
import copy
import unittest

from tools import vertigo_tactics as vertigo
from tools.policy_decision import PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def gas_room():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=1223, hp=30, max_hp=30, buffs=[
        {"name": "vertigo", "description": "Turns of vertigo remaining: 2."}])
    # Decision 817: confusion covers every adjacent landing, but 1271 is
    # observed clear beyond 1222. The newly visible gnoll at 1624 sleeps.
    terrain = {1121: 4, 1122: 4, 1123: 4, 1171: 2, 1172: 2,
               1173: 19, 1174: 1, 1221: 15, 1222: 29, 1223: 29,
               1224: 29, 1271: 2, 1272: 29, 1273: 1, 1274: 1}
    gas = {1171, 1172, 1173, 1174, 1221, 1222, 1223, 1224, 1272, 1273, 1274}
    s["map"] = {"width": 50, "height": 44, "cells": [
        dict(cell=c, terrain=t, visible=True, observed=True,
             effects=["A cloud of confusion gas is swirling here."] if c in gas else [])
        for c, t in terrain.items()]}
    next(t for t in s["map"]["cells"] if t["cell"] == 1173)["trap"] = "confusion gas trap"
    s["objects"] = [{"cell": 1624, "name": "gnoll scout", "sleeping": True},
                    {"cell": 1171, "name": "pasty", "top_item": {"name": "pasty"}},
                    {"cell": 1278, "name": "turquoise potion",
                     "top_item": {"name": "turquoise potion", "identified": False}}]
    p = verified()
    p.update(s)
    # Accepted-input receipt at log line 2362; supplied explicitly, not
    # claimed as recovered full policy memory.
    p.vertigo_plan = {"moves": 1, "waits": 0, "stale": 0}
    return s, p


class SleepingVertigoEscapeTests(unittest.TestCase):
    def test_distant_sleeper_does_not_veto_all_direction_checked_escape(self):
        s, p = gas_room()
        self.assertEqual([1223, 1222, 1271], vertigo.exit_route(p, s, True))
        try:
            action = p.choose(s)
        except PlannerStuck:
            self.fail("A distant sleeping gnoll must not veto a fully checked gas escape")
        self.assertEqual("vertigo-response", action.controller)
        self.assertEqual({"type": "cell", "cell": 1222}, action.action)
        self.assertEqual(8, len(p.planner.report["vertigo_response"]["possible_landings"]))
        self.assertEqual(1, p.vertigo_plan["moves"])
        self.assertEqual(0, p.vertigo_plan["waits"])
        self.assertFalse(action.movement_batch)
        self.assertIn(1171, p.loot)
        self.assertIn(1278, p.loot)  # Escape proposals do not collect rewards.
        after = copy.deepcopy(s)
        after["hero"]["cell"] = 1273  # Synthetic accepted random outcome.
        receipt = vertigo.observe(p, s, action, after)
        self.assertEqual(2, receipt["moves"])
        self.assertFalse(receipt["moved_as_requested"])

    def test_near_sleeper_active_or_remembered_threat_still_blocks(self):
        for kind in ("near", "active", "remembered"):
            s, p = gas_room()
            if kind == "near":
                s["objects"][0]["cell"] = 1374
            elif kind == "active":
                s["objects"][0]["sleeping"] = False
            else:
                p.recent_threats[1374] = {"cell": 1374, "name": "gnoll scout"}
            with self.assertRaises(PlannerStuck, msg=kind):
                vertigo.choose(p, s)

    def test_all_landing_hazards_and_budget_are_still_enforced(self):
        for kind in ("pit", "trap", "toxic", "plant", "unknown", "warning", "budget"):
            s, p = gas_room()
            t = p.tiles[1224]
            if kind == "pit":
                t["terrain"] = 0
            elif kind == "trap":
                t.update(terrain=18, trap="dart trap")
            elif kind == "toxic":
                t["effects"] = ["A cloud of toxic gas"]
            elif kind == "plant":
                t["plant"] = "stormvine"
            elif kind == "unknown":
                t["visible"] = False
            elif kind == "warning":
                s["danger_cells"] = [1224]
            else:
                p.vertigo_plan["moves"] = vertigo.MAX_MOVES
            with self.assertRaises(PlannerStuck, msg=kind):
                vertigo.choose(p, s)

    def test_sleeper_does_not_enable_renewing_gas_waits(self):
        s, p = gas_room()
        p.tiles[1224]["terrain"] = 0
        with self.assertRaises(PlannerStuck):
            vertigo.choose(p, s)
        self.assertEqual(0, p.vertigo_plan["waits"])


if __name__ == "__main__":
    unittest.main()
