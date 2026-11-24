"""D3308 public recipe preview reduction; not reconstructed runtime memory."""
import unittest

from tools.alchemy_tactics import Brew, alchemy_menu, inventory_baseline
from tools.test_challenge_rules import verified


class MageroyalCraftPreviewTests(unittest.TestCase):
    def fixture(self, ingredients=("blandfruit", "seed of mageroyal")):
        p = verified()
        p.alchemy_plan = dict(
            brew=Brew(ingredients, "dreamfruit", "known fruit recipe"),
            stage="slot", index=2, steps=6,
            inventory_before={"blandfruit": 1, "seed of mageroyal": 1,
                              "dreamfruit": 0, "magefruit": 0})
        s = dict(scene="AlchemyScene", status="menu", modal=False, ui=dict(
            energy_text="Energy: 5", buttons=[
                dict(id="button-0", label="Back"),
                dict(id="button-1", label="blandfruit"),
                dict(id="button-2", label="seed of mageroyal"),
                dict(id="button-6", label="Craft: magefruit")]))
        return p, s

    def test_recorded_preview_crafts_actual_named_output_without_credit(self):
        p, s = self.fixture()
        d = alchemy_menu(p, s)
        self.assertEqual({"type": "button", "id": "button-6"}, d.action)
        self.assertEqual("magefruit", p.alchemy_plan["crafted_output"])
        self.assertEqual(0, p.alchemy_plan["before_counts"]["magefruit"])
        self.assertNotIn("alchemy_receipt", p.planner.report)

    def test_other_ingredients_do_not_authorize_alias(self):
        p, s = self.fixture(("blandfruit", "seed of fadeleaf"))
        self.assertNotEqual("button-6", alchemy_menu(p, s).action.get("id"))

    def test_unoffered_output_is_not_invented(self):
        p, s = self.fixture()
        s["ui"]["buttons"][-1]["label"] = "Craft: firefruit"
        self.assertNotEqual("button-6", alchemy_menu(p, s).action.get("id"))

    def test_baseline_counts_actual_output_before_inventory_omitting_menu(self):
        p, _ = self.fixture()
        before = inventory_baseline(dict(inventory=[
            dict(name="magefruit", quantity=2),
            dict(name="blandfruit", quantity=1),
            dict(name="seed of mageroyal", quantity=1)]),
            p.alchemy_plan["brew"])
        self.assertIn("magefruit", before)
        self.assertEqual(2, before["magefruit"])


if __name__ == "__main__":
    unittest.main()
