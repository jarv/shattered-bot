"""Reduced public run 156 D1107 geometry; isolated selectors, not replay."""
import unittest

from tools import multi_enemy_tactics as multi
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=666, hp=35, max_hp=35, strength=12,
                     buffs=[{"name": "hungry"}, {"name": "barrier"}])
    terrain = {
        605: 4, 606: 10, 607: 4, 635: 4, 636: 20, 637: 4,
        638: 4, 639: 4, 640: 4, 665: 4, 666: 1, 667: 4,
        668: 1, 669: 1, 670: 1, 695: 4, 696: 20, 697: 6,
        698: 1, 699: 29, 700: 1, 725: 4, 726: 4, 727: 4,
        728: 1, 729: 29, 730: 1, 757: 4, 758: 1, 759: 29, 760: 1,
    }
    s["map"] = dict(width=30, height=45, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [
        dict(name="swarm of flies", cell=697, health_bar=[3, 21],
             status_icons=["pincushion"]),
        dict(name="swarm of flies", cell=698, health_bar=[3, 21])]
    s["inventory"] = [dict(
        id="staff", name="staff of magic missile +1", status="1/5",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["ZAP", "IMBUE", "UNEQUIP"],
        description="This melee weapon deals 2-8 damage and requires 10 strength.")]
    p = verified()
    p.update(s)
    return p, s


class MultiRetreatLockedPocketTests(unittest.TestCase):
    def test_non_choke_locked_pocket_is_not_a_retreat_objective(self):
        p, s = fixture()
        self.assertFalse(multi.single_file(p, s, s["objects"], 636))
        self.assertLessEqual(multi.approach_pressure(p, s, s["objects"], 636), 1)
        d = multi.choose(p, s, s["objects"])
        self.assertTrue(d is None or d.action != {"type": "cell", "cell": 636},
                        "Low approach pressure is not an onward exit past locked door 606")

    def test_full_selector_does_not_dispatch_the_pocket_retreat(self):
        p, s = fixture()
        d = p.choose(s)
        self.assertNotEqual({"type": "cell", "cell": 636}, d.action)
        self.assertEqual({"type": "item", "id": "staff", "action": "ZAP"}, d.action)
        self.assertEqual("unit-engagement", d.controller)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_observed_clear_onward_floor_still_admits_retreat(self):
        p, s = fixture()
        p.tiles[606]["terrain"] = 1
        d = multi.choose(p, s, s["objects"])
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 636}, d.action)

    def test_hazard_loot_or_unknown_onward_space_is_not_an_exit(self):
        for case in ("trap", "loot", "unknown"):
            with self.subTest(case=case):
                p, s = fixture()
                p.tiles[606]["terrain"] = 1
                if case == "trap":
                    p.tiles[606].update(terrain=18, trap="shocking trap")
                elif case == "loot":
                    p.loot[606] = dict(cell=606, name="potion of strength")
                else:
                    del p.tiles[606]
                d = multi.choose(p, s, s["objects"])
                self.assertTrue(d is None or d.action != {"type": "cell", "cell": 636})

    def test_verified_door_choke_does_not_require_an_onward_exit(self):
        p, s = fixture()
        p.tiles[666]["terrain"] = 6
        self.assertTrue(multi.single_file(p, s, s["objects"], 636))
        d = multi.choose(p, s, s["objects"])
        self.assertIsNotNone(d)
        self.assertEqual({"type": "cell", "cell": 636}, d.action)


if __name__ == "__main__":
    unittest.main()
