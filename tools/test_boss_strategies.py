import unittest
from unittest.mock import patch

from tools.boss_strategies import GooStrategy, create_strategies, strategy_for, goo_blast_reaches
from tools.survival_bot import SurvivalPolicy, distance, neighbors
from tools.test_survival_bot import state


class GooStrategyTests(unittest.TestCase):
    def test_landing_safety_checks_goo_following_into_vacated_hero_tile(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "Goo"}]
        p.update(s)
        strategy, goo = p.boss_strategies["goo"], s["objects"][0]
        with patch.object(strategy, "escape_distance", side_effect=[1, 99]) as escape:
            self.assertEqual(99, strategy.landing_escape_distance(p, s, [goo], goo, 23, distance, neighbors))
            future_call = escape.call_args_list[1]
            self.assertEqual(24, future_call.args[3]["cell"])
            self.assertEqual(24, future_call.args[2][0]["cell"])
        self.assertEqual(25, goo["cell"])  # Prediction never mutates the observation.

    def test_hard_corner_cover_blocks_charge_in_either_direction(self):
        self.assertTrue(goo_blast_reaches(24, 19, 7, {}))
        self.assertFalse(goo_blast_reaches(24, 19, 7, {18: {"terrain": 4}}))
        self.assertFalse(goo_blast_reaches(24, 19, 7, {25: {"terrain": 4}}))

    def test_soft_cover_does_not_protect_against_goo_charge(self):
        for terrain in (5, 6, 15, 30):
            self.assertTrue(goo_blast_reaches(24, 19, 7, {18: {"terrain": terrain}}))

    def test_unknown_cells_are_not_assumed_to_be_cover(self):
        self.assertTrue(goo_blast_reaches(24, 19, 7, {}))
        self.assertFalse(goo_blast_reaches(24, 21, 7, {}))  # Beyond charged reach.

    def test_precharge_position_does_not_rely_on_small_dead_end_refuge(self):
        s = state()
        s.update(depth=5, boss_health_text="53/100")
        s["hero"]["cell"] = 452
        s["map"].update(width=34, height=20)
        floors = {347, 381, 382, 416, 419, 420, 421, 422, 423, 424, 425, 450, 451,
                  452, 453, 454, 455, 456, 457, 458, 459, 487, 488, 489, 490,
                  521, 522, 523, 524, 525, 526, 527, 556, 558, 559, 560, 561,
                  593, 594, 595, 628, 629}
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in floors else 4, "visible": True}
                             for c in range(680)]
        s["objects"] = [{"cell": 487, "name": "Goo"}]
        p = SurvivalPolicy()
        p.update(s)
        b, g = p.boss_strategies["goo"], s["objects"][0]
        self.assertEqual(1, b.escape_distance(p, s, [g], g, 452, neighbors))
        self.assertGreater(b.escape_distance(p, s, [g], g, 452, neighbors, min_refuge=8), 2)
        d = p.choose(s)
        self.assertEqual("boss: goo leave corner before another charge", d.reason)
        self.assertIn(d.action["cell"], {419, 453})

    def encounter(self):
        s = state()
        s["depth"] = 5
        s["boss_health_text"] = "80/100"
        s["objects"] = [{"cell": 25, "name": "Goo"}]
        return s

    def test_registry_is_specific_to_boss_and_floor(self):
        s = state()
        strategies = create_strategies()
        self.assertIsNone(strategy_for(s, strategies))
        s["depth"] = 5
        self.assertIsInstance(strategy_for(s, strategies), GooStrategy)
        s["depth"] = 10
        self.assertIsNone(strategy_for(s, strategies))

    def test_future_boss_can_register_independently(self):
        class NextBoss:
            depth = 10
        s = state()
        s.update(depth=10, objects=[{"name": "next boss", "cell": 25}])
        strategy = NextBoss()
        self.assertIs(strategy, strategy_for(s, {"next boss": strategy}))

    def test_health_phase_uses_displayed_bar_only(self):
        strategy = GooStrategy()
        self.assertEqual(0.4, strategy.health_fraction({"boss_health_text": "40/100"}))
        self.assertIsNone(strategy.health_fraction({}))
        self.assertIsNone(strategy.health_fraction({"boss_health_text": "0/0"}))

    def test_enraged_goo_heals_earlier(self):
        s = self.encounter()
        s["hero"]["hp"] = 12
        s["boss_health_text"] = "40/100"
        s["inventory"].append({"id": "heal", "name": "potion of healing", "actions": ["DRINK"]})
        self.assertEqual("heal", SurvivalPolicy().choose(s).action["id"])
        s["boss_health_text"] = "80/100"
        self.assertEqual("boss: goo best estimated damage", SurvivalPolicy().choose(s).reason)

    def test_warning_precedes_healing_and_herbal_armor(self):
        s = self.encounter()
        s["hero"].update(hp=3, buffs=[{"name": "herbal armor"}])
        s["inventory"].append({"id": "heal", "name": "potion of healing", "actions": ["DRINK"]})
        s["danger_cells"] = [24, 25, 17, 18, 31, 32, 26, 19, 33]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("boss: goo evade charged attack", d.reason)
        self.assertNotIn(d.action["cell"], s["danger_cells"])

    def test_two_step_escape_when_all_first_steps_are_in_warning(self):
        s = self.encounter()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (22, 23, 24, 25) else 4,
                               "visible": True} for c in range(49)]
        s["danger_cells"] = [24, 25]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("boss: goo evade charged attack", d.reason)
        self.assertEqual(23, d.action["cell"])
        s["hero"]["cell"] = 23
        s["danger_cells"] = [23, 24, 25]
        d = SurvivalPolicy().choose(s)
        self.assertEqual(22, d.action["cell"])

    def test_does_not_attack_from_unsafe_water_when_goo_can_be_lured(self):
        s = self.encounter()
        s["map"]["cells"] = [{"cell": c, "terrain": 1, "visible": True} for c in range(49)]
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 29
        d = SurvivalPolicy().choose(s)
        self.assertEqual("boss: goo lure off healing water", d.reason)
        self.assertGreater(distance(d.action["cell"], 25, 7), 1)

    def test_luring_is_bounded(self):
        s, p = self.encounter(), SurvivalPolicy()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 29
        p.boss_strategies["goo"].lure_steps = 6
        self.assertEqual("boss: goo best estimated damage", p.choose(s).reason)

    def test_rinse_never_enters_charge_warning(self):
        s = self.encounter()
        s["hero"]["cell"] = 16
        s["hero"]["buffs"] = [{"name": "ooze"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 29
        s["danger_cells"] = [23]
        d = SurvivalPolicy().choose(s)
        self.assertNotEqual(23, d.action.get("cell"))

    def test_full_charge_without_immediate_escape_never_falls_through(self):
        from tools.survival_bot import Finished
        s = self.encounter()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (22, 23, 24, 25) else 4,
                               "visible": True} for c in range(49)]
        s["danger_cells"] = [23, 24, 25]
        with self.assertRaises(Finished) as error:
            SurvivalPolicy().choose(s)
        self.assertEqual("blocked", error.exception.outcome)
        self.assertIn("refusing generic movement", error.exception.reason)

    def test_known_escape_used_instead_of_walking_into_full_charge(self):
        s = self.encounter()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (24, 25) else 4,
                               "visible": True} for c in range(49)]
        s["danger_cells"] = [23, 24, 25]
        s["inventory"].append({"id": "escape", "name": "scroll of teleportation", "actions": ["READ"]})
        d = SurvivalPolicy().choose(s)
        self.assertEqual("escape", d.action["id"])

    def test_early_warning_plans_beyond_radius_two_not_just_small_warning(self):
        s = self.encounter()
        s["danger_cells"] = [24, 25]
        p = SurvivalPolicy()
        d = p.choose(s)
        self.assertNotIn(d.action["cell"], s["danger_cells"])
        self.assertNotEqual("combat: evade telegraph", d.reason)

    def test_rinses_at_safe_adjacent_water(self):
        s = self.encounter()
        s["map"]["cells"] = [{"cell": c, "terrain": 1, "visible": True} for c in range(49)]
        s["hero"]["buffs"] = [{"name": "ooze"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 29
        d = SurvivalPolicy().choose(s)
        self.assertEqual("boss: goo rinse ooze safely", d.reason)
        self.assertEqual(23, d.action["cell"])

    def test_prepares_health_before_waking_sleeping_goo(self):
        s = self.encounter()
        s["boss_health_text"] = None
        s["objects"][0]["sleeping"] = True
        s["hero"]["hp"] = 17
        self.assertEqual("boss: goo prepare health before engagement", SurvivalPolicy().choose(s).reason)

    def test_preparation_is_bounded_and_hunger_aware(self):
        s, p = self.encounter(), SurvivalPolicy()
        s["boss_health_text"] = None
        s["objects"][0]["sleeping"] = True
        s["inventory"][0]["status"] = "1/4"
        p.boss_strategies["goo"].preparation_waits = 120
        self.assertNotIn("prepare", p.choose(s).reason)
        s["hero"]["buffs"] = [{"name": "starving"}]
        self.assertNotIn("prepare", SurvivalPolicy().choose(s).reason)

    def test_spends_last_charge_against_goo(self):
        s = self.encounter()
        s["inventory"][0]["status"] = "1/4"
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])

    def test_missing_boss_is_not_invented_or_declared_dead_while_bar_remains(self):
        s, p = self.encounter(), SurvivalPolicy()
        s["objects"] = []
        p.update(s)
        strategy = p.boss_strategies["goo"]
        self.assertFalse(strategy.victory(p, s))
        self.assertIsNone(strategy.choose(p, s, [], distance, neighbors))

    def test_stays_outside_warning_if_no_attack_has_line_of_fire(self):
        s, p = self.encounter(), SurvivalPolicy()
        s["objects"][0]["cell"] = 26
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["danger_cells"] = [25, 26]
        p.update(s)
        d = p.boss_strategies["goo"].choose(p, s, s["objects"], distance, neighbors)
        self.assertEqual("boss: goo hold outside charged attack", d.reason)
