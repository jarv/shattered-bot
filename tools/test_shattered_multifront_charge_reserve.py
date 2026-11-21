"""Reduced public decision 284 from recording 000056, not a gameplay replay."""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_nodes import ordinary_combat
from tools.policy_runtime import Context


def fixture():
    p = MagePolicy()
    p.depth = 2
    staff = dict(id="item-0", name="staff of magic missile", status="1/4",
                 identified=True, curse_known=True, known_cursed=False,
                 equipped=True, actions=["IMBUE", "ZAP", "THROW"],
                 description="This tier-1 melee weapon deals 1-6 damage and requires 10 strength. "
                             "Each bolt from this wand deals 2-8 damage.")
    enemies = [dict(name="gnoll scout", cell=1053),
               dict(name="marsupial rat", cell=1168),
               dict(name="marsupial rat", cell=1169)]
    s = dict(depth=2, status="ready", modal=False, danger_cells=[],
             hero=dict(cell=1164, name="mage", hp=23, max_hp=25, strength=10),
             map=dict(width=36, height=40), inventory=[staff], objects=enemies)
    # Only the public firing lanes relevant to this leaf are retained.
    p.tiles = {cell: dict(cell=cell, terrain=terrain, visible=True)
               for cell, terrain in [(1053, 1), (1090, 29), (1127, 1),
                                     (1164, 6), (1165, 1), (1166, 1),
                                     (1167, 19), (1168, 29), (1169, 29)]}
    p.planner.report["unit_target"] = 1053
    return p, s, enemies


class MultifrontChargeReserveTests(unittest.TestCase):
    def test_recorded_multifront_pressure_uses_admitted_charge_not_approach_wait(self):
        p, s, enemies = fixture()
        self.assertTrue(p.shot_clear(s, 1053))
        action = ordinary_combat(Context(p, s, enemies=enemies, active=enemies, engage=enemies))
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"}, action.action)
        self.assertEqual(1053, p.target)

    def test_isolated_ordinary_enemy_still_preserves_scarce_charge(self):
        p, s, enemies = fixture()
        s["objects"] = enemies[:1]
        action = ordinary_combat(Context(p, s, enemies=enemies[:1],
                                        active=enemies[:1], engage=enemies[:1]))
        self.assertEqual({"type": "wait"}, action.action)

    def test_blocked_shot_and_empty_staff_do_not_invent_an_attack(self):
        for mode in ("blocked", "empty"):
            with self.subTest(mode=mode):
                p, s, enemies = fixture()
                if mode == "blocked":
                    p.tiles[1090]["terrain"] = 4
                else:
                    s["inventory"][0]["status"] = "0/4"
                action = ordinary_combat(Context(p, s, enemies=enemies,
                                                active=enemies, engage=enemies))
                self.assertEqual({"type": "wait"}, action.action)


if __name__ == "__main__":
    unittest.main()
