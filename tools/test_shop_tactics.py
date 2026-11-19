import unittest

from tools.survival_bot import SurvivalPolicy, neighbors
from tools.shop_tactics import choose_shop, priority, visit_entrance_shop
from tools.test_survival_bot import state, explored_policy, fully_known


class ShopTests(unittest.TestCase):
    def test_checked_stair_annex_door_does_not_end_shop_search(self):
        s = state()
        s["depth"] = 6
        s["hero"]["cell"] = 10
        s["map"]["cells"] = [{"cell": c, "terrain": {24: 37, 17: 5, 9: 1, 10: 1, 11: 1}.get(c, 4),
                               "visible": True} for c in range(7, 49)]
        p = SurvivalPolicy(goal="survival")
        p.update(s)
        p.entrance_cell = 24
        p.entrance_doors_checked.add(17)
        p.exhausted.add(10)
        d = visit_entrance_shop(p, s, p.paths(s), neighbors)
        self.assertEqual("shop: reveal entrance chamber doors", d.reason)
        self.assertIn(d.action["cell"], {9, 11})
        self.assertNotIn(6, p.shop_visited_floors)

    def shop(self):
        s = state()
        s["depth"] = 6
        s["hero"]["gold"] = 1000
        s["objects"] = [self.stock(23, "potion of healing", 100),
                        self.stock(25, "scroll of identify", 200),
                        self.stock(31, "scroll holder", 500)]
        return s

    @staticmethod
    def stock(cell, name, price):
        return {"cell": cell, "name": name, "top_item": {"name": name}, "for_sale": True, "price": price}

    def select(self, s):
        p = SurvivalPolicy(goal="survival")
        p.update(s)
        return p, choose_shop(p, s, p.paths(s))

    def test_bag_before_scroll_before_healing(self):
        s = self.shop()
        p, d = self.select(s)
        self.assertEqual(31, d.action["cell"])
        s["inventory"].append({"id": "bag", "name": "scroll holder", "actions": []})
        self.assertEqual(25, self.select(s)[1].action["cell"])
        s["objects"].pop(1)
        self.assertEqual(23, self.select(s)[1].action["cell"])

    def test_all_capacity_bags_are_priorities(self):
        for name in ("scroll holder", "potion bandolier", "velvet pouch", "magical holster"):
            self.assertEqual(0, priority(name, [])[0])
            self.assertIsNone(priority(name, [{"name": name}]))

    def test_unknown_scrolls_are_buyable_but_unknown_potions_are_not(self):
        self.assertEqual(1, priority("scroll of SOWILO", [])[0])
        self.assertIsNone(priority("azure potion", []))
        self.assertIsNone(priority("potion of liquid flame", []))

    def test_unaffordable_stock_is_skipped(self):
        s = self.shop()
        s["hero"]["gold"] = 150
        self.assertEqual(23, self.select(s)[1].action["cell"])
        s["hero"]["gold"] = 0
        self.assertIsNone(self.select(s)[1])

    def test_menu_buys_only_intended_item_at_expected_price(self):
        s = self.shop()
        s["hero"]["cell"] = 31
        p, d = self.select(s)
        self.assertIsNotNone(p.shop_plan)
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["Scroll Holder", "Some description"],
                   "buttons": [{"id": "buy", "label": "Buy for 500g"}, {"id": "steal", "label": "Steal"}]}
        d = p.choose(s)
        self.assertEqual({"type": "button", "id": "buy"}, d.action)
        self.assertEqual("scroll holder", p.purchases[0]["name"])
        self.assertIsNone(p.shop_plan)

    def test_changed_price_wrong_title_and_insufficient_gold_cancel(self):
        for scenario in ("price", "title", "gold"):
            s = self.shop()
            s["hero"]["cell"] = 31
            p, _ = self.select(s)
            s.update(modal=True, status="menu")
            s["ui"] = {"texts": ["Scroll Holder"], "buttons": [{"id": "buy", "label": "Buy for 500g"}]}
            if scenario == "price": s["ui"]["buttons"][0]["label"] = "Buy for 600g"
            if scenario == "title": s["ui"]["texts"] = ["potion of liquid flame"]
            if scenario == "gold": s["hero"]["gold"] = 400
            self.assertEqual({"type": "back"}, p.choose(s).action)
            self.assertEqual([], p.purchases)

    def test_navigation_does_not_authorize_purchase_until_at_stock(self):
        s = self.shop()
        s["hero"]["cell"] = 17
        p, _ = self.select(s)
        self.assertIsNone(p.shop_plan)

    def test_adjacent_stock_can_open_purchase_window_on_same_click(self):
        s = self.shop()
        p, _ = self.select(s)
        self.assertEqual("scroll holder", p.shop_plan["name"])

    def test_shop_displays_are_destinations_not_transit_tiles(self):
        s = self.shop()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (24, 25, 26) else 4, "visible": True}
                             for c in range(49)]
        s["objects"] = [self.stock(25, "ankh", 500)]
        p = SurvivalPolicy()
        p.update(s)
        previous = p.paths(s)
        self.assertIn(25, previous)
        self.assertNotIn(26, previous)

    def test_unplanned_trade_window_is_cancelled_not_purchased(self):
        s = self.shop()
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["500g: Ankh"], "buttons": [{"id": "buy", "label": "Buy for 500g"}]}
        self.assertEqual({"type": "back"}, SurvivalPolicy(goal="survival").choose(s).action)

    def test_survival_continues_after_goo_and_past_floor_five(self):
        for depth in (5, 6):
            s = fully_known(state())
            s["depth"] = depth
            next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
            p = explored_policy(s)
            p.goal = "survival"
            p.shop_visited_floors.add(depth)  # This fixture tests descent after a completed shop visit.
            p.boss_seen = True
            d = p.choose(s)
            self.assertTrue(d.reason.startswith("stairs:"))
            if depth == 5: self.assertIn("goo", p.defeated_bosses)

    def test_nonpriority_stock_is_not_collected_as_free_loot(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        s["objects"] = [self.stock(23, "potion of liquid flame", 100)]
        s["hero"]["gold"] = 500
        p = explored_policy(s)
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))

    def test_post_goo_developer_message_is_closed_without_opening_browser(self):
        s = state()
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["A Message From The Developer"], "buttons": [
            {"id": "external", "label": "Go to Patreon Page"}, {"id": "close", "label": "Close"}]}
        self.assertEqual({"type": "button", "id": "close"}, SurvivalPolicy().choose(s).action)
