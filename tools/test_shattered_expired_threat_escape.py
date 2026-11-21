"""Quiet escape release when the final stale sighting expires on selection.

Reduced public run-000086 decision-403 geometry/bookkeeping; isolated probes,
not recorded runtime memory or a gameplay replay.
"""
import copy
import unittest

from tools.escape_commitment import reverses
from tools.policy_decision import Decision
from tools.pursuit_budget import observe_accepted
from tools.test_regular_feedback import arena


class ExpiredThreatEscapeTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        s["hero"].update(hp=25, max_hp=25, buffs=[{"name": "hungry"}])
        s["inventory"][0]["status"] = "2/5"
        # Analogue of 398 -> 397 with a distant last sighting at 503.
        for tile in s["map"]["cells"]:
            if tile["cell"] == 60:
                tile["visible"] = False
        p.update(s)
        p.escape_commitment = {
            "edges": [(41, 40)], "hp": 25, "charges": 2, "age": 4}
        p.recent_threats = {
            60: {"name": "gnoll scout", "cell": 60, "observations_ago": 6}}
        p.pursuit_quiet_moves = 2
        # The third accepted quiet input cannot yet release the route because
        # this memory is still present until the next public-state update.
        observe_accepted(p, s, Decision({"type": "wait"}, "quiet choke"),
                         copy.deepcopy(s))
        self.assertEqual(3, p.pursuit_quiet_moves)
        self.assertTrue(reverses(p, s, 41))
        return s, p

    def test_expired_last_sighting_releases_already_quiet_route(self):
        s, p = self.fixture()
        p.update(s)
        self.assertFalse(p.recent_threats)
        self.assertFalse(reverses(p, s, 41))
        self.assertIsNone(p.escape_commitment)
        self.assertEqual(3, p.pursuit_quiet_moves)  # No invented accepted input.

    def test_unsafe_or_unconfirmed_quiet_context_retains_protection(self):
        for case in ("recent", "active", "damage", "unseen", "poison",
                     "burn", "bleed", "short", "modal", "danger"):
            with self.subTest(case=case):
                s, p = self.fixture()
                if case == "recent":
                    p.recent_threats[60]["observations_ago"] = 5
                if case == "active":
                    s["objects"] = [{"name": "gnoll scout", "cell": 43}]
                if case == "damage":
                    s = copy.deepcopy(s)
                    s["hero"]["hp"] -= 1
                if case == "unseen":
                    p.unseen_damage_turns = 3
                if case in ("poison", "burn", "bleed"):
                    s = copy.deepcopy(s)
                    s["hero"]["buffs"] = [{"name": case}]
                if case == "short":
                    p.pursuit_quiet_moves = 2
                if case == "modal":
                    s = copy.deepcopy(s)
                    s["modal"] = True
                if case == "danger":
                    s["danger_cells"] = [41]
                p.update(s)
                self.assertIsNotNone(p.escape_commitment)


if __name__ == "__main__":
    unittest.main()
