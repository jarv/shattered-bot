"""Reduced public 000197 D1748–1751 sale transaction, not a game replay."""
import copy
import unittest

from tools import inventory_tactics as inventory
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=6, branch=0)
    s["hero"].update(cell=144, hp=45, max_hp=45, gold=827, strength=12)
    s["map"] = dict(width=34, height=44, cells=[
        dict(cell=c, terrain=14, visible=True, observed=True, effects=[])
        for c in (144, 177)])
    s["objects"] = [dict(name="shopkeeper", cell=177)]
    s["inventory"] = [
        dict(id="item-14", name="velvet pouch", identified=True,
             actions=["DROP", "THROW"]),
        dict(id="item-20", name="blob of goo x3", quantity=3, identified=True,
             equipped=False, actions=["DROP", "THROW"])]
    p = verified()
    p.update(s)
    return p, s


def menu(s, labels, texts=("Sell an item",)):
    s.update(status="menu", modal=True)
    s["ui"] = dict(texts=list(texts), buttons=[
        dict(id=bid, label=label) for bid, label in labels])


class SalePouchNavigationTests(unittest.TestCase):
    def start(self):
        p, s = fixture()
        self.assertEqual({"type": "cell", "cell": 177},
                         inventory.choose(p, s, []).action)
        self.assertEqual("blob of goo", p.sell_plan["name"])
        menu(s, [("button-0", "Sell an item")], ("Shopkeeper",))
        self.assertEqual({"type": "button", "id": "button-0"}, p.menu(s).action)
        return p, s

    def test_recorded_backpack_then_pouch_is_not_cancelled(self):
        p, s = self.start()
        tabs = [("button-12", "Backpack"), ("button-13", "Velvet Pouch")]
        menu(s, [("button-3", "dirk")] + tabs)
        self.assertEqual({"type": "button", "id": "button-12"}, p.menu(s).action)
        # D1751: the recorded unchanged backpack still exposes the pouch tab.
        self.assertEqual({"type": "button", "id": "button-13"}, p.menu(s).action)
        self.assertEqual(["backpack", "velvet pouch"], p.sell_plan["bags"])
        self.assertEqual("select", p.sell_plan["stage"])
        self.assertFalse(p.inventory_events)
        self.assertEqual(827, s["hero"]["gold"])
        self.assertEqual(3, inventory.count(s, "blob of goo"))

    def test_isolated_pouch_selection_still_requires_quote_and_receipt(self):
        p, s = self.start()
        # Synthetic alternative UI; not an observation from after changed D1751.
        menu(s, [("pouch", "Velvet Pouch")])
        self.assertEqual({"type": "button", "id": "pouch"}, p.menu(s).action)
        menu(s, [("goo", "blob of goo x3"), ("seed", "seed of earthroot")])
        self.assertEqual("goo", p.menu(s).action["id"])
        self.assertFalse(p.inventory_events)
        menu(s, [("sell", "Sell 1 for 30g")], ("Blob of goo",))
        confirmation = p.menu(s)
        self.assertEqual({"type": "button", "id": "sell"}, confirmation.action)
        self.assertFalse(p.inventory_events)
        after = copy.deepcopy(s)
        after["inventory"][-1].update(name="blob of goo x2", quantity=2)
        after["hero"]["gold"] += 30
        receipts = inventory.observe_accepted(p, s, confirmation, after)
        self.assertEqual("sold", receipts[0]["kind"])
        self.assertEqual("close", p.sell_plan["stage"])

    def test_bags_are_not_revisited_and_unknown_controls_are_not_guessed(self):
        p, s = self.start()
        p.sell_plan["bags"] = ["backpack", "velvet pouch"]
        menu(s, [("pack", "Backpack"), ("pouch", "Velvet Pouch"),
                 ("unknown", "Open secret storage")])
        self.assertEqual({"type": "back"}, p.menu(s).action)
        self.assertFalse(p.inventory_events)

    def test_changed_candidate_is_not_recovered_by_browsing(self):
        p, s = self.start()
        s["inventory"][-1]["identified"] = False
        menu(s, [("pouch", "Velvet Pouch")])
        self.assertEqual({"type": "back"}, p.menu(s).action)
        self.assertFalse(p.inventory_events)


if __name__ == "__main__":
    unittest.main()
