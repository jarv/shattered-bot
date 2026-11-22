"""Reduced public selector fixture from run 000132 decision 761, line 2217.

This is not recovered runtime memory or a replay. No unknown identity is supplied.
"""
import unittest

from tools.consumable_tactics import choose_consumable, discovery_menu, identify_context
from tools.policy_geometry import distance, neighbors
from tools.test_challenge_rules import verified


def scene():
    s = dict(scene="GameScene", status="ready", modal=False, depth=3,
             danger_cells=[], map=dict(width=37, height=42, cells=[
                 dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
                 for t, cells in ((4, (644, 681, 718)), (1, (645, 682, 719)),
                                  (29, (646, 683, 720))) for c in cells]),
             hero=dict(name="mage", cell=682, hp=30, max_hp=30,
                       buffs=[dict(name="hungry")], talents=[]),
             inventory=[
                 dict(id="item-8", name="scroll of identify", identified=True,
                      quantity=1, actions=["READ"]),
                 dict(id="item-9", name="scroll of GYFU", identified=False,
                      quantity=1, actions=["READ"]),
                 dict(id="item-3", name="spear", identified=False, quantity=1,
                      actions=["EQUIP"])],
             objects=[], ui=dict(texts=[], buttons=[]))
    p = verified()
    p.update(s)
    return s, p


def select(s, p):
    return choose_consumable(p, s, s["objects"], distance, neighbors)


class ScrollIdentifyBeforeReadTests(unittest.TestCase):
    def test_known_identify_precedes_unknown_scroll_activation(self):
        s, p = scene()
        d = select(s, p)
        self.assertEqual(dict(type="item", id="item-8", action="READ"), d.action)
        self.assertEqual("discover-scroll", p.menu_plan)
        self.assertNotIn("scroll of gyfu", p.tested_scrolls)
        self.assertEqual(0, p.consumable_cooldown)
        self.assertFalse(s["inventory"][1]["identified"])

    def test_menu_targets_scroll_not_higher_quantity_equipment(self):
        s, p = scene()
        s["inventory"][2]["quantity"] = 10
        s["ui"] = dict(texts=["Identify an item"], buttons=[
            dict(id="equipment", label="spear"), dict(id="scroll", label="scroll of GYFU")])
        self.assertEqual("scroll", discovery_menu(p, s).action["id"])
        self.assertFalse(s["inventory"][1]["identified"])

    def test_potion_priority_is_preserved(self):
        s, p = scene()
        s["inventory"].append(dict(id="potion", name="azure potion", identified=False,
                                   quantity=1, actions=["DRINK"]))
        self.assertEqual("item-8", select(s, p).action["id"])
        s["ui"] = dict(texts=["Identify an item"], buttons=[
            dict(id="scroll", label="scroll of GYFU"), dict(id="potion", label="azure potion")])
        self.assertEqual("potion", discovery_menu(p, s).action["id"])

    def test_bag_navigation_does_not_substitute_equipment_for_scroll(self):
        s, p = scene()
        s["ui"] = dict(texts=["Identify an item"], buttons=[
            dict(id="equipment", label="spear"), dict(id="bag", label="scroll holder")])
        self.assertEqual("bag", discovery_menu(p, s).action["id"])

    def test_scroll_testing_without_identify_retains_original_selection(self):
        s, p = scene()
        s["inventory"].pop(0)
        self.assertEqual(dict(type="item", id="item-9", action="READ"), select(s, p).action)

    def test_existing_safety_and_retry_gates_remain(self):
        for blocker in ("blind", "starving", "hurt", "danger", "enemy", "failed"):
            with self.subTest(blocker=blocker):
                s, p = scene()
                if blocker in ("blind", "starving"):
                    s["hero"]["buffs"] = [dict(name=blocker)]
                elif blocker == "hurt":
                    s["hero"]["hp"] = 20
                elif blocker == "danger":
                    s["danger_cells"] = [682]
                elif blocker == "enemy":
                    s["objects"] = [dict(name="gnoll scout", cell=645)]
                else:
                    p.failed_identify_context = identify_context(s)
                self.assertIsNone(select(s, p))


if __name__ == "__main__":
    unittest.main()
