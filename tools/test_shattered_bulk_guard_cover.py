"""Reduced public geometry from run 000202 decision 3713.

The optional plan is an isolated plan-shaped probe, not recovered run memory.
No actions are dispatched and no changed-decision future is supplied.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.ranged_tactics import choose


def fixture(committed=False, bulk=True, equipped=True):
    terrain = {
        766: 14, 767: 27, 768: 4, 769: 4, 770: 4, 771: 4,
        802: 14, 803: 27, 804: 4, 805: 1, 806: 20, 807: 1,
        838: 14, 839: 14, 840: 5, 841: 1, 842: 4, 843: 4,
        874: 14, 875: 14, 876: 4, 877: 4, 878: 4, 879: 4,
    }
    s = dict(
        scene="GameScene", status="ready", modal=False, depth=8, branch=0,
        hero=dict(cell=805, hp=17, max_hp=70, name="mage", strength=13,
                  buffs=[], talents=[]),
        inventory=[dict(
            id="armor", name="leather armor of bulk" if bulk else "leather armor",
            identified=True, equipped=equipped, actions=["UNEQUIP"],
            description="This tier-2 armor blocks 0-4 damage and requires 12 strength.")],
        danger_cells=[], ui=dict(texts=[], buttons=[]),
        objects=[dict(name="prison guard", cell=807,
                      health_bar=[4, 16], status_icons=["pincushion"])],
        map=dict(width=36, height=46, cells=[
            dict(cell=c, terrain=t, observed=True,
                 visible=c not in {766, 767, 802, 803, 838, 839, 874, 875, 879},
                 effects=[])
            for c, t in terrain.items()]))
    p = MagePolicy()
    p.update(s)
    if committed:
        p.ranged_plan = dict(name="prison guard", goal=802, mode="cover",
                             steps=3, waits=0, hp=17, dot=False, harmful=[])
    return s, p


class BulkGuardCoverTests(unittest.TestCase):
    def test_committed_cover_replans_before_exposed_bulk_door(self):
        s, p = fixture(committed=True)
        before = copy.deepcopy(s)
        self.assertTrue(p.enemy_can_see(s, s["objects"][0], 840))
        self.assertFalse(p.enemy_can_see(s, s["objects"][0], 841))
        d = choose(p, s, s["objects"], escape_only=True)
        self.assertEqual(dict(type="cell", cell=841), d.action)
        self.assertEqual(841, p.ranged_plan["goal"])
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)

    def test_new_cover_does_not_use_bulk_door_when_other_bank_is_blocked(self):
        s, p = fixture()
        p.tiles[841]["trap"] = "burning trap"
        self.assertIsNone(choose(p, s, s["objects"], escape_only=True))
        self.assertIsNone(p.ranged_plan)

    def test_open_door_is_not_a_fast_bulk_escape_either(self):
        s, p = fixture(committed=True)
        p.tiles[840]["terrain"] = 6
        d = choose(p, s, s["objects"], escape_only=True)
        self.assertEqual(dict(type="cell", cell=841), d.action)

    def test_failed_committed_cover_does_not_relax_alternative_hazard(self):
        s, p = fixture(committed=True)
        p.tiles[841]["trap"] = "burning trap"
        self.assertIsNone(choose(p, s, s["objects"], escape_only=True))
        self.assertIsNone(p.ranged_plan)

    def test_normal_or_unworn_bulk_armor_keeps_existing_cover_admission(self):
        for bulk, equipped in ((False, True), (True, False)):
            with self.subTest(bulk=bulk, equipped=equipped):
                s, p = fixture(committed=True, bulk=bulk, equipped=equipped)
                d = choose(p, s, s["objects"], escape_only=True)
                self.assertEqual(dict(type="cell", cell=840), d.action)
                self.assertEqual(802, p.ranged_plan["goal"])


if __name__ == "__main__":
    unittest.main()
