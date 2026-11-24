"""Run 247 D655: spent flame must not preempt ordinary floor observation.

Reduced public geometry (668 -> 625 frontier, stairs at 960, shelf at 1376).
This is a deterministic selector fixture, not recovered runtime memory.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.room_supplies import descend, depleted


def fixture():
    cells = {668: 2, 625: 1, 710: 6, 751: 1, 792: 1,
             834: 5, 875: 1, 917: 1, 960: 8, 1376: 27}
    s = dict(scene="GameScene", status="ready", modal=False, depth=2, branch=0,
             observation_id=1312, danger_cells=[], objects=[],
             ui=dict(texts=[], buttons=[]),
             hero=dict(cell=668, hp=30, max_hp=30, level=3, strength=10,
                       buffs=[], talents=[]),
             inventory=[dict(id="unknown", name="indigo potion", quantity=1,
                             identified=False, actions=["DRINK", "DROP", "THROW"])],
             map=dict(width=42, height=42, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
                 for c, t in cells.items()]))
    p = MagePolicy()
    p.update(s)
    # Reduced bookkeeping premise: the recording has an accepted floor-flame
    # consumption receipt at D470, not an inferred unknown-potion identity.
    p.room_supply_spent_elsewhere.add("potion of liquid flame")
    return s, p


class SpentSupplyFrontierTests(unittest.TestCase):
    def test_spent_flame_yields_to_existing_frontier_selector(self):
        s, p = fixture()
        self.assertEqual({"flame"}, depleted(p, s))
        self.assertIsNone(descend(p, s, []),
                          "One spent room supply must not abandon observed floor work")
        d = p.explore(s, [])
        self.assertEqual(Intent.EXPLORE, d.intent)
        self.assertEqual(dict(type="cell", cell=625), d.action)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.puzzle_probe)

    def test_unopened_door_also_prevents_early_supply_descent(self):
        s, p = fixture()
        from unittest.mock import patch
        with patch.object(p, "exploration_report", return_value={
                "unexplored_frontiers": [], "unopened_doors": [834]}):
            self.assertIsNone(descend(p, s, []))

    def test_exhausted_supply_descent_remains_after_ordinary_work(self):
        s, p = fixture()
        from unittest.mock import patch
        with patch.object(p, "exploration_report", return_value={
                "unexplored_frontiers": [], "unopened_doors": []}):
            d = descend(p, s, [])
        self.assertEqual(Intent.DESCEND, d.intent)
        self.assertFalse(p.completed_room_rewards)


if __name__ == "__main__":
    unittest.main()
