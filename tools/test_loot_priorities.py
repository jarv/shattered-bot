import unittest

from tools.chest_tactics import eligible_chests
from tools.survival_bot import SurvivalPolicy
from tools.shop_tactics import visit_entrance_shop, priority
from tools.test_survival_bot import state, fully_known, explored_policy
from tools.test_combat_items import gear


class ChestTests(unittest.TestCase):
    def test_crystal_choice_prefers_wand_then_ring_and_never_artifact(self):
        loot = {23: {"name": "crystal chest", "description": "You can see _an artifact_ inside."},
                25: {"name": "crystal chest", "description": "You can see _a wand_ inside."},
                31: {"name": "crystal chest", "description": "You can see _a ring_ inside."}}
        self.assertEqual({25}, eligible_chests(loot, {"crystal": 1}))
        del loot[25]
        self.assertEqual({31}, eligible_chests(loot, {"crystal": 1}))
        del loot[31]
        self.assertEqual(set(), eligible_chests(loot, {"crystal": 1}))

    def test_unknown_crystal_contents_are_not_inferred(self):
        self.assertEqual(set(), eligible_chests({25: {"name": "crystal chest"}}, {"crystal": 1}))

    def test_locked_chest_needs_golden_not_iron_key(self):
        loot = {25: {"name": "locked chest"}}
        self.assertEqual(set(), eligible_chests(loot, {"iron": 1}))
        self.assertEqual({25}, eligible_chests(loot, {"golden": 1}))

    def test_uses_chest_key_before_hungry_descent(self):
        s = fully_known(state())
        s["hero"]["buffs"] = [{"name": "hungry"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 8
        s["keys"] = [{"name": "golden key", "quantity": 1, "depth": 1}]
        s["objects"] = [{"name": "locked chest", "cell": 25}]
        p = explored_policy(s)
        self.assertEqual("loot: spend matching key on useful chest", p.choose(s).reason)

    def test_crystal_wand_is_reachable_but_artifact_is_not(self):
        s, p = state(), SurvivalPolicy()
        s["keys"] = [{"name": "Crystal key", "quantity": 1, "depth": 1}]
        s["objects"] = [{"name": "crystal chest", "cell": 25, "description": "You can see a wand inside."},
                        {"name": "crystal chest", "cell": 23, "description": "You can see an artifact inside."}]
        p.update(s)
        self.assertTrue(p.walkable(25))
        self.assertFalse(p.walkable(23))
        self.assertEqual(25, p.choose(s).action["cell"])

    def test_unkeyed_chests_are_not_transit_tiles(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"name": "locked chest", "cell": 25}]
        p.update(s)
        self.assertFalse(p.walkable(25))


class EntranceShopTests(unittest.TestCase):
    def test_entrance_door_checked_before_hungry_descent(self):
        s = fully_known(state())
        s["depth"] = 6
        s["hero"]["buffs"] = [{"name": "hungry"}]
        s["map"]["cells"] = [{"cell": c, "terrain": {24: 7, 23: 1, 22: 8, 25: 5, 26: 1}.get(c, 4), "visible": True}
                             for c in range(49)]
        p = explored_policy(s)
        p.goal = "survival"
        d = p.choose(s)
        self.assertEqual("shop: check entrance door before descent", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_visiting_store_does_not_require_affordable_purchase(self):
        s, p = state(), SurvivalPolicy(goal="survival")
        s["depth"] = 6
        s["objects"] = [{"cell": 25, "name": "400g: potion bandolier", "for_sale": True,
                         "price": 400, "top_item": {"name": "potion bandolier"}}]
        s["hero"]["gold"] = 0
        p.update(s)
        from tools.survival_bot import neighbors
        self.assertIsNone(visit_entrance_shop(p, s, p.paths(s), neighbors))
        self.assertIn(6, p.shop_visited_floors)

    def test_other_floor_without_shop_is_not_forced_into_entrance_search(self):
        s, p = state(), SurvivalPolicy()
        p.update(s)
        from tools.survival_bot import neighbors
        self.assertIsNone(visit_entrance_shop(p, s, p.paths(s), neighbors))


class EquippedCurseTests(unittest.TestCase):
    def cursed_state(self):
        s = state()
        s["inventory"][0]["known_cursed"] = True
        s["inventory"] += [{"id": "cleanse", "name": "scroll of remove curse", "actions": ["READ"]},
                           {"id": "upgrade", "name": "scroll of upgrade", "actions": ["READ"]}]
        return s

    def test_cleanse_precedes_upgrades_discovery_and_equipment(self):
        s = self.cursed_state()
        self.assertEqual("cleanse", SurvivalPolicy().choose(s).action["id"])

    def test_cleanup_can_be_used_in_combat_without_attacking_cursed_weapon(self):
        s = self.cursed_state()
        s["objects"] = [{"name": "sewer crab", "cell": 25}]
        self.assertEqual("cleanse", SurvivalPolicy().choose(s).action["id"])

    def test_cleanse_selection_targets_cursed_equipped_item_before_spare(self):
        s, p = self.cursed_state(), SurvivalPolicy()
        s["inventory"].append(gear("cursed sword", known_cursed=True))
        p.choose(s)
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["Cleanse an item"], "buttons": [
            {"id": "spare", "label": "cursed sword"}, {"id": "equipped", "label": "staff of magic missile"}]}
        self.assertEqual("equipped", p.choose(s).action["id"])

    def test_shop_curse_removal_overrides_normal_bag_priority(self):
        s = self.cursed_state()
        self.assertLess(priority("scroll of remove curse", s["inventory"]), priority("scroll holder", s["inventory"]))
