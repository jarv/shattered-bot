"""Reduced public upgrade menu from recording 000055, decision 2161.

Only allocation and menu state are reconstructed, not whole-run memory.
Post-navigation menus below are isolated fixtures, not replay observations.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Finished
from tools.policy_interaction import MenuPhase, menu
from tools.upgrade_tactics import choose_upgrade


def fixture():
    staff = dict(name="staff of magic missile +3", identified=True,
                 upgradable=True, actions=["IMBUE", "ZAP"],
                 description="Each bolt deals 5-14 damage.")
    wand = dict(name="wand of prismatic light", identified=True,
                upgradable=True, curse_known=True, known_cursed=False,
                status="2/2", actions=["ZAP"],
                description="The beam deals 4-14 damage.")
    s = dict(scene="GameScene", modal=True, status="menu",
             hero=dict(strength=12, hp=50, max_hp=50),
             inventory=[staff, wand, dict(name="scroll of upgrade", quantity=1)],
             ui=dict(texts=["Upgrade an item"], buttons=[
                 dict(id="button-0", label=staff["name"]),
                 dict(id="button-1", label="leather armor +1"),
                 dict(id="button-11", label="Backpack"),
                 dict(id="button-12", label="Velvet Pouch"),
                 dict(id="button-13", label="Magical Holster")]))
    p = MagePolicy()
    p.menu_plan = MenuPhase.UPGRADE_SELECT
    p.upgrade_target = choose_upgrade(s)[0]["name"]
    return p, s


class UpgradeHolsterSelectionTests(unittest.TestCase):
    def open_holster(self, p, s):
        try:
            return menu(p, s)
        except Finished:
            self.fail("Allocated carried wand requires the visible holster tab, not a blocked menu")

    def test_recorded_allocation_opens_visible_holster_not_wrong_staff(self):
        p, s = fixture()
        self.assertEqual("wand of prismatic light", p.upgrade_target)
        self.assertEqual({"type": "button", "id": "button-13"}, self.open_holster(p, s).action)
        self.assertEqual("wand of prismatic light", p.upgrade_target)
        # Independent UI fixture: still requires exact target and confirmation.
        s["ui"]["buttons"].append(dict(id="wand", label=p.upgrade_target))
        self.assertEqual({"type": "button", "id": "wand"}, menu(p, s).action)
        self.assertEqual(MenuPhase.UPGRADE_CONFIRM, p.menu_plan)
        s["ui"]["buttons"] = [dict(id="confirm", label="Upgrade")]
        self.assertEqual({"type": "button", "id": "confirm"}, menu(p, s).action)
        self.assertIsNone(p.menu_plan)
        self.assertIsNone(p.upgrade_target)

    def test_unavailable_target_after_one_tab_still_fails_closed(self):
        p, s = fixture()
        self.open_holster(p, s)
        with self.assertRaises(Finished):
            menu(p, s)
        self.assertEqual("wand of prismatic light", p.upgrade_target)

    def test_visible_target_wins_without_navigation(self):
        p, s = fixture()
        s["ui"]["buttons"].append(dict(id="wand", label=p.upgrade_target))
        self.assertEqual("wand", menu(p, s).action["id"])
        self.assertEqual(MenuPhase.UPGRADE_CONFIRM, p.menu_plan)

    def test_no_guessing_absent_tab_nonwand_or_missing_inventory(self):
        for case in ("absent-tab", "nonwand", "missing-inventory"):
            with self.subTest(case=case):
                p, s = fixture()
                if case == "absent-tab":
                    s["ui"]["buttons"].pop()
                elif case == "nonwand":
                    p.upgrade_target = "ring of haste"
                else:
                    s.pop("inventory")
                with self.assertRaises(Finished):
                    menu(p, s)


if __name__ == "__main__":
    unittest.main()
