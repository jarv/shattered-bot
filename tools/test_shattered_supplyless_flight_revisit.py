"""Reduced selector fixture for run 000069 decisions 993-1002.

Public resource facts: hungry, full health, food and known healing, no flight
supply or unknown potion; protected loot competes with a usable keyed route.
Geometry is synthetic. This is not recovered runtime memory or a game replay.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.priority_resources import choose, targets
from tools.puzzle_supplies import prepare_supplies
from tools.tactical_recovery import locked_room_route


def fixture():
    s = dict(
        scene="GameScene", status="ready", modal=False, depth=3, branch=0,
        danger_cells=[], ui=dict(texts=[], buttons=[]),
        hero=dict(cell=64, hp=30, max_hp=30, strength=12, level=3,
                  buffs=[dict(name="hungry")], talents=[]),
        inventory=[
            dict(id="food", name="ration of food x2", quantity=2, actions=["EAT"]),
            dict(id="healing", name="potion of healing", quantity=1,
                 identified=True, actions=["DRINK"])],
        map=dict(width=15, height=9, cells=[
            dict(cell=c, observed=True, visible=c % 15 <= 4,
                 terrain=4 if c % 15 in {0, 14} or c // 15 in {0, 8}
                 else 10 if c == 61 else 0 if 9 <= c % 15 <= 12
                 else 29 if c == 67 else 1)
            for c in range(135)]),
        objects=[])
    p = MagePolicy()
    p.update(s)
    # Remembered protected food corresponds to the recording's trap-room ration.
    p.loot[73] = dict(cell=73, name="ration of food",
                      top_item=dict(name="ration of food", quantity=1))
    p.keys["iron"] = 1
    return p, s


class SupplylessFlightRevisitTests(unittest.TestCase):
    def test_no_supply_preparation_does_not_reverse_keyed_progress(self):
        p, s = fixture()
        keyed = locked_room_route(p, s)
        self.assertIsNotNone(keyed)
        self.assertLess(keyed.action["cell"] % 15, s["hero"]["cell"] % 15)
        self.assertIsNone(
            choose(p, s, []),
            "Supplyless flight staging must yield instead of reversing keyed progress")
        self.assertEqual(keyed.action, locked_room_route(p, s).action)
        self.assertEqual(0, p.puzzle_revisit_steps["flight"])
        self.assertIn(73, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)
        self.assertNotIn((3, "puzzle-meal"), p.room_attempts)

    def test_supplyless_yield_preserves_mandatory_progression_pickup(self):
        p, s = fixture()
        p.loot[73] = dict(cell=73, name="scroll of upgrade",
                          top_item=dict(name="scroll of upgrade"))
        self.assertIsNone(choose(p, s, []))
        self.assertIn(73, targets(p))
        self.assertFalse(p.loot_collection_receipts)

    def test_untried_unknown_supply_still_allows_guarded_revisit(self):
        p, s = fixture()
        # Isolate post-meal staging without inventing any accepted game input.
        p.room_attempts.add((3, "puzzle-meal"))
        s["inventory"].append(dict(id="unknown", name="azure potion",
                                   quantity=1, actions=["DRINK"]))
        d = prepare_supplies(p, s, [], distance, neighbors)
        self.assertIsNotNone(d)
        self.assertIn("revisit levitation-room", d.reason)
        self.assertGreater(d.action["cell"] % 15, s["hero"]["cell"] % 15)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)

    def test_unusable_or_already_tested_unknown_is_not_a_supply(self):
        for case in ("no-drink", "tested"):
            with self.subTest(case=case):
                p, s = fixture()
                p.room_attempts.add((3, "puzzle-meal"))
                s["inventory"].append(dict(
                    id="unknown", name="azure potion", quantity=1,
                    actions=[] if case == "no-drink" else ["DRINK"]))
                if case == "tested":
                    p.puzzle_drinks.add((3, "azure potion"))
                self.assertIsNone(prepare_supplies(p, s, [], distance, neighbors))
                self.assertIn(73, p.loot)


if __name__ == "__main__":
    unittest.main()
