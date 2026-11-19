import unittest

from tools.combat_positioning import close_zapper, rinse_ooze
from tools.survival_bot import Finished, SurvivalPolicy, distance, neighbors
from tools.test_survival_bot import state, fully_known


class SkeletonSpacingTests(unittest.TestCase):
    def test_deep_sleep_is_a_nonlethal_escape_from_adjacent_skeleton(self):
        s = self.wounded()
        s["inventory"].append({"id": "sleep", "name": "stone of deep sleep", "actions": ["THROW"]})
        p = SurvivalPolicy()
        d = p.choose(s)
        self.assertEqual("sleep", d.action["id"])
        self.assertEqual(25, p.target)

    def test_starving_low_hp_hero_does_not_reawaken_a_slept_skeleton(self):
        s = self.wounded()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["objects"][0]["sleeping"] = True
        d = SurvivalPolicy().choose(s)
        self.assertNotEqual(25, d.action.get("cell"))
        self.assertNotEqual("ZAP", d.action.get("action"))

    def wounded(self):
        s = state()
        s["hero"].update(hp=7, max_hp=50)
        s["objects"] = [{"cell": 25, "name": "skeleton", "health_bar": [3, 32]}]
        return s

    def test_uses_fear_instead_of_finishing_adjacent_skeleton(self):
        s = self.wounded()
        s["inventory"].append({"id": "fear", "name": "stone of fear", "actions": ["THROW"]})
        p = SurvivalPolicy()
        d = p.choose(s)
        self.assertEqual("fear", d.action["id"])
        self.assertEqual(25, p.target)

    def test_retreat_is_bounded_instead_of_infinite_kiting_or_fatal_attack(self):
        s, p = self.wounded(), SurvivalPolicy()
        for _ in range(6):
            self.assertEqual("survival: gain spacing before skeleton death blast", p.choose(s).reason)
        with self.assertRaises(Finished):
            p.choose(s)

    def test_can_finish_from_range_or_when_healthy(self):
        s = self.wounded()
        s["objects"][0]["cell"] = 26
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])
        s["objects"][0]["cell"] = 25
        s["hero"]["hp"] = 50
        self.assertTrue(SurvivalPolicy().choose(s).reason.startswith("combat:"))

    def test_level_up_does_not_turn_twenty_hp_into_fatal_blast_guard(self):
        s = self.wounded()
        s["hero"].update(hp=20, max_hp=50)
        s["inventory"][0]["status"] = "0/4"
        s["inventory"].append({"id": "earth", "name": "wand of living earth +2", "actions": ["ZAP"],
                               "status": "3/4", "identified": True, "curse_known": True})
        d = SurvivalPolicy().choose(s)
        self.assertEqual("ZAP", d.action["action"])
        self.assertEqual("earth", d.action["id"])


class CriticalRetreatTests(unittest.TestCase):
    def test_lone_nearly_dead_slime_gets_bounded_finisher_not_endless_retreat(self):
        s, p = state(), SurvivalPolicy()
        s["hero"].update(hp=13, max_hp=40)
        s["inventory"][0]["status"] = "0/4"
        s["objects"] = [{"cell": 25, "name": "slime", "health_bar": [2, 37]}]
        for _ in range(2):
            d = p.choose(s)
            self.assertEqual("combat: melee", d.reason)
            self.assertEqual(25, d.action["cell"])
        self.assertEqual("combat: retreat at low health with exhausted magic", p.choose(s).reason)

    def test_defensive_invisibility_is_used_to_withdraw_not_immediately_attack(self):
        s = fully_known(state())
        s["hero"].update(hp=8, max_hp=55, buffs=[{"name": "invisible"}])
        s["objects"] = [{"cell": 26, "name": "crazy thief"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("combat: retreat under invisibility before reengaging", d.reason)
        self.assertGreater(distance(d.action["cell"], 26, 7), 2)

    def test_empty_staff_and_critical_hp_prefers_clear_step_over_melee(self):
        s = fully_known(state())
        s["hero"].update(hp=6, max_hp=35)
        s["inventory"][0]["status"] = "0/4"
        s["objects"] = [{"cell": 25, "name": "gnoll scout"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("combat: retreat at low health with exhausted magic", d.reason)
        self.assertGreater(distance(d.action["cell"], 25, 7), 1)

    def test_charged_magic_is_used_instead_of_endless_critical_retreat(self):
        s = state()
        s["hero"].update(hp=6, max_hp=35)
        s["objects"] = [{"cell": 25, "name": "gnoll scout"}]
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])


class RotGardenTests(unittest.TestCase):
    def garden(self):
        s = state()
        s["hero"]["cell"] = 23
        s["map"]["cells"] = [{"cell": c, "terrain": {22: 8, 23: 1, 24: 6, 25: 15, 26: 15}.get(c, 4), "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 26, "name": "rot lasher"}]
        return s

    def test_quest_room_is_blocked_but_outside_door_is_not(self):
        s, p = self.garden(), SurvivalPolicy()
        p.update(s)
        self.assertTrue(p.walkable(23))
        self.assertFalse(p.walkable(25))
        self.assertFalse(p.walkable(26))
        self.assertTrue(any(n["kind"] == "rot garden quest" for n in p.room_notes))

    def test_retreats_instead_of_using_sungrass_while_attacked(self):
        s = self.garden()
        s["hero"].update(cell=25, hp=10)
        s["inventory"].append({"id": "seed", "name": "seed of sungrass", "actions": ["PLANT", "THROW"]})
        d = SurvivalPolicy().choose(s)
        self.assertEqual("room: retreat to safe ground", d.reason)
        self.assertEqual(24, d.action["cell"])

    def test_rot_heart_alone_also_identifies_quest_detour(self):
        s, p = self.garden(), SurvivalPolicy()
        s["objects"][0]["name"] = "rot heart"
        p.update(s)
        self.assertFalse(p.walkable(25))


class OozeRinseTests(unittest.TestCase):
    def test_burning_rinse_prefers_unexposed_first_step_over_equal_length_water(self):
        s,p=self.wet_state()
        s["hero"]["buffs"]=[{"name":"burning"}]
        p.tiles[10]["terrain"]=29
        p.paths=lambda state,occupied=():{24:None,25:24,26:25,17:24,10:17}
        action=rinse_ooze(p,s,[{"name":"marsupial rat","cell":31}],distance,neighbors)
        self.assertEqual(17,action.action.get("cell"))
        self.assertEqual("retreat",action.intent)

    def wet_state(self):
        s = fully_known(state())
        s["hero"]["buffs"] = [{"name": "caustic ooze"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["terrain"] = 29
        p = SurvivalPolicy()
        p.update(s)
        return s, p

    def test_paths_to_water_two_moves_away_not_only_adjacent(self):
        s, p = self.wet_state()
        d = rinse_ooze(p, s, [], distance, neighbors)
        self.assertEqual("survival: wash ooze in nearby water", d.reason)
        self.assertEqual(1, distance(24, d.action["cell"], 7))
        self.assertLess(distance(d.action["cell"], 26, 7), 2)

    def test_piranha_pool_is_not_a_rinse_destination(self):
        s, p = self.wet_state()
        s["objects"] = [{"cell": 26, "name": "giant piranha"}]
        p.update(s)
        self.assertIsNone(rinse_ooze(p, s, [], distance, neighbors))

    def test_does_not_walk_into_warning_to_rinse(self):
        s, p = self.wet_state()
        s["danger_cells"] = [26]
        self.assertIsNone(rinse_ooze(p, s, [], distance, neighbors))

    def test_flying_hero_does_not_chase_water_that_cannot_cleanse(self):
        s, p = self.wet_state()
        s["hero"]["buffs"].append({"name": "levitating"})
        self.assertIsNone(rinse_ooze(p, s, [], distance, neighbors))

    def test_does_not_approach_melee_attacker_just_to_wash(self):
        s, p = self.wet_state()
        s["objects"] = [{"cell": 19, "name": "caustic slime"}]
        p.update(s)
        self.assertIsNone(rinse_ooze(p, s, s["objects"], distance, neighbors))

    def test_goo_rinse_rejects_water_in_charge_corner(self):
        s = state()
        s["hero"].update(cell=307, buffs=[{"name": "caustic ooze"}])
        s["map"].update(width=25, height=20)
        floors = {282, 283, 284, 285, 286, 307, 308, 309, 310, 311, 332, 333, 334}
        s["map"]["cells"] = [{"cell": c, "terrain": 29 if c == 282 else 1 if c in floors else 4, "visible": True}
                             for c in range(500)]
        s["objects"] = [{"cell": 283, "name": "Goo"}]
        p = SurvivalPolicy()
        p.update(s)
        self.assertIsNone(rinse_ooze(p, s, s["objects"], distance, neighbors))


class ZapperTests(unittest.TestCase):
    def test_retreat_does_not_leave_cover_for_a_zappers_firing_lane(self):
        s = fully_known(state())
        floors = {24, 31, 32, 33, 34}
        for tile in s["map"]["cells"]:
            tile["terrain"] = 1 if tile["cell"] in floors else 4
        s["objects"] = [{"cell": 34, "name": "DM-100"}]
        p = SurvivalPolicy()
        p.update(s)
        self.assertFalse(p.shot_clear(s, 34))
        d = p.retreat(s, s["objects"])
        if d:
            hypothetical = dict(s, hero=dict(s["hero"], cell=d.action["cell"]))
            self.assertFalse(p.shot_clear(hypothetical, 34))

    def test_unreachable_ordinary_enemy_does_not_cause_indefinite_waits(self):
        s, p = fully_known(state()), SurvivalPolicy()
        for tile in s["map"]["cells"]:
            tile["terrain"] = 1 if tile["cell"] in {24, 26} else 4
        s["objects"] = [{"cell": 26, "name": "gnoll scout"}]
        for _ in range(12):
            self.assertEqual("wait", p.choose(s).action["type"])
        with self.assertRaises(Finished):
            p.choose(s)

    def test_critical_health_uses_haste_before_gap_closing(self):
        s = state()
        s["hero"].update(hp=5, max_hp=60)
        s["objects"] = [{"cell": 26, "name": "DM-100"}]
        s["inventory"].append({"id": "haste", "name": "potion of haste", "actions": ["DRINK"]})
        self.assertEqual("haste", SurvivalPolicy().choose(s).action["id"])

    def test_critical_health_casts_instead_of_slow_gap_closing(self):
        s = state()
        s["hero"].update(hp=5, max_hp=60)
        s["objects"] = [{"cell": 26, "name": "DM-100"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("ZAP", d.action["action"])
        self.assertEqual("ranged: cast instead of slow gap closing at critical health", d.reason)

    def test_multiple_zappers_do_not_trigger_conflicting_melee_funneling(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "DM-100"}, {"cell": 32, "name": "DM-100"}]
        p.update(s)
        self.assertIsNone(p.single_enemy_position(s, s["objects"]))
        self.assertEqual("ranged: engage zapper at close range", p.choose(s).reason)

    def test_dm100_closes_instead_of_trading_distant_shots(self):
        s = state()
        s["objects"] = [{"cell": 26, "name": "DM-100"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("ranged: close distance to stop ranged zaps", d.reason)
        self.assertEqual(1, distance(d.action["cell"], 26, 7))

    def test_adjacent_zapper_is_attacked_without_backing_off(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "DM-100"}]
        self.assertEqual("ranged: engage zapper at close range", SurvivalPolicy().choose(s).reason)

    def test_other_ranged_casters_also_have_melee_gap_closing(self):
        for name in ("gnoll shaman", "dwarf warlock"):
            s = state()
            s["objects"] = [{"cell": 26, "name": name}]
            self.assertEqual("ranged: close distance to stop ranged zaps", SurvivalPolicy().choose(s).reason)

    def test_sleeping_zapper_does_not_trigger_approach_tactics(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "DM-100", "sleeping": True}]
        p.update(s)
        self.assertIsNone(close_zapper(p, s, s["objects"], distance))

    def test_does_not_ignore_adjacent_melee_threat_to_chase_zapper(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "DM-100"}, {"cell": 23, "name": "prison guard"}]
        p.update(s)
        self.assertIsNone(close_zapper(p, s, s["objects"], distance))
