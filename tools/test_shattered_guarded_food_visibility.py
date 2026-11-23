"""Reduced public-input fixture from run 000190 D2485-2486.

Cached food, sleeper and stock are explicit fixture bookkeeping, not recovered
runtime memory. No observations are fed after a changed selection.
"""
import copy
import unittest

from tools.priority_resources import choose, targets
from tools.shop_tactics import choose_shop
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 6
    s["hero"].update(cell=237, hp=47, max_hp=50, gold=218,
                     strength=12, buffs=[{"name": "hungry"}])
    # Recorded food approach and an observed route toward affordable shop food.
    floors = dict.fromkeys((78, 79, 110, 141, 172, 204, 237, 238,
                            239, 240, 241, 502), 1)
    floors.update({242: 5, 275: 29, 307: 29, 339: 29, 371: 29,
                   403: 29, 435: 2, 467: 2, 500: 5, 469: 2, 535: 5})
    floors.update(dict.fromkeys(range(561, 567), 14))
    s["map"] = dict(width=32, height=32, cells=[
        dict(cell=c, terrain=t, visible=c in {172, 204, 237, 238, 239, 240, 241},
             observed=True, effects=[]) for c, t in floors.items()])
    p = verified()
    p.update(s)
    p.shop_visited_floors.add(6)
    p.enemy_sightings[78] = dict(cell=78, name="swarm of flies",
                                sleeping=True, status_icons=[])
    p.loot[79] = dict(cell=79, name="ration of food",
                      top_item=dict(name="ration of food", identified=True))
    p.loot[561] = dict(cell=561, name="100g: small food ration",
                       top_item=dict(name="small food ration", identified=True),
                       for_sale=True, price=100)
    return s, p


class GuardedFoodVisibilityTests(unittest.TestCase):
    def test_hidden_guard_does_not_restart_food_approach_over_shopping(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertIn(79, p.paths(s))
        self.assertEqual(238, choose_shop(copy.deepcopy(p), s, p.paths(s)).action["cell"])
        d = p.choose(s)
        self.assertEqual("shop: buy priority supplies", d.reason)
        self.assertEqual(238, d.action["cell"])
        self.assertEqual(before, s)
        self.assertIn(79, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.purchases)
        self.assertFalse(p.cleared_floors)

    def test_visible_enemy_veto_and_hazard_gates_are_unchanged(self):
        s, p = fixture()
        self.assertIsNone(choose(p, s, [p.enemy_sightings[78]]))
        p.enemy_sightings.clear()
        p.tiles[110]["trap"] = "shocking trap"
        self.assertIsNone(choose(p, s, []))

    def test_unrelated_sleeper_does_not_suppress_food(self):
        s, p = fixture()
        p.enemy_sightings = {700: dict(cell=700, name="swarm of flies", sleeping=True)}
        self.assertEqual(204, choose(p, s, []).action["cell"])

    def test_required_upgrade_strength_and_key_are_not_optional_food(self):
        for name in ("scroll of upgrade", "potion of strength", "iron key"):
            s, p = fixture()
            p.loot[79].update(name=name, top_item=dict(name=name))
            if name == "iron key":
                p.tiles[800] = dict(cell=800, terrain=10, visible=False)
            self.assertEqual(204, choose(p, s, []).action["cell"])
            self.assertIn(79, targets(p))

    def test_fresh_empty_guard_cell_releases_food_priority(self):
        s, p = fixture()
        next(t for t in s["map"]["cells"] if t["cell"] == 78)["visible"] = True
        p.update(s)
        self.assertNotIn(78, p.enemy_sightings)
        self.assertEqual(204, choose(p, s, []).action["cell"])


if __name__ == "__main__":
    unittest.main()
