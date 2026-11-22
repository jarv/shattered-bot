"""Run 95: completed trap room above a wall is not a crystal-room supply."""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance
from tools.puzzle_supplies import demands
from tools.room_supplies import requirements


def fixture():
    # Public coordinates: trap 541, solid wall row 568--574, crystal door
    # 632 and uncollected chest 633. The earlier flight reward was at 480.
    cells = {}
    for y in range(15, 22):
        for x in range(8, 18):
            c = y * 31 + x
            terrain = (18 if y <= 17 and 10 <= x <= 14 else
                       1 if y <= 17 and x == 15 else 4)
            cells[c] = dict(cell=c, terrain=terrain, observed=True, visible=True)
    for c, terrain in {535:20, 536:5, 480:11, 630:1, 631:1,
                       632:31, 633:14, 602:14, 603:14}.items():
        cells[c] = dict(cell=c, terrain=terrain, observed=True, visible=True)
    s = dict(scene="GameScene", status="ready", modal=False, depth=1,
             hero=dict(cell=535, hp=25, max_hp=25, strength=10, buffs=[]),
             inventory=[], objects=[], danger_cells=[],
             map=dict(width=31, height=32, cells=list(cells.values())))
    p = MagePolicy()
    p.update(s)
    p.loot[633] = dict(cell=633, name="Chest")
    p.completed_room_rewards.add((1, "flight", 480))
    return p, s


class FlightWallSeparationTests(unittest.TestCase):
    def test_crystal_chest_across_solid_wall_does_not_reserve_flight(self):
        p, s = fixture()
        self.assertFalse([d for d in requirements(p, s) if d.kind == "flight"],
                         "Proximity across the observed wall is not a flight retrieval")
        self.assertIn(633, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_real_unfinished_reward_still_requires_flight(self):
        p, s = fixture()
        p.loot[480] = dict(cell=480, name="scroll of upgrade")
        p.completed_room_rewards.clear()
        self.assertTrue([d for d in requirements(p, s) if d.kind == "flight"])
        self.assertIn(480, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_unknown_separator_does_not_certify_unrelated_loot(self):
        p, s = fixture()
        # Without a positively observed separator, retain the conservative
        # reservation. Missing geometry is not proof the reward is unrelated.
        for c in range(568, 575):
            p.tiles.pop(c, None)
        self.assertTrue([d for d in demands(p, s, distance,
                                           include_deferred=True)
                         if d.kind == "flight"])


if __name__ == "__main__":
    unittest.main()
