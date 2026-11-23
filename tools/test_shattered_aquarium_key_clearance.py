"""Run 205: stationary missile preparation for a key beside an aquarium.

Reduced public geometry from decisions 522--540: a 3x3 water island,
visible ordinary piranha, a key on its dry melee bank, and a charged staff
on the safe exterior. This is a fixture, not replayed policy memory.
"""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.priority_resources import choose


class AquariumKeyClearanceTests(unittest.TestCase):
    def fixture(self):
        s, p = arena()
        s["hero"].update(cell=21, hp=30, max_hp=30, buffs=[])
        water = {y*9+x for y in (4, 5, 6) for x in (3, 4, 5)}
        for t in s["map"]["cells"]:
            if t["cell"] in water:
                t["terrain"] = 29
            elif t["cell"] == 21:
                t["terrain"] = 2  # Recorded safe exterior at decision 523 was grass.
        s["objects"] = [
            {"cell": 48, "name": "giant piranha"},
            {"cell": 31, "name": "iron key",
             "top_item": {"name": "iron key", "identified": True, "quantity": 1}},
        ]
        s["inventory"] = [{"id": "staff", "name": "staff of magic missile +2",
                           "identified": True, "curse_known": True,
                           "known_cursed": False, "status": "2/6",
                           "actions": ["ZAP"], "quantity": 1}]
        p.update(s)
        return s, p

    def test_safe_stationary_shot_prepares_key_before_lock_is_seen(self):
        s, p = self.fixture()
        self.assertEqual("aquarium", next(iter(p.piranha_habitats.values()))["profile"])
        self.assertTrue(p.shot_clear(s, 48))
        self.assertIn(31, p.room_blocked)
        original = copy.deepcopy(s)
        d = choose(p, s, [])
        self.assertIsNotNone(d, "Do not abandon a visible key when a safe stationary missile is available")
        self.assertEqual({"type": "item", "id": "staff", "action": "ZAP"}, d.action)
        self.assertEqual(48, p.target)
        self.assertEqual(original, s)
        self.assertIn(31, p.loot)
        self.assertIn(31, p.room_blocked)  # A proposed shot is not a kill or collection.
        self.assertFalse(p.loot_collection_receipts)

    def test_no_movement_recharge_or_unsafe_shot_fallback(self):
        for case in ("empty", "unknown-charge", "cursed", "other-wand", "near",
                     "invisible", "hurt", "warning", "threat", "fish-hidden",
                     "phantom", "unknown-edge", "obstructed", "optional-loot", "champions"):
            with self.subTest(case=case):
                s, p = self.fixture()
                staff = s["inventory"][0]
                if case == "empty": staff["status"] = "0/6"
                if case == "unknown-charge": staff["status"] = "?/6"
                if case == "cursed": staff["known_cursed"] = True
                if case == "other-wand": staff["name"] = "wand of lightning"
                if case == "near": s["hero"]["cell"] = 30
                if case == "invisible": s["hero"]["buffs"] = [{"name": "invisible"}]
                if case == "hurt": s["hero"]["hp"] = 10
                if case == "warning": s["danger_cells"] = [21]
                if case == "threat": p.recent_threats[12] = {"name": "gnoll scout", "cell": 12}
                if case == "fish-hidden": s["objects"] = s["objects"][1:]
                if case == "phantom": s["objects"][0]["name"] = "phantom piranha"
                if case == "unknown-edge": p.tiles[39]["observed"] = False
                if case == "obstructed": s["objects"].append({"name": "sad ghost", "cell": 30});p.neutral_actor_cells.add(30)
                if case == "optional-loot": p.loot[31]["top_item"]["name"] = "gold"
                if case == "champions":
                    from tools.challenge_rules import ChallengeRules
                    p.rules = ChallengeRules(hostile_champions=True)
                self.assertIsNone(choose(p, s, []))

    def test_current_enemy_preempts_optional_stationary_clearance(self):
        s, p = self.fixture()
        self.assertIsNone(choose(p, s, [{"name": "marsupial rat", "cell": 12}]))


if __name__ == "__main__":
    unittest.main()
