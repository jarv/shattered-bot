"""Run 40: quiet pickup/search time must participate in escape release."""
import copy
import unittest

from tools.escape_commitment import reverses
from tools.policy_decision import Decision, Intent
from tools.pursuit_budget import observe_accepted
from tools.test_regular_feedback import arena


class QuietPickupSearchTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        s["hero"].update(hp=27, max_hp=30, buffs=[{"name": "hungry"}])
        s["inventory"][0]["status"] = "4/5"
        # Recorded edges 908->907->906, reduced to arena cells 42->41->40.
        p.escape_commitment = {
            "edges": [(42, 41), (41, 40)], "hp": 29, "charges": 4, "age": 4
        }
        p.pursuit_retreat_moves = 6
        s["evaluation_stats"] = {"elapsed_turns": 572.15478515625}
        s["objects"] = [{"name": "stone of blast", "cell": 40},
                        {"name": "stone of shock", "cell": 41}]
        p.loot[41] = copy.deepcopy(s["objects"][1])
        return s, p

    def accepted(self, p, s, action, turn, intent=Intent.OTHER):
        after = copy.deepcopy(s)
        after["evaluation_stats"]["elapsed_turns"] = turn
        observe_accepted(p, s, Decision(action, "quiet public input", intent), after)
        return after

    def test_recorded_quiet_pickup_search_wait_release_without_extra_waits(self):
        s, p = self.fixture()
        self.assertTrue(reverses(p, s, 41))
        s = self.accepted(p, s, {"type": "cell", "cell": 40},
                          573.5524291992188, Intent.LOOT)
        s["objects"] = s["objects"][1:]
        self.assertIsNotNone(p.escape_commitment)
        s = self.accepted(p, s, {"type": "search"}, 575.8909912109375)
        self.assertIsNotNone(p.escape_commitment)
        s = self.accepted(p, s, {"type": "wait"}, 576.8909912109375)
        self.assertIsNone(p.escape_commitment,
                          "Three accepted quiet timed inputs must release stale reversal memory")
        self.assertFalse(reverses(p, s, 41))
        self.assertEqual(0, p.pursuit_retreat_moves)
        # Releasing route memory is not a receipt for the remaining item.
        self.assertEqual("stone of shock", p.loot[41]["name"])
        self.assertTrue(p.walkable(41))
        p.tiles[41]["effects"] = ["The air is unnaturally frigid here."]
        self.assertFalse(p.walkable(41), "Route release must not admit active cold")

    def test_free_or_unknown_clock_searches_do_not_count(self):
        for clock in ("unchanged", "missing"):
            s, p = self.fixture()
            if clock == "missing":
                s.pop("evaluation_stats")
            for _ in range(3):
                observe_accepted(p, s, Decision({"type": "search"}, "inspect"),
                                 copy.deepcopy(s))
            self.assertIsNotNone(p.escape_commitment)
            self.assertEqual(0, p.pursuit_quiet_moves)

    def test_existing_threat_and_damage_release_gates_remain(self):
        for case in ("enemy", "recent", "unseen", "poison", "damage"):
            s, p = self.fixture()
            if case == "enemy":
                s["objects"].append({"name": "marsupial rat", "cell": 42})
            elif case == "recent":
                p.recent_threats[42] = {"name": "marsupial rat", "cell": 42}
            elif case == "unseen":
                p.unseen_damage_turns = 1
            elif case == "poison":
                s["hero"]["buffs"].append({"name": "poisoned"})
            for _ in range(3):
                after = copy.deepcopy(s)
                after["evaluation_stats"]["elapsed_turns"] += 1
                if case == "damage":
                    after["hero"]["hp"] -= 1
                observe_accepted(p, s, Decision({"type": "search"}, "search"), after)
                s = after
            self.assertIsNotNone(p.escape_commitment, case)


if __name__ == "__main__":
    unittest.main()
