"""Changed inventory permits planned reobservation, never a stale drink receipt."""
import copy
import unittest

from tools.test_shattered_descent_bank_revisit import fixture
from tools.descent_potions import begin, advance, remembered_preparation
from tools.policy_decision import PlannerStuck, Intent


def changed():
    s, p = fixture()
    s["inventory"].append(dict(id="new", name="golden potion", quantity=2,
                               identified=False, actions=["DROP", "THROW", "DRINK"]))
    return s, p


class InventoryAwareReturn(unittest.TestCase):
    def test_new_color_replans_storage_without_mutating_visibility_or_receipts(self):
        s, p = changed()
        tiles = copy.deepcopy(p.tiles)
        history = copy.deepcopy(p.descent_potion_bank_history)
        original = copy.deepcopy(s)
        action = begin(p, s)
        self.assertEqual(Intent.REPOSITION, action.intent)
        self.assertEqual(dict(type="cell", cell=1170), action.action)
        self.assertEqual(tiles, p.tiles)
        self.assertEqual(history, p.descent_potion_bank_history)
        self.assertEqual(original, s)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertEqual("return-to-preparation-area",
                         p.objective_results["potion-discovery"]["prerequisites"][0]["objective"])

    def test_added_inventory_requires_current_drop_capability_and_no_owned_transaction(self):
        for kind in ("no-drop", "stash", "journey", "trap-return", "drop-plan"):
            s, p = changed()
            if kind == "no-drop":
                for i in s["inventory"]: i["actions"].remove("DROP")
            elif kind == "stash": p.potion_stash = {"phase": "retrieve"}
            elif kind == "journey": p.room_journey = object()
            elif kind == "trap-return": p.trap_payload_return = {"cell": 1135}
            else: p.drop_plan = {"cell": 1135}
            self.assertFalse(remembered_preparation(p, s, 1135), kind)

    def test_changed_inventory_still_requires_observed_storage_geometry(self):
        s, p = changed()
        for t in p.tiles.values():
            t["observed"] = False
        self.assertFalse(remembered_preparation(p, s, 1135))

    def test_stale_arrival_cannot_drink_and_fresh_arrival_starts_protection(self):
        s, p = changed()
        s["hero"]["cell"] = 1135
        p.update(s)
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        # Independent, synthetic fresh arrival with the same carried colors.
        s, p = changed()
        s["hero"]["cell"] = 1135
        for t in s["map"]["cells"]:
            t["visible"] = True
        p.update(s)
        action = begin(p, s)
        self.assertNotEqual("DRINK", action.action.get("action"))
        s["hero"]["cell"] = action.action["cell"]
        p.update(s)
        action = advance(p, s)
        self.assertNotEqual("DRINK", action.action.get("action"))
        self.assertIsNotNone(p.potion_stash)
        self.assertFalse(p.strength_identified)

    def test_new_route_hazard_and_spent_transit_budget_still_exhaust(self):
        for kind in ("hazard", "budget"):
            s, p = changed()
            if kind == "hazard":
                p.tiles[1170]["trap"] = "poison"
            else:
                p.descent_potion_plan = dict(depth=1, steps=0, waits=0, candidate=None,
                                             bank=None, pending=False, return_steps=64)
            with self.assertRaises(PlannerStuck):
                begin(p, s)
