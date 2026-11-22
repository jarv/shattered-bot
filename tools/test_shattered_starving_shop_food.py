"""Reduced public shop inputs from run 000116 D2192 (line 6562).

Independent selector fixture, not recorded policy memory or a gameplay replay.
"""
import copy
import unittest

from tools.shop_tactics import choose_shop, confirm_purchase
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 6
    s["hero"].update(cell=153, hp=5, max_hp=50, gold=798,
                     strength=12, buffs=[{"name": "starving"}])
    s["map"] = dict(width=39, height=42, cells=[
        dict(cell=c, terrain=14, visible=True, observed=True, effects=[])
        for c in (112, 152, 153, 191, 230, 270)])
    s["inventory"] += [
        dict(id="bag", name="potion bandolier", actions=[]),
        dict(id="meat", name="mystery meat", actions=["EAT"])]
    s["objects"] = [
        dict(cell=c, name=f"{price}g: {name}", for_sale=True, price=price,
             top_item=dict(name=name, identified=True))
        for c, name, price in ((112, "small food ration", 100),
                               (270, "scroll of identify", 300))]
    p = verified()
    p.update(s)
    return s, p


class StarvingShopFoodTests(unittest.TestCase):
    def select(self, s, p):
        return choose_shop(p, s, p.paths(s))

    def test_starving_without_safe_food_buys_ration_before_scroll(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        self.assertFalse(p.food_items(s))  # Raw meat is not safe carried food.
        d = self.select(s, p)
        self.assertEqual({"type": "cell", "cell": 152}, d.action,
                         "Reach observed food before optional scroll shopping")
        self.assertEqual(original, s)
        self.assertIsNone(p.shop_plan)  # Travel is not a purchase receipt.
        self.assertFalse(p.purchases)

    def test_hungry_or_carried_food_retains_normal_priority(self):
        for carried in (False, True):
            s, p = fixture()
            if carried:
                s["inventory"].append(dict(id="food", name="ration of food",
                                            actions=["EAT"]))
            else:
                s["hero"]["buffs"] = [{"name": "hungry"}]
            self.assertEqual(191, self.select(s, p).action["cell"])

    def test_unaffordable_or_blocked_food_does_not_gain_access(self):
        for refusal in ("price", "blocked"):
            s, p = fixture()
            if refusal == "price":
                p.loot[112]["price"] = 900
            else:
                p.blocked.add(112)
            self.assertEqual(191, self.select(s, p).action["cell"])

    def test_food_purchase_still_requires_matching_title_and_price(self):
        s, p = fixture()
        s["hero"]["cell"] = 152
        p.update(s)
        self.select(s, p)
        self.assertIsNotNone(p.shop_plan, "Admit the adjacent ration purchase")
        self.assertEqual(112, p.shop_plan["cell"])
        s["ui"] = dict(texts=["small food ration"],
                       buttons=[dict(id="buy", label="Buy for 100g")])
        self.assertEqual("buy", confirm_purchase(p, s).action["id"])
        self.select(s, p)
        s["ui"]["texts"] = ["scroll of identify"]
        self.assertEqual("back", confirm_purchase(p, s).action["type"])


if __name__ == "__main__":
    unittest.main()
