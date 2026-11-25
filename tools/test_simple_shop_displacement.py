import unittest
from unittest.mock import patch

from tools.test_bot_profiles import ready
from tools.shop_tactics import visit_entrance_shop, ShopVisitBlocked
from tools.policy_geometry import neighbors
from tools.bot_profiles import resolve


class SimpleShopDisplacementTests(unittest.TestCase):
    def test_disconnected_entrance_can_be_reexplored_without_claiming_shop_visit(self):
        s, p = ready()
        s["depth"] = 6
        p.update(s)
        p.entrance_cell = 8
        with patch("tools.shop_tactics._visit_entrance_shop", side_effect=ShopVisitBlocked("no entrance branches")):
            self.assertIsNone(visit_entrance_shop(p, s, {24: None}, neighbors))
        self.assertNotIn(6, p.shop_visited_floors)
        self.assertTrue(p.deferred_obligations)

    def test_connected_or_visible_shop_and_legacy_errors_are_not_swallowed(self):
        for kind in ("connected", "visible", "legacy"):
            s, p = ready()
            s["depth"] = 6
            p.update(s)
            p.entrance_cell = 8
            previous = {24: None}
            if kind == "connected":previous[8] = 24
            elif kind == "visible":s["objects"] = [{"name": "shopkeeper", "cell": 25}]
            else:p.profile = resolve("legacy-bot")
            with patch("tools.shop_tactics._visit_entrance_shop", side_effect=ShopVisitBlocked("no entrance branches")):
                with self.assertRaises(ShopVisitBlocked, msg=kind):
                    visit_entrance_shop(p, s, previous, neighbors)
