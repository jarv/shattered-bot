"""Run 60: arrival at a flight approach must admit its safe entrance scout."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.test_consumable_tactics import potion
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies, safe_test_bank


def entrance():
    s = state()
    s["hero"].update(cell=674, hp=25, max_hp=25, strength=10)
    # Reduced public geometry at decision 328; omitted cells are not walkable.
    terrain = {c: 4 for y in range(16, 23) for c in range(y*38+25, y*38+37)}
    terrain.update({633: 29, 634: 29, 671: 29, 672: 29, 673: 29, 674: 29,
                    635: 12, 636: 12, 675: 5, 757: 11})
    for c in (676, 677, 678, 679, 680, 681, 714, 715, 716, 717, 718,
              719, 752, 753, 754, 755, 756, 791, 792, 793, 794, 795,
              830, 831, 832, 833):
        terrain[c] = 0
    s["map"] = dict(width=38, height=30, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] += [potion("azure potion"), potion("potion of healing")]
    s["objects"] = [{"cell": 757, "name": "Chest"}]
    p = verified()
    p.update(s)
    # Explicit reduced bookkeeping, not a claim of recorded memory.
    p.puzzle_flight_bank = 674
    return s, p


class FlightEscapeDoorPreflightTests(unittest.TestCase):
    def test_closed_entrance_is_scouted_without_drinking_or_crossing(self):
        s, p = entrance()
        self.assertFalse(safe_test_bank(p, s, 674, distance, neighbors,
                                       allow_dry=True, flight_bank=True))
        action = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(action, "The closed entrance must not deadlock bank admission")
        self.assertEqual({"type": "cell", "cell": 675}, action.action)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertIn(757, p.loot)
        self.assertFalse(p.flight_entrance_receipts)
        # Synthetic opening observation only: not an arrival or potion receipt.
        after = copy.deepcopy(s)
        next(t for t in after["map"]["cells"] if t["cell"] == 675)["terrain"] = 6
        p.update(after)
        # Open doors still do not satisfy the ordinary escape-terrain count.
        # Scouting does not certify that an unknown drink is now safe.
        self.assertFalse(safe_test_bank(p, after, 674, distance, neighbors,
                                       allow_dry=True, flight_bank=True))
        self.assertFalse(p.flight_entrance_receipts)
        self.assertIn(757, p.loot)
        self.assertIsNone(prepare_supplies(p, after, [], distance, neighbors))

    def test_unseen_trapped_or_threatened_entrance_is_not_scouted(self):
        for case in ("unseen", "trap", "threat", "budget"):
            s, p = entrance()
            door = p.tiles[675]
            if case == "unseen":
                door["visible"] = False
            elif case == "trap":
                door["trap"] = "poison dart trap"
            elif case == "threat":
                p.recent_threats[673] = {"cell": 673, "name": "marsupial rat"}
            else:
                p.puzzle_revisit_steps["flight"] = 48
            action = prepare_supplies(p, s, [], distance, neighbors)
            self.assertTrue(action is None or action.action != {"type": "cell", "cell": 675}, case)
            self.assertFalse(p.puzzle_drinks)
            self.assertIsNone(p.room_journey)


if __name__ == "__main__":
    unittest.main()
