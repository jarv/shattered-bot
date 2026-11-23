"""Run 180 D1106/1135: confirmed pursuer defeat on the reverse edge.

Reduced public targeting/kill receipt and reconstructed escape bookkeeping,
not recorded runtime memory or a continuation after an alternative action.
The quiet-memory case matches D1106's admission, not D1135's extra stale sighting.
"""
import copy
import unittest

from tools.combat_observation import observe_accepted_attack
from tools.escape_commitment import reverses
from tools.policy_decision import Decision
from tools.test_regular_feedback import arena


class DefeatedEscapeEdgeTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        # Public 287 -> 288 -> 289 reduced to arena 42 -> 41 -> 40.
        s["hero"].update(hp=32, max_hp=35, buffs=[{"name": "hungry"}])
        s["inventory"][0]["status"] = "0/6"
        s["objects"] = [{"name": "sewer crab", "cell": 41,
                         "health_bar": [9, 21]}]
        s["ui"] = {"texts": []}
        p.update(s)
        p.escape_commitment = {"edges": [(42, 41), (41, 40)],
                               "hp": 35, "charges": 3, "age": 5}
        p.recent_threats = {41: dict(s["objects"][0], observations_ago=0)}
        p.loot[41] = {"name": "throwing club", "cell": 41}
        after = copy.deepcopy(s)
        after["objects"] = [{"name": "throwing club", "cell": 41,
                             "top_item": {"name": "throwing club"}}]
        after["ui"]["texts"] = ["You defeated sewer crab."]
        return s, p, after

    def accept(self, s, p, after):
        return observe_accepted_attack(
            p, s, Decision({"type": "cell", "cell": 41}, "combat: melee"), after)

    def test_exact_last_pursuer_receipt_retires_only_its_reverse_edge(self):
        s, p, after = self.fixture()
        self.assertTrue(reverses(p, s, 41))
        feedback = self.accept(s, p, after)
        self.assertTrue(feedback["censored"])
        self.assertFalse(reverses(p, after, 41),
                         "Confirmed last pursuer death must retire its immediate escape edge")
        self.assertEqual([(42, 41)], p.escape_commitment["edges"])
        self.assertEqual(5, p.escape_commitment["age"])
        self.assertEqual("throwing club", p.loot[41]["name"])
        p.tiles[41]["effects"] = ["A fire is raging here."]
        self.assertFalse(p.walkable(41))

    def test_ambiguous_or_unsafe_receipts_keep_protection(self):
        for case in ("no-message", "old-message", "other-message", "still-present",
                     "other-before", "other-after", "remembered", "unseen",
                     "danger", "poison", "depth", "branch", "not-edge", "invisible"):
            with self.subTest(case=case):
                s, p, after = self.fixture()
                if case == "no-message":
                    after["ui"]["texts"] = []
                elif case == "old-message":
                    s["ui"]["texts"] = list(after["ui"]["texts"])
                elif case == "other-message":
                    after["ui"]["texts"] = ["You defeated gnoll scout."]
                elif case == "still-present":
                    after["objects"] += s["objects"]
                elif case in ("other-before", "other-after"):
                    (s if case == "other-before" else after)["objects"].append(
                        {"name": "gnoll scout", "cell": 43})
                elif case == "remembered":
                    p.recent_threats[43] = {"name": "gnoll scout", "cell": 43}
                elif case == "unseen":
                    p.unseen_damage_turns = 1
                elif case == "danger":
                    after["danger_cells"] = [41]
                elif case == "poison":
                    after["hero"]["buffs"].append({"name": "poisoned"})
                elif case == "depth":
                    after["depth"] += 1
                elif case == "branch":
                    after["branch"] = 1
                elif case == "not-edge":
                    p.escape_commitment["edges"] = [(42, 40)]
                elif case == "invisible":
                    for tile in after["map"]["cells"]:
                        if tile["cell"] == 41:
                            tile["visible"] = False
                edges = list(p.escape_commitment["edges"])
                self.accept(s, p, after)
                self.assertEqual(edges, p.escape_commitment["edges"])


if __name__ == "__main__":
    unittest.main()
