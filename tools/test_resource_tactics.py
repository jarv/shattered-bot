import unittest

from tools.survival_bot import Finished, SurvivalPolicy, distance, neighbors
from tools.resource_tactics import choose_meat, choose_well, choose_enchantment, clear_blocking_plant, recheck_hazards
from tools.test_survival_bot import state, fully_known, explored_policy
from tools.test_combat_items import gear


HEALTH = ["Power of health radiates from the water of this well. Drinking from this well will heal your wounds."]


class ResourceTests(unittest.TestCase):
    def test_known_mirror_image_is_used_before_critical_health_summoner_trade(self):
        s, p = state(), SurvivalPolicy()
        s["hero"].update(hp=4, max_hp=55)
        s["objects"] = [{"cell": 26, "name": "necromancer"}]
        s["inventory"].append({"id": "mirror", "name": "scroll of mirror image", "actions": ["READ"]})
        self.assertEqual("mirror", p.choose(s).action["id"])
        s["objects"].append({"cell": 23, "name": "mirror image"})
        self.assertNotEqual("mirror", p.choose(s).action.get("id"))

    def test_firebloom_grills_meat_without_standing_in_fire(self):
        s = fully_known(state())
        s["inventory"] += [{"id": "meat", "name": "mystery meat", "actions": ["EAT", "THROW"]},
                            {"id": "fire", "name": "seed of firebloom", "actions": ["THROW", "PLANT"]}]
        p = SurvivalPolicy()
        p.update(s)
        self.assertEqual("fire", choose_meat(p, s, [], distance, neighbors).action["id"])
        cell = p.target
        self.assertEqual(2, distance(s["hero"]["cell"], cell, 7))
        next(t for t in s["map"]["cells"] if t["cell"] == cell)["plant"] = "firebloom"
        p.update(s)
        d = choose_meat(p, s, [], distance, neighbors)
        self.assertEqual("meat", d.action["id"])
        self.assertEqual("food: grill raw meat with prepared firebloom", d.reason)

    def test_does_not_light_fire_in_flammable_surroundings_for_cooking(self):
        s = fully_known(state())
        for tile in s["map"]["cells"]:
            if tile["terrain"] == 1:
                tile["terrain"] = 2
        s["inventory"] += [{"id": "meat", "name": "mystery meat", "actions": ["EAT", "THROW"]},
                            {"id": "fire", "name": "seed of firebloom", "actions": ["THROW", "PLANT"]}]
        p = SurvivalPolicy()
        p.update(s)
        self.assertIsNone(choose_meat(p, s, [], distance, neighbors))

    def test_exhausted_routes_can_use_one_known_teleport_not_repeat_forever(self):
        s = fully_known(state())
        s["inventory"].append({"id": "teleport", "name": "scroll of teleportation", "actions": ["READ"]})
        p = explored_policy(s)
        self.assertEqual("teleport", p.choose(s).action["id"])
        with self.assertRaises(Finished):
            p.choose(s)

    def test_stale_gas_is_reobserved_not_assumed_clear_or_permanent(self):
        s = fully_known(state())
        s["hero"]["cell"] = 22
        for tile in s["map"]["cells"]:
            tile["terrain"] = {22: 1, 23: 1, 24: 1, 25: 1, 26: 8}.get(tile["cell"], 4)
            if tile["cell"] == 25:
                tile.update(visible=False, effects=["A greenish cloud of toxic gas is swirling here."])
        p = SurvivalPolicy()
        p.update(s)
        d = recheck_hazards(p, s, p.paths(s), distance)
        self.assertEqual("explore: recheck remembered hazard from safe ground", d.reason)
        self.assertEqual(23, d.action["cell"])
        self.assertFalse(p.walkable(25))
        p.hazard_recheck_steps = 60
        self.assertIsNone(recheck_hazards(p, s, p.paths(s), distance))

    def test_clears_blocking_sorrowmoss_without_trampling_or_mutating_map(self):
        s = fully_known(state())
        for tile in s["map"]["cells"]:
            tile["terrain"] = {24: 1, 25: 1, 26: 8}.get(tile["cell"], 4)
            if tile["cell"] == 25:
                tile["plant"] = "sorrowmoss"
        s["inventory"].append({"id": "food", "name": "frozen carpaccio", "actions": ["EAT", "THROW"]})
        p = SurvivalPolicy()
        d = p.choose(s)
        self.assertEqual("THROW", d.action["action"])
        self.assertEqual("food", d.action["id"])
        self.assertEqual(25, p.target)
        self.assertFalse(p.walkable(25))
        self.assertNotIn(26, p.paths(s))

    def test_plant_clearance_does_not_treat_firebloom_as_harmless(self):
        s = fully_known(state())
        for tile in s["map"]["cells"]:
            tile["terrain"] = {24: 1, 25: 1, 26: 8}.get(tile["cell"], 4)
            if tile["cell"] == 25:
                tile["plant"] = "firebloom"
        s["inventory"].append({"id": "food", "name": "frozen carpaccio", "actions": ["EAT", "THROW"]})
        p = SurvivalPolicy()
        p.update(s)
        self.assertIsNone(clear_blocking_plant(p, s, p.paths(s), distance))

    def test_critical_adjacent_guard_uses_fear_even_during_discovery_cooldown(self):
        s, p = state(), SurvivalPolicy()
        s["hero"].update(hp=13, max_hp=65, buffs=[{"name": "crippled"}])
        s["objects"] = [{"cell": 25, "name": "prison guard"}]
        s["inventory"].append({"id": "fear", "name": "stone of fear", "actions": ["THROW"]})
        p.consumable_cooldown = 20
        self.assertEqual("fear", p.choose(s).action["id"])
        self.assertEqual(25, p.target)

    def test_raw_meat_is_never_food_but_cooked_meat_is(self):
        s = state()
        s["inventory"] = [{"id": n, "name": n, "actions": ["EAT", "THROW"]}
                          for n in ("mystery meat", "chargrilled meat", "frozen carpaccio", "blandfruit")]
        self.assertEqual(["chargrilled meat", "frozen carpaccio"], [i["name"] for i in SurvivalPolicy.food_items(s)])

    def test_prepares_icecap_then_throws_meat_not_hero_into_cold(self):
        s = fully_known(state())
        s["inventory"] += [{"id": "meat", "name": "mystery meat", "actions": ["EAT", "THROW"]},
                            {"id": "ice", "name": "seed of icecap", "actions": ["THROW", "PLANT"]}]
        p = SurvivalPolicy()
        p.update(s)
        d = choose_meat(p, s, [], distance, neighbors)
        self.assertEqual("ice", d.action["id"])
        cell = p.target
        self.assertEqual(2, distance(cell, s["hero"]["cell"], 7))
        next(t for t in s["map"]["cells"] if t["cell"] == cell)["plant"] = "Icecap"
        p.update(s)
        self.assertEqual("meat", choose_meat(p, s, [], distance, neighbors).action["id"])
        self.assertEqual(cell, p.target)

    def test_meat_preparation_does_not_run_during_combat(self):
        s = state()
        p = SurvivalPolicy()
        p.update(s)
        self.assertIsNone(choose_meat(p, s, [{"cell": 25, "name": "rat"}], distance, neighbors))

    def well(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 26).update(terrain=16, effects=HEALTH)
        return s

    def test_healing_well_is_not_classified_as_a_hazard(self):
        s, p = self.well(), SurvivalPolicy()
        p.update(s)
        self.assertNotIn(26, p.room_blocked)

    def test_preserves_well_when_healthy_but_uses_when_hurt(self):
        s, p = self.well(), SurvivalPolicy()
        p.update(s)
        self.assertIsNone(choose_well(p, s, [], distance, neighbors))
        s["hero"]["hp"] = 8
        self.assertTrue(choose_well(p, s, [], distance, neighbors).reason.startswith("well:"))

    def test_well_is_used_to_cleanse_equipped_curse_even_at_full_hp(self):
        s, p = self.well(), SurvivalPolicy()
        s["inventory"][0].update(equipped=True, known_cursed=True)
        p.update(s)
        self.assertIsNotNone(choose_well(p, s, [], distance, neighbors))

    def test_does_not_walk_past_enemy_to_reach_well(self):
        s, p = self.well(), SurvivalPolicy()
        s["hero"]["hp"] = 8
        s["objects"] = [{"cell": 25, "name": "prison guard"}]
        p.update(s)
        self.assertIsNone(choose_well(p, s, s["objects"], distance, neighbors))

    def test_burning_paths_to_nearby_safe_water(self):
        s = fully_known(state())
        s["hero"]["buffs"] = [{"name": "burning"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 29
        d = SurvivalPolicy().choose(s)
        self.assertEqual("survival: extinguish burning in nearby water", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_burning_on_fire_seeks_water_before_special_room_stop(self):
        s = fully_known(state())
        s["hero"].update(hp=7, buffs=[{"name": "burning"}])
        next(t for t in s["map"]["cells"] if t["cell"] == 24)["effects"] = ["A fire is raging here."]
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 29
        d = SurvivalPolicy().choose(s)
        self.assertEqual("survival: extinguish burning in nearby water", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_stylus_enchants_useful_armor_once_not_cloth_or_existing_glyph(self):
        s, p = state(), SurvivalPolicy()
        armor = gear("leather armor", "armor", high=4, strength=12, equipped=True, curse_known=True)
        s["inventory"] = [armor, {"id": "stylus", "name": "arcane stylus", "actions": ["INSCRIBE"]}]
        self.assertEqual("INSCRIBE", choose_enchantment(p, s).action["action"])
        s["ui"] = {"texts": ["Select armor to inscribe"], "buttons": [{"id": "armor", "label": "leather armor"}]}
        self.assertEqual("armor", p.menu(s).action["id"])
        armor["description"] += " It is inscribed with a glyph of swiftness."
        self.assertIsNone(choose_enchantment(p, s))

    def test_known_cursed_gear_is_not_enchanted(self):
        s = state()
        s["inventory"] = [gear("leather armor", "armor", strength=12, equipped=True, known_cursed=True),
                          {"id": "stylus", "name": "arcane stylus", "actions": ["INSCRIBE"]}]
        self.assertIsNone(choose_enchantment(SurvivalPolicy(), s))

    def test_enchantment_scroll_selects_weapon_then_visible_choice(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"] = [gear("staff", equipped=True, identified=True),
                          {"id": "scroll", "name": "scroll of enchantment", "actions": ["READ"]}]
        self.assertEqual("READ", choose_enchantment(p, s).action["action"])
        s["ui"] = {"texts": ["Enchant an item"], "buttons": [{"id": "staff", "label": "staff"}]}
        self.assertEqual("staff", p.menu(s).action["id"])
        s["ui"] = {"texts": ["Select an enchantment to apply to your weapon."], "buttons": [
            {"id": "fire", "label": "Blazing"}, {"id": "cold", "label": "Chilling"}, {"id": "cancel", "label": "Cancel"}]}
        self.assertEqual("cold", p.menu(s).action["id"])
        self.assertIsNone(p.menu_plan)
