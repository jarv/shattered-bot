"""Reduced missing-exit search admission from recording 000109.

Bookkeeping is a deterministic fixture, not originally recorded memory.
"""
import unittest

from tools.policy_decision import Finished
from tools.test_regular_feedback import arena


class FundedMissingExitSearchTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        s["depth"] = 4
        s["hero"].update(hp=40, max_hp=40, buffs=[{"name": "hungry"}])
        s["evaluation_stats"] = {"elapsed_turns": 1703.7503662109375}
        s["inventory"] = [{"id": "food", "name": "ration of food",
                           "quantity": 1, "actions": ["EAT"]}]
        p.update(s)
        p.exhausted.update(p.tiles)
        p.visits.update({c: 1 for c in p.tiles})
        p.searches = 13
        p.hunger_projection = {
            "turn": s["evaluation_stats"]["elapsed_turns"], "phase": "hungry",
            "remaining": 0, "foods": {"ration of food": 1}}
        return s, p

    def test_funded_missing_exit_can_select_bounded_observed_search(self):
        s, p = self.fixture()
        try:
            d = p.explore(s, [])
        except Finished as error:
            self.fail("Carried-food-funded missing-exit search excluded: " + error.reason)
        self.assertIn("secret-search vantage", d.reason)
        self.assertEqual("cell", d.action["type"])
        self.assertIn(d.action["cell"], p.paths(s))
        self.assertEqual(13, p.searches)
        self.assertFalse(p.searched_walls)
        self.assertFalse(p.cleared_floors)

    def test_no_extension_without_food_or_with_starvation_or_threats(self):
        for case in ("food", "starving", "threat", "danger", "health", "spent"):
            with self.subTest(case=case):
                s, p = self.fixture()
                if case == "food":
                    s["inventory"] = []
                elif case == "starving":
                    s["hero"]["buffs"] = [{"name": "starving"}]
                elif case == "threat":
                    p.recent_threats[41] = {"cell": 41, "name": "gnoll scout"}
                elif case == "danger":
                    s["danger_cells"] = [41]
                elif case == "health":
                    s["hero"]["hp"] = 20
                else:
                    p.searches = 40
                with self.assertRaises(Finished):
                    p.explore(s, [])

    def test_exit_mapping_and_boss_keep_existing_limits(self):
        for case in ("exit", "mapping", "boss"):
            with self.subTest(case=case):
                s, p = self.fixture()
                if case == "exit":
                    p.tiles[49]["terrain"] = 8
                    self.assertEqual("descend", p.explore(s, []).intent)
                else:
                    if case == "mapping":
                        p.mapped_floors.add((4, 0))
                    else:
                        s["depth"] = p.depth = 10
                    with self.assertRaises(Finished):
                        p.explore(s, [])


if __name__ == "__main__":
    unittest.main()
