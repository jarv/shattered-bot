"""Run 39: a hypothetical flight route is not an actionable entrance scout."""
import unittest
from unittest.mock import patch

from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import Demand, prepare_supplies, revisit_flight_room
from tools.room_tactics import Journey
from tools.test_required_corridor_and_flight_staging import flight_room


class RemoteFlightEntranceTests(unittest.TestCase):
    def fixture(self):
        s, p = flight_room()
        # Isolate the recorded contradiction: a safe bank whose hypothetical
        # flight route encounters a closed, unscouted door three cells away.
        for t in s["map"]["cells"]:
            t["visible"] = True
            if t["cell"] == 68:
                t["terrain"] = 5
        p.update(s)
        p.loot.pop(73, None)
        p.loot[71] = {"cell": 71, "name": "Chest"}
        demand = Demand("flight", "potion of levitation", 69)

        def journey(policy, staged, enemies, adjacent, **kwargs):
            if staged["hero"]["cell"] == 65:
                return Journey("flight", list(range(65, 72)), s["depth"])
            return None

        return s, p, demand, journey

    def test_unscoutable_bank_does_not_preempt_progress_with_futile_staging(self):
        s, p, demand, journey = self.fixture()
        with patch("tools.puzzle_supplies.demands", return_value=[demand]), \
                patch("tools.puzzle_supplies.prepare_intuition", return_value=None), \
                patch("tools.puzzle_supplies.plan_journey", side_effect=journey):
            action = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNone(action, "Remote unscouted entrance cannot justify a test-bank move")
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.flight_entrance_receipts)

    def test_revisit_uses_same_entrance_admission_as_testing(self):
        s, p, demand, journey = self.fixture()
        with patch("tools.puzzle_supplies.plan_journey", side_effect=journey):
            action = revisit_flight_room(p, s, demand, distance)
        self.assertIsNone(action)
        self.assertEqual(0, p.puzzle_revisit_steps["flight"])

    def test_receipted_reclosure_does_not_reject_previously_scouted_route(self):
        s, p, demand, journey = self.fixture()
        p.flight_entrance_receipts.add((s["depth"], s.get("branch", 0), 68))
        with patch("tools.puzzle_supplies.demands", return_value=[demand]), \
                patch("tools.puzzle_supplies.prepare_intuition", return_value=None), \
                patch("tools.puzzle_supplies.plan_journey", side_effect=journey):
            action = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(action)
        self.assertEqual("cell", action.action["type"])
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)


if __name__ == "__main__":
    unittest.main()
