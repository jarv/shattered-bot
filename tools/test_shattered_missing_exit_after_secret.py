"""Run 11: discovering a secret is not evidence that the floor exit was found."""
import unittest

from tools.policy_decision import Finished
from tools.test_regular_feedback import arena


class MissingExitAfterSecretTests(unittest.TestCase):
    def fixture(self):
        # Minimal public-geometry reduction of decision 1075: observed room,
        # no reachable exit/frontier, healthy Mage, unspent wall-search budget.
        s, p = arena()
        s["depth"] = 3
        p.update(s)
        p.exhausted.update(p.tiles)
        p.visits.update({c: 1 for c in p.tiles})
        # Reconstructed bookkeeping, not a hidden-room identity or completion.
        p.secret_area_found = True
        return s, p

    def test_missing_exit_keeps_bounded_wall_search_after_secret_discovery(self):
        s, p = self.fixture()
        try:
            d = p.explore(s, [])
        except Finished as error:
            self.fail("Secret discovery suppressed missing-exit search: " + error.reason)
        self.assertIn("secret-search vantage", d.reason)
        self.assertEqual(1, p.secret_search_steps)
        self.assertEqual(0, p.searches)  # Movement proposal is not a search receipt.
        self.assertFalse(p.searched_walls)
        self.assertFalse(p.cleared_floors)

    def test_known_exit_retains_optional_secret_search_suppression(self):
        s, p = self.fixture()
        p.tiles[49]["terrain"] = 8
        self.assertEqual("descend", p.explore(s, []).intent)
        self.assertEqual(0, p.secret_search_steps)

    def test_mapping_boss_and_spent_budget_still_suppress_search(self):
        for case in ("mapping", "boss", "budget"):
            with self.subTest(case=case):
                s, p = self.fixture()
                if case == "mapping":
                    p.mapped_floors.add((3, 0))
                elif case == "boss":
                    s["depth"] = p.depth = 10
                else:
                    p.searches = 40
                with self.assertRaises(Finished):
                    p.explore(s, [])
                self.assertEqual(0, p.secret_search_steps)


if __name__ == "__main__":
    unittest.main()
