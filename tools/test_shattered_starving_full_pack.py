"""Reduced public D3180-3183 facts from 000217, not recorded policy memory.

Independent selector/receipt fixtures only; no gameplay or changed-action replay.
"""
import copy
import unittest

from tools.exploration_budget import starving_food
from tools.inventory_tactics import observe_accepted, signature
from tools.loot_completion import required_loot
from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision, Intent
from tools.test_survival_bot import state


def encounter(bank=False, receipt=True):
    s = state()
    s["depth"] = 8
    s["hero"].update(cell=1412 if bank else 1411, hp=34, max_hp=65,
                     strength=13, buffs=[{"name": "starving"}])
    s["map"] = dict(width=40, height=54, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
        for c in (1411, 1412, 1451, 1452)])
    # Retain only the protected staff, unsafe raw food, and the first ranked
    # backpack replacement from the recording. Fullness is evidenced by the
    # explicit receipt, never inferred from this reduced inventory's length.
    s["inventory"] += [
        dict(id="item-12", name="bomb", quantity=1, identified=True,
             actions=["DROP", "THROW", "LIGHTTHROW"]),
        dict(id="item-14", name="mystery meat x2", quantity=2, actions=["EAT"])]
    s["objects"] = [dict(cell=1411, name="pasty", top_item=dict(
        name="pasty", quantity=1, identified=True,
        description="An authentic Cornish pasty with a traditional filling of beef and potato. Delicious!"))]
    p = MagePolicy()
    p.update(s)
    if receipt:
        before = copy.deepcopy(s)
        before["hero"]["cell"] = 1411
        after = copy.deepcopy(before)
        after["ui"]["texts"].append("You can't carry: pasty.")
        observe_accepted(p, before, Decision(
            {"type": "cell", "cell": 1411}, "pickup", Intent.LOOT), after)
    return s, p


class StarvingFullPackTests(unittest.TestCase):
    def test_preparation_funds_inventory_relief_instead_of_refused_food_click(self):
        s, p = encounter()
        before = copy.deepcopy(s)
        self.assertEqual(signature(s), p.inventory_pressure["signature"])
        d = p.preparation(s, [])
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertEqual({"type": "cell", "cell": 1412}, d.action)
        self.assertEqual(before, s)
        self.assertIn(1411, required_loot(p))
        self.assertNotIn(1411, p.loot_collection_receipts)
        self.assertIsNone(p.inventory_disposal_pending)

    def test_independent_bank_fixture_uses_existing_ranked_drop(self):
        s, p = encounter(bank=True)
        d = starving_food(p, s, [])
        self.assertEqual({"type": "item", "id": "item-12", "action": "DROP"}, d.action)
        self.assertIsNotNone(p.inventory_disposal_pending)
        self.assertIsNotNone(p.inventory_pressure)  # Selection is not a receipt.
        self.assertNotIn(1411, p.loot_collection_receipts)

    def test_no_admitted_replacement_declines_without_retrying_pickup(self):
        s, p = encounter()
        s["inventory"] = [i for i in s["inventory"] if i["name"] != "bomb"]
        p.inventory_pressure["signature"] = signature(s)
        self.assertIsNone(starving_food(p, s, []))
        self.assertIn(1411, required_loot(p))

    def test_absent_stale_or_different_bag_pressure_does_not_block_food(self):
        for mode in ("absent", "stale", "different-bag"):
            with self.subTest(mode=mode):
                s, p = encounter(receipt=mode != "absent")
                if mode == "stale":
                    s["inventory"].append(dict(id="new", name="waterskin", actions=[]))
                if mode == "different-bag":
                    s["inventory"].append(dict(id="bag", name="potion bandolier", actions=[]))
                    p.inventory_pressure.update(signature=signature(s), item=dict(name="azure potion"))
                self.assertEqual({"type": "cell", "cell": 1411}, starving_food(p, s, []).action)
                self.assertIsNone(p.inventory_disposal_pending)

    def test_safety_and_carried_food_still_precede_cleanup(self):
        for mode in ("enemy", "danger", "poison", "carried"):
            with self.subTest(mode=mode):
                s, p = encounter()
                enemies = [{"name": "guard", "cell": 1452}] if mode == "enemy" else []
                if mode == "danger":
                    s["danger_cells"] = [1452]
                if mode == "poison":
                    s["hero"]["buffs"].append({"name": "poisoned"})
                if mode == "carried":
                    s["inventory"].append(dict(id="food", name="ration of food", actions=["EAT"]))
                d = starving_food(p, s, enemies)
                if mode == "carried":
                    self.assertEqual("EAT", d.action["action"])
                else:
                    self.assertIsNone(d)
                self.assertIsNone(p.inventory_disposal_pending)


if __name__ == "__main__":
    unittest.main()
