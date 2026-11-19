import unittest

from tools.survival_bot import Finished, SurvivalPolicy, distance
from tools.test_survival_bot import state


class NecromancerTests(unittest.TestCase):
    def test_haste_can_withdraw_through_exposed_steps_before_finishing_caster(self):
        s, p = state(), SurvivalPolicy()
        s["hero"].update(hp=10, max_hp=60, buffs=[{"name": "haste"}])
        floors = {17, 18, 23, 24, 25, 26, 31, 33}
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in floors else 4, "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 31, "name": "necromancer", "health_bar": [9, 43]},
                        {"cell": 23, "name": "necromancer's skeleton"},
                        {"cell": 17, "name": "DM-100"}, {"cell": 18, "name": "skeleton"}]
        d = p.choose(s)
        self.assertEqual("necro: haste withdrawal before linked skeleton explosion", d.reason)
        self.assertEqual(25, d.action["cell"])
        self.assertEqual(33, p.necro_escape_target)
        s["hero"]["cell"] = 25
        self.assertEqual(33, p.choose(s).action["cell"])

    def test_finishes_nearly_dead_guard_before_tunneling_on_caster(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 17, "name": "necromancer"},
                        {"cell": 31, "name": "prison guard", "health_bar": [3, 32]}]
        d = p.choose(s)
        self.assertEqual("necro: finish wounded adjacent attacker first", d.reason)
        self.assertEqual("ZAP", d.action["action"])
        self.assertEqual(31, p.target)

    def test_healthy_guard_does_not_displace_summoner_priority(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 17, "name": "necromancer"},
                        {"cell": 31, "name": "prison guard", "health_bar": [30, 32]}]
        self.assertEqual("necro: focus visible summoner", p.choose(s).reason)

    def test_casts_at_caster_not_adjacent_summon_when_shot_is_clear(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "necromancer"},
                        {"cell": 23, "name": "necromancer's skeleton"}]
        self.assertEqual("necro: focus visible summoner", p.choose(s).reason)
        self.assertEqual(26, p.target)

    def test_moves_around_blocking_skeleton_to_get_a_shot(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "necromancer"},
                        {"cell": 25, "name": "necromancer's skeleton"}]
        d = p.choose(s)
        self.assertEqual("necro: bypass minion toward summoner", d.reason)
        self.assertNotEqual(25, d.action["cell"])

    def test_caster_is_not_counted_as_second_melee_attacker(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "necromancer"},
                        {"cell": 32, "name": "necromancer's skeleton"}]
        p.update(s)
        self.assertIsNone(p.single_enemy_position(s, s["objects"]))
        self.assertEqual("necro: focus visible summoner", p.choose(s).reason)

    def test_spectral_necromancer_is_a_priority_over_its_wraiths(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "spectral necromancer"}, {"cell": 23, "name": "wraith"}]
        self.assertEqual("necro: focus visible summoner", p.choose(s).reason)
        self.assertEqual(26, p.target)

    def test_last_seen_caster_is_navigation_only_not_a_zap_target(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "necromancer"}]
        p.update(s)
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = False
        s["objects"] = [{"cell": 25, "name": "necromancer's skeleton"}]
        d = p.choose(s)
        self.assertEqual("necro: investigate last visible summoner position", d.reason)
        self.assertEqual("cell", d.action["type"])
        self.assertIsNone(p.target)

    def test_known_invisibility_is_used_to_escape_low_hp_attrition(self):
        s, p = state(), SurvivalPolicy()
        s["hero"]["hp"] = 8
        s["objects"] = [{"cell": 25, "name": "necromancer's skeleton"}]
        s["inventory"].append({"id": "escape", "name": "potion of invisibility", "actions": ["DRINK"]})
        self.assertEqual("escape", p.choose(s).action["id"])

    def test_skeleton_only_encounter_with_space_breaks_contact(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "necromancer's skeleton"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("necro: break contact with supported skeleton", d.reason)
        self.assertGreater(distance(d.action["cell"], 25, 7), 1)

    def test_boxed_in_blocker_attacks_are_bounded(self):
        s, p = state(), SurvivalPolicy()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (24, 25) else 4, "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 25, "name": "necromancer's skeleton"}]
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        for _ in range(4):
            self.assertEqual("necro: bounded attack on blocking summon", p.choose(s).reason)
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertEqual("blocked", error.exception.outcome)

    def test_ordinary_skeleton_is_not_assumed_to_have_a_summoner(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "skeleton"}]
        self.assertFalse(SurvivalPolicy().choose(s).reason.startswith("necro:"))

    def test_low_hp_does_not_finish_caster_beside_exploding_summon(self):
        s = state()
        s["hero"]["hp"] = 5
        s["objects"] = [{"cell": 26, "name": "necromancer", "health_bar": [2, 43]},
                        {"cell": 25, "name": "necromancer's skeleton"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("necro: gain distance before linked skeleton explosion", d.reason)
        self.assertGreater(distance(d.action["cell"], 25, 7), 1)

    def test_boxed_in_fatal_bone_explosion_is_not_a_valid_finishing_attack(self):
        s = state()
        s["hero"]["hp"] = 5
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (24, 25, 26) else 4, "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 26, "name": "necromancer", "health_bar": [2, 43]},
                        {"cell": 25, "name": "necromancer's skeleton"}]
        with self.assertRaises(Finished) as error:
            SurvivalPolicy().choose(s)
        self.assertIn("bone explosion", error.exception.reason)
