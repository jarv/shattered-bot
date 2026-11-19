import unittest

from tools.upgrade_tactics import choose_upgrade, strength_reduction
from tools.test_survival_bot import state


class UpgradeTests(unittest.TestCase):
    def setup_state(self, staff_level=0, scrolls=1):
        s = state()
        s["depth"] = 6
        s["hero"]["strength"] = 13
        s["inventory"][0]["name"] += f" +{staff_level}" if staff_level else ""
        s["inventory"] += [{"name": "scroll of upgrade", "quantity": scrolls, "actions": ["READ"]},
                           {"name": "cloth armor", "equipped": True, "identified": True,
                            "description": "This tier-1 armor blocks 0-2 damage and requires 10 strength."}]
        return s

    def test_strength_breakpoints_are_triangular_not_every_upgrade(self):
        self.assertEqual([0, 1, 1, 2, 2, 2, 3], [strength_reduction(i) for i in range(7)])

    def test_first_upgrade_goes_to_staff(self):
        s = self.setup_state()
        self.assertIs(s["inventory"][0], choose_upgrade(s)[0])

    def test_staff_has_early_target_then_retains_one_flexible_scroll(self):
        self.assertIsNotNone(choose_upgrade(self.setup_state(2)))
        self.assertIsNone(choose_upgrade(self.setup_state(3)))
        self.assertIsNotNone(choose_upgrade(self.setup_state(3, scrolls=2)))

    def test_one_upgrade_unlocking_identified_mail_beats_more_staff_damage(self):
        s = self.setup_state(3)
        mail = {"name": "mail armor", "identified": True,
                "description": "This tier-3 armor blocks 0-6 damage and requires 14 strength."}
        s["inventory"].append(mail)
        self.assertIs(mail, choose_upgrade(s)[0])

    def test_unknown_or_cursed_armor_is_not_treated_as_a_known_breakpoint(self):
        for fields in ({"identified": False}, {"identified": True, "known_cursed": True}):
            s = self.setup_state(3)
            s["inventory"].append(dict(name="mail armor", description="Typically this tier-3 armor blocks 0-6 damage and requires 14 strength.", **fields))
            self.assertIsNone(choose_upgrade(s))

    def test_upgrades_useful_equipped_ring_not_only_staff_and_armor(self):
        s = self.setup_state(3)
        ring = {"name": "ring of haste", "identified": True, "equipped": True, "upgradable": True}
        s["inventory"].append(ring)
        self.assertIs(ring, choose_upgrade(s)[0])

    def test_energy_ring_investment_supports_spare_wand_arsenal(self):
        s = self.setup_state(3)
        ring = {"name": "ring of energy", "identified": True, "equipped": True}
        s["inventory"] += [ring, {"name": "wand of frost", "identified": True, "description": "Deals 2-8 damage."}]
        self.assertIs(ring, choose_upgrade(s)[0])

    def test_strong_scaling_spare_wand_is_an_upgrade_candidate(self):
        s = self.setup_state(3)
        s["inventory"][0]["description"] = "Each bolt deals 5-14 damage."
        wand = {"name": "wand of frost +1", "identified": True, "description": "Deals 3-13 damage."}
        s["inventory"].append(wand)
        self.assertIs(wand, choose_upgrade(s)[0])

    def test_non_upgradable_and_unknown_support_items_are_skipped(self):
        for fields in ({"identified": True, "upgradable": False}, {"identified": False, "upgradable": True}):
            s = self.setup_state(3)
            s["inventory"].append(dict(name="ring of haste", equipped=True, **fields))
            self.assertIsNone(choose_upgrade(s))

    def test_ring_upgrade_uses_normal_item_selection_not_staff_only(self):
        from tools.survival_bot import SurvivalPolicy
        s = self.setup_state(3)
        s["depth"] = 1
        s["inventory"][-2]["id"] = "scroll"
        ring = {"id": "ring", "name": "ring of haste", "identified": True, "equipped": True, "actions": []}
        s["inventory"].append(ring)
        for item in s["inventory"]:
            item.setdefault("actions", [])
        p = SurvivalPolicy()
        self.assertEqual("scroll", p.choose(s).action["id"])
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["Upgrade an item"], "buttons": [
            {"id": "staff", "label": "staff of magic missile +3"}, {"id": "ring-upgrade", "label": "ring of haste"}]}
        self.assertEqual("ring-upgrade", p.choose(s).action["id"])
