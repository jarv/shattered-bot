"""Run 152 D23: reduced public choke and accepted D22 hold, not runtime memory."""
import unittest

from tools.mage_policy import MagePolicy
from tools import multi_enemy_tactics as multi
from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=1, branch=0)
    s["hero"].update(cell=418, hp=20, max_hp=20, strength=10, buffs=[])
    # Public D23 geometry, restricted to the entry, holding pocket and
    # the alternative route which the recording selected toward door 540.
    groups = {
        4: [337, 376, 377, 378, 457, 460, 498, 500, 501, 539],
        12: [417],
        1: [338, 339, 379, 380, 418, 420, 421, 422, 459, 461, 499],
        29: [340, 381, 458],
        6: [419],
        5: [540],
    }
    s["map"] = dict(width=41, height=26, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for t, cells in groups.items() for c in cells])
    s["objects"] = [dict(name="marsupial rat", cell=340),
                     dict(name="marsupial rat", cell=419)]
    s["inventory"] = [dict(id="item-0", name="staff of magic missile",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        status="3/4", actions=["ZAP", "UNEQUIP", "IMBUE"],
        description="This tier-1 melee weapon deals 1-6 damage and requires 10 strength.")]
    p = MagePolicy()
    p.update(s)
    # Reconstruction of the hold established by accepted D22, not a new
    # observation or a claim that the encounter is cleared.
    p.doorway_hold = dict(depth=1, door=419, hide=418, inputs=0, quiet=0, waits=0)
    return p, s


class OccupiedChokeRetentionTests(unittest.TestCase):
    def test_entry_occupant_does_not_invalidate_single_file_hold(self):
        p, s = fixture()
        enemies = s["objects"]
        self.assertEqual(1, multi.approach_pressure(p, s, enemies, 418))
        self.assertTrue(multi.single_file(p, s, enemies, 418),
                        "The entry occupant occupies the blocked gate, not a second flank")
        self.assertFalse(multi.needs_retreat(p, s, enemies))
        self.assertIsNone(multi.choose(p, s, enemies))
        self.assertIsNone(p.multi_door_plan)
        d = hold_doorway(p, s, enemies, distance, neighbors, line_clear)
        self.assertEqual({"type": "cell", "cell": 419}, d.action)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_real_flank_still_invalidates_hold(self):
        p, s = fixture()
        s["objects"][0]["cell"] = 459
        self.assertFalse(multi.single_file(p, s, s["objects"], 418))
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))

    def test_unknown_surroundings_are_not_certified(self):
        p, s = fixture()
        p.tiles.pop(377)
        self.assertFalse(multi.single_file(p, s, s["objects"], 418))

    def test_unoccupied_entry_still_qualifies(self):
        p, s = fixture()
        s["objects"][1]["cell"] = 379
        self.assertTrue(multi.single_file(p, s, s["objects"], 418))
        self.assertFalse(multi.needs_retreat(p, s, s["objects"]))

    def test_ranged_pressure_is_not_erased_by_gate_connectivity(self):
        p, s = fixture()
        s["objects"][0].update(name="gnoll trickster", cell=420)
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))


if __name__ == "__main__":
    unittest.main()
