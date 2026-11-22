"""Shelf hypotheses must not deadlock mandatory discovery or certify hidden loot."""
import copy
import unittest

from tools.test_shattered_strength_before_descent import ready
from tools.descent_potions import begin, observe, advance
from tools.room_supplies import requirements, discovery_requirements, allowed
from tools.policy_decision import PlannerStuck


def shelf_state(*, bag=False, backs="unknown"):
    s, p = ready(bag=bag)
    for tile in s["map"]["cells"]:
        if 23 <= tile["cell"] <= 31:
            tile["terrain"] = 27
        if 12 <= tile["cell"] <= 20 and backs == "wall":
            tile["terrain"] = 4
    if backs == "unknown":
        s["map"]["cells"] = [t for t in s["map"]["cells"] if not 12 <= t["cell"] <= 20]
        for c in range(12, 21):
            p.tiles.pop(c, None)
    p.update(s)
    return s, p


class BookshelfDiscoveryTests(unittest.TestCase):
    def test_synthetic_strength_receipt_finishes_discovery_not_shelf_collection(self):
        s, p = shelf_state()
        action = begin(p, s)
        self.assertIsNone(observe(p, s, action, copy.deepcopy(s)))
        self.assertFalse(p.strength_identified)
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i["id"] != action.action["id"]]
        after["hero"]["strength"] += 1
        receipt = observe(p, s, action, after)
        self.assertTrue(receipt["strength_identified"])
        self.assertFalse(receipt["collection_credited"])
        self.assertIsNone(advance(p, after))
        self.assertIsNone(p.descent_potion_plan)
        self.assertFalse(p.descent_counts_as_clear())

    def test_optional_shelves_allow_safe_discovery_without_claiming_clearance(self):
        for backs in ("unknown", "wall"):
            for bag in (False, True):
                with self.subTest(backs=backs, bag=bag):
                    s, p = shelf_state(bag=bag, backs=backs)
                    self.assertTrue(any(d.kind == "flame" for d in requirements(p, s)))
                    action = begin(p, s)
                    self.assertEqual("DRINK", action.action.get("action"))
                    self.assertFalse(p.strength_identified)
                    self.assertTrue(p.deferred_obligations)
                    self.assertFalse(p.descent_counts_as_clear())
                    self.assertFalse(p.completed_room_rewards)

    def test_farther_barricade_is_not_hidden_by_nearest_shelf_representative(self):
        s, p = shelf_state()
        p.tiles[12] = dict(cell=12, terrain=13, visible=False, observed=True)
        self.assertTrue(any(d.kind == "flame" for d in discovery_requirements(p, s)))
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertFalse(p.deferred_obligations)

    def test_observed_shelf_separated_reward_still_reserves_unknown_supply(self):
        s, p = shelf_state(backs="floor")
        p.loot[15] = dict(cell=15, name="Chest")
        self.assertNotIn(15, p.paths(s))
        self.assertTrue(any(d.kind == "flame" for d in discovery_requirements(p, s)))
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertFalse(p.completed_room_rewards)

    def test_known_flame_remains_reserved_for_optional_shelves(self):
        s, p = shelf_state()
        item = dict(id="flame", name="potion of liquid flame", quantity=1,
                    identified=True, actions=["DRINK", "THROW"])
        s["inventory"].append(item)
        p.last_state = s
        discovery_requirements(p, s)
        self.assertFalse(allowed(p, item, "DRINK"))
        self.assertFalse(allowed(p, item, "THROW"))

    def test_shelf_exemption_does_not_admit_an_unsafe_drink(self):
        s, p = shelf_state()
        s["hero"]["hp"] = 5
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertFalse(p.strength_identified)


if __name__ == "__main__":
    unittest.main()
