"""Run 151 decision 748: reduced public route, not original runtime memory."""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.ghost_quest import visit_ghost
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import GameplayBlocked


def fixture():
    route = [834, 779, 724, 668, 612, 557, 503, 449, 395]
    s = {
        "scene": "GameScene", "status": "ready", "modal": False,
        "depth": 2, "branch": 0, "danger_cells": [],
        "hero": {"name": "mage", "cell": 834, "hp": 30, "max_hp": 30,
                 "strength": 11, "buffs": [{"name": "hungry"}]},
        "inventory": [], "objects": [], "ui": {"texts": [], "buttons": []},
        "map": {"width": 55, "height": 35, "cells": [
            {"cell": c, "terrain": 29 if c == 834 else 5 if c in {668, 503}
             else 1, "observed": True, "visible": c not in {612, 557},
             "effects": []} for c in route]},
    }
    p = MagePolicy()
    p.update(s)
    # Explicit reconstruction of relevant priors from the validated recording.
    # Narrow origin area to the recorded first-sighting tile for this fixture.
    p.ghost_quest.update(stage="reward", origin_cell=395, origin_depth=2,
                         origin_area=[395], last_cell=784, last_depth=2)
    p.escape_commitment = {"edges": [(781, 780)], "hp": 30,
                           "charges": 6, "age": 4}
    return s, p


class GhostEscapeReturnTests(unittest.TestCase):
    def test_nonreversing_reward_return_preserves_escape_memory(self):
        s, p = fixture()
        plan = copy.deepcopy(p.escape_commitment)
        d = visit_ghost(p, s, [], distance, neighbors)
        self.assertIsNotNone(d, "Unrelated escape edge must not exclude reward return")
        self.assertEqual({"type": "cell", "cell": 779}, d.action)
        self.assertEqual("reposition", d.intent)
        self.assertEqual(plan, p.escape_commitment)
        self.assertEqual("reward", p.ghost_quest["stage"])
        self.assertIsNone(p.ghost_menu)
        self.assertNotIn("selected", p.ghost_quest)

    def test_reverse_edge_anywhere_in_return_route_is_not_admitted(self):
        for edge in [(779, 834), (557, 612)]:
            s, p = fixture()
            p.escape_commitment["edges"] = [edge]
            self.assertIsNone(visit_ghost(p, s, [], distance, neighbors))
            self.assertEqual("reward", p.ghost_quest["stage"])
            self.assertEqual(0, p.ghost_quest["travel"])

    def test_existing_threat_health_and_hazard_vetoes_remain(self):
        for case in ("recent", "ranged", "enemy", "danger", "health", "poison", "plant", "effect"):
            with self.subTest(case=case):
                s, p = fixture()
                enemies = []
                if case == "recent": p.recent_threats[780] = {"name": "fetid rat", "cell": 780}
                if case == "ranged": p.ranged_plan = {"name": "gnoll trickster"}
                if case == "enemy": enemies = [{"name": "fetid rat", "cell": 780}]
                if case == "danger": s["danger_cells"] = [779]
                if case == "health": s["hero"]["hp"] = 14
                if case == "poison": s["hero"]["buffs"] = [{"name": "poisoned"}]
                if case == "plant": p.tiles[779]["plant"] = "sorrowmoss"
                if case == "effect": p.tiles[779]["effects"] = ["A cloud of toxic gas"]
                try:
                    decision = visit_ghost(p, s, enemies, distance, neighbors)
                except GameplayBlocked:
                    decision = None
                self.assertIsNone(decision)
                self.assertEqual("reward", p.ghost_quest["stage"])

    def test_escape_still_blocks_starting_quest(self):
        s, p = fixture()
        p.ghost_quest["stage"] = "new"
        self.assertIsNone(visit_ghost(p, s, [], distance, neighbors))


if __name__ == "__main__":
    unittest.main()
