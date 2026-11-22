"""Run 97, decision 1328: reduced public room, not recovered policy memory."""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import neighbors
from tools.puzzle_supplies import stage_known_flight
from tools.room_tactics import plan_journey


def fixture():
    # Public room coordinates and terrain from the played revision 27378a92.
    cells = {}
    for y in range(42, 51):
        for x in range(33, 41):
            c = y * 50 + x
            cells[c] = dict(cell=c, terrain=4 if x in {33, 40} or
                            y in {42, 50} else 0, observed=True,
                            visible=True, effects=[])
    for c in (2184, 2189, 2484, 2489, 2286, 2287, 2386, 2387):
        cells[c]["terrain"] = 14
    cells[2134]["terrain"] = 5
    potion = dict(id="flight", name="potion of levitation", identified=True,
                  quantity=1, actions=["DRINK"])
    s = dict(scene="GameScene", status="ready", modal=False, depth=3,
             branch=0, danger_cells=[], ui=dict(texts=[], buttons=[]),
             hero=dict(cell=2184, hp=35, max_hp=35, strength=11, buffs=[]),
             inventory=[potion], keys=[dict(name="golden key", depth=3, quantity=1)],
             objects=[dict(cell=c, name="golden key",
                           top_item=dict(name="golden key", quantity=1))
                      for c in (2189, 2484, 2489)] +
                     [dict(cell=c, name="Locked chest")
                      for c in (2286, 2287, 2386, 2387)],
             map=dict(width=50, height=53, cells=list(cells.values())))
    p = MagePolicy()
    p.update(s)
    return p, s, potion


class FlightKeyDeficitTests(unittest.TestCase):
    def test_one_held_key_does_not_spend_only_flight_on_optional_chest(self):
        p, s, potion = fixture()
        before = copy.deepcopy(s)
        journey = plan_journey(p, s, [], neighbors, probe_kind="flight", plan_only=True)
        self.assertIsNotNone(journey)
        self.assertEqual(2189, journey.route[-1],
                         "Prefer a budgeted matching key while observed locks exceed held keys")
        self.assertLessEqual(2 * (len(journey.route)-1) + journey.interaction_budget + 3, 20)
        self.assertEqual(before, s)
        self.assertIsNone(p.room_journey)
        d = stage_known_flight(p, s, potion, neighbors)
        self.assertEqual(dict(type="item", id="flight", action="DRINK"), d.action)
        self.assertEqual(2189, p.room_journey.route[-1])
        self.assertEqual("protect", p.room_journey.stage)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)

    def test_no_key_deficit_preserves_short_chest_trip(self):
        p, s, _ = fixture()
        p.keys["golden"] = 4
        j = plan_journey(p, s, [], neighbors, probe_kind="flight", plan_only=True)
        self.assertEqual(2286, j.route[-1])

    def test_key_priority_does_not_bypass_route_or_duration_gates(self):
        for case in ("blocked-keys", "short-duration", "enemy", "heavy"):
            with self.subTest(case=case):
                p, s, _ = fixture()
                enemies = []
                if case == "blocked-keys":
                    p.blocked.update((2189, 2484, 2489))
                elif case == "short-duration":
                    s["hero"]["buffs"] = [dict(name="levitating",
                        description="Turns of levitation remaining: 12.")]
                elif case == "enemy":
                    enemies = [dict(cell=2185, name="gnoll scout")]
                else:
                    s["inventory"].append(dict(name="leather armor", equipped=True,
                        identified=False, description="Requires 12 strength."))
                j = plan_journey(p, s, enemies, neighbors, probe_kind="flight", plan_only=True)
                if case in {"enemy", "heavy"}:
                    self.assertIsNone(j)
                else:
                    self.assertEqual(2286, j.route[-1])


if __name__ == "__main__":
    unittest.main()
