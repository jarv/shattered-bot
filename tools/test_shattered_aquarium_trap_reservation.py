"""Run 239: a confusion trap near aquarium gold is not a flight puzzle.

Reduced public geometry from decisions 691--693 and 780, played revision
e9d784dc4f4f533bb45cc404d3dfa400c294d518. This is not runtime memory.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance
from tools.puzzle_supplies import demands
from tools.room_supplies import requirements
from tools.priority_resources import targets


def fixture():
    cells = {}
    for y in range(14, 20):
        for x in range(14, 21):
            c = y * 33 + x
            cells[c] = dict(cell=c, terrain=4, observed=True, visible=True)
    for c in (477, 478, 479, 480, 481, 510, 514, 576, 609, 610, 611):
        cells[c]["terrain"] = 1
    for c in (511, 512, 513, 544, 546, 577, 578, 579):
        cells[c]["terrain"] = 14
    cells[545]["terrain"] = 29
    cells[543].update(terrain=18, trap="confusion gas trap")
    s = dict(scene="GameScene", status="ready", modal=False, depth=2, branch=0,
             hero=dict(cell=610, hp=30, max_hp=30, strength=10, buffs=[]),
             danger_cells=[], inventory=[], ui=dict(texts=[]),
             objects=[dict(cell=545, name="giant piranha", sleeping=True),
                      dict(cell=512, name="gold x93",
                           top_item=dict(name="gold", quantity=93, identified=True))],
             map=dict(width=33, height=38, cells=list(cells.values())))
    p = MagePolicy()
    p.update(s)
    return p, s


class AquariumTrapReservationTests(unittest.TestCase):
    def test_dry_ring_gold_does_not_reserve_flight_or_admit_shore(self):
        p, s = fixture()
        before = copy.deepcopy(s)
        self.assertEqual("aquarium", p.piranha_habitats[545]["profile"])
        self.assertNotIn(512, p.paths(s))
        self.assertFalse([d for d in requirements(p, s) if d.kind == "flight"],
                         "Fish-blocked gold with a known trap-free dry approach is not a flight reward")
        self.assertEqual(before, s)
        self.assertIn(512, p.loot)
        self.assertIn(512, p.room_blocked)
        self.assertNotIn(512, p.paths(s))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)

    def test_unknown_or_trapped_dry_approaches_keep_reservation(self):
        for case in ("unknown", "traps", "candidate"):
            with self.subTest(case=case):
                p, s = fixture()
                ring = (511, 512, 513, 544, 546, 577, 578, 579)
                if case == "unknown":
                    for c in ring:
                        if c != 512:
                            p.tiles[c]["observed"] = False
                elif case == "traps":
                    for c in ring:
                        if c != 512:
                            p.tiles[c].update(terrain=18, trap="confusion gas trap")
                else:
                    p.piranha_habitats[545]["profile"] = "candidate"
                self.assertTrue([d for d in demands(p, s, distance) if d.kind == "flight"])

    def test_real_flight_reward_and_mandatory_pickup_survive(self):
        p, s = fixture()
        p.tiles[543]["terrain"] = 0
        p.loot[543] = dict(cell=543, name="scroll of upgrade",
                           top_item=dict(name="scroll of upgrade", identified=True))
        self.assertTrue([d for d in requirements(p, s) if d.kind == "flight"])
        self.assertIn(543, targets(p))
        self.assertNotIn(543, p.paths(s))
        self.assertFalse(p.loot_collection_receipts)

    def test_dry_ring_progression_loot_is_still_mandatory_and_blocked(self):
        p, s = fixture()
        p.loot[512].update(name="scroll of upgrade",
                           top_item=dict(name="scroll of upgrade", identified=True))
        self.assertFalse([d for d in requirements(p, s) if d.kind == "flight"])
        self.assertIn(512, targets(p))
        self.assertIn(512, p.room_blocked)
        self.assertNotIn(512, p.paths(s))
        self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
