"""Reduced run 155 D29 public geometry, not recorded runtime memory.

The hold is reconstructed from accepted D27 and the D28 entry strike.
These are isolated selector probes, never changed-policy continuation.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.doorway_tactics import hold_doorway
from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=1, branch=0)
    s["hero"].update(cell=285, hp=19, max_hp=20, buffs=[])
    terrain = {259: 4, 260: 4, 261: 4, 284: 4, 285: 1, 286: 5,
               309: 4, 310: 6, 311: 4, 333: 1, 334: 1, 335: 29,
               358: 1, 359: 1, 360: 29}
    s["map"] = dict(width=25, height=41, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="marsupial rat", cell=310, health_bar=[11, 21]),
                    dict(name="marsupial rat", cell=334)]
    s["inventory"] = [dict(id="item-0", name="staff of magic missile",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        status="4/4", actions=["ZAP", "UNEQUIP", "IMBUE"],
        description="This tier-1 melee weapon deals 1-6 damage and requires 10 strength.")]
    p = MagePolicy()
    p.update(s)
    p.doorway_hold = dict(depth=1, door=310, hide=285, inputs=1, quiet=0, waits=0)
    return p, s


class ContactRatChokeTests(unittest.TestCase):
    def test_recorded_contact_rat_does_not_invent_a_second_attack_slot(self):
        p, s = fixture()
        self.assertTrue(multi.single_file(p, s, s["objects"], 285))
        self.assertEqual(1, multi.approach_pressure(p, s, s["objects"], 285))
        self.assertFalse(multi.needs_retreat(p, s, s["objects"]))
        self.assertIsNone(multi.choose(p, s, s["objects"]))
        d = hold_doorway(p, s, s["objects"], distance, neighbors, line_clear)
        self.assertEqual({"type": "cell", "cell": 310}, d.action)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_prospective_step_keeps_conservative_approach_pressure(self):
        p, s = fixture()
        # A move to the adjacent door is not the stationary choke decision.
        self.assertEqual(2, multi.approach_pressure(p, s, s["objects"], 286))

    def test_no_established_hold_keeps_conservative_pressure(self):
        p, s = fixture()
        p.doorway_hold = None
        self.assertEqual(2, multi.approach_pressure(p, s, s["objects"], 285))

    def test_fast_or_other_species_are_not_given_stationary_rat_admission(self):
        for change in (dict(status_icons=["adrenaline"]), dict(name="swarm of flies")):
            with self.subTest(change=change):
                p, s = fixture()
                s["objects"][0].update(change)
                self.assertGreater(multi.approach_pressure(p, s, s["objects"], 285), 1)

    def test_real_contact_flank_and_unknown_geometry_still_require_retreat(self):
        p, s = fixture()
        s["objects"][1]["cell"] = 286
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))
        p, s = fixture()
        p.tiles.pop(259)
        self.assertFalse(multi.single_file(p, s, s["objects"], 285))
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))


if __name__ == "__main__":
    unittest.main()
