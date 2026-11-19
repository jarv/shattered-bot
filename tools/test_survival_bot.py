import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from .survival_bot import Decision, Finished, Intent, SurvivalPolicy, NavigationLoopGuard, distance, line_clear, neighbors, run
except ImportError:
    from survival_bot import Decision, Finished, Intent, SurvivalPolicy, NavigationLoopGuard, distance, line_clear, neighbors, run


def state():
    return {
        "scene": "GameScene", "status": "ready", "modal": False, "depth": 1,
        "observation_id": 1, "boss_health_text": None, "danger_cells": [],
        "hero": {"name": "mage", "cell": 24, "hp": 20, "max_hp": 20,
                 "level": 1, "buffs": [], "talents": []},
        "inventory": [{"id": "item-0", "name": "staff of magic missile", "actions": ["ZAP", "IMBUE"],
                       "status": "4/4", "equipped": True}],
        "map": {"width": 7, "height": 7,
                "cells": [{"cell": y * 7 + x, "terrain": 1, "visible": True, "effects": []}
                          for y in range(1, 6) for x in range(1, 6)]},
        "objects": [], "ui": {"texts": [], "buttons": []},
    }


def fully_known(s):
    known = {t["cell"] for t in s["map"]["cells"]}
    s["map"]["cells"] += [{"cell": c, "terrain": 4, "visible": True} for c in range(49) if c not in known]
    return s


def explored_policy(s):
    p = SurvivalPolicy()
    p.update(s)
    p.visits.update({c: 1 for c in p.paths(s)})
    p.searches = 40
    return p


class NavigationTests(unittest.TestCase):
    def test_magic_mapping_does_not_count_unseen_rooms_as_explored(self):
        s = fully_known(state())
        for tile in s["map"]["cells"]:
            tile.update(mapped=True, observed=True)
        unseen = next(t for t in s["map"]["cells"] if t["cell"] == 40)
        unseen.update(visible=False, observed=False)
        p = explored_policy(s)
        self.assertIn(40, p.paths(s))
        self.assertIn(40, p.exploration_report(s, p.paths(s))["unexplored_frontiers"])
        self.assertEqual("explore: frontier", p.explore(s, []).reason)
        unseen.update(visible=True, observed=True)
        p.update(s)
        self.assertNotIn(40, p.exploration_report(s, p.paths(s))["unexplored_frontiers"])

    def test_last_seen_combat_approach_is_not_reversed_by_nearby_loot(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "marsupial rat"}]
        p.update(s)
        p.combat_approach_target = 26
        p.combat_approach_steps = 1
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = False
        s["objects"] = [{"cell": 23, "name": "jade potion", "top_item": {"name": "jade potion"}}]
        d = p.choose(s)
        self.assertEqual("explore: continue last-seen combat approach", d.reason)
        self.assertEqual(1, distance(d.action["cell"], 26, 7))
        self.assertIsNone(p.target)  # Memory is not a blind zap target.
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["visible"] = True
        p.choose(s)
        self.assertIsNone(p.combat_approach_target)

    def test_living_skeleton_is_not_remembered_as_route_blocking_bones(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "skeleton", "description":
                         "Skeletons are composed of the bones of unlucky adventurers and inhabitants of the prison."}]
        p.update(s)
        self.assertNotIn(25, p.loot)
        self.assertIn(25, p.enemy_sightings)
        self.assertNotIn(25, p.room_blocked)
        s["objects"] = [{"cell": 25, "name": "skeleton", "description": "These bones are all that remains of an adventurer."}]
        p.update(s)
        self.assertIn(25, p.loot)
        self.assertIn(25, p.room_blocked)
        self.assertFalse(p.choose(s).reason.startswith("combat:"))

    def test_spent_trap_is_walkable_but_active_trap_is_not(self):
        s, p = state(), SurvivalPolicy()
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        tile.update(terrain=19, name="Triggered trap", trap="burning trap")
        p.update(s)
        self.assertTrue(p.walkable(25))
        self.assertIn(25, p.paths(s))
        tile.update(terrain=18, name="Trap")
        p.update(s)
        self.assertFalse(p.walkable(25))
        self.assertNotIn(25, p.paths(s))

    def test_no_wrapping_at_grid_edge(self):
        self.assertNotIn(6, list(neighbors(7, 7, 7)))
        self.assertEqual(3, len(list(neighbors(0, 7, 7))))

    def test_distance_is_chebyshev(self):
        self.assertEqual(1, distance(0, 8, 7))

    def test_beam_does_not_pass_unknown_or_closed_doors(self):
        tiles = {1: {"terrain": 1}, 2: {"terrain": 5}, 3: {"terrain": 1}}
        self.assertFalse(line_clear(1, 3, 7, tiles))
        tiles[2]["terrain"] = 1
        self.assertTrue(line_clear(1, 3, 7, tiles))
        del tiles[2]
        self.assertFalse(line_clear(1, 3, 7, tiles))

    def test_paths_avoid_discovered_traps_and_effects(self):
        s = state()
        s["map"]["cells"][0]["trap"] = "poison dart trap"
        s["map"]["cells"][1]["effects"] = ["toxic gas"]
        p = SurvivalPolicy()
        p.update(s)
        paths = p.paths(s)
        self.assertNotIn(s["map"]["cells"][0]["cell"], paths)
        self.assertNotIn(s["map"]["cells"][1]["cell"], paths)

    def test_paths_do_not_open_tombs_on_the_way_to_other_loot(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "Tomb"},
                        {"cell": 26, "name": "scroll of identify", "top_item": {"name": "scroll of identify"}}]
        p = SurvivalPolicy()
        p.update(s)
        paths = p.paths(s)
        self.assertNotIn(25, paths)
        self.assertIn(26, paths)


class PolicyTests(unittest.TestCase):
    def test_automatic_next_upgrade_preview_is_cancelled_not_spent(self):
        s, p = state(), SurvivalPolicy()
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["Upgrade an Item", "Upgrading an item permanently improves it:", "+4", "+5", "Upgrade", "Back"],
                   "buttons": [{"id": "back", "label": "Back"}]}
        self.assertEqual("back", p.choose(s).action["type"])
        self.assertEqual("upgrade-cancel", p.menu_plan)
        s["ui"] = {"texts": ["Upgrade an item"], "buttons": [{"id": "staff", "label": "staff of magic missile +4"}]}
        self.assertEqual("back", p.choose(s).action["type"])
        self.assertIsNone(p.menu_plan)

    def test_zap_then_target(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "sewer snake"}]
        d = p.choose(s)
        self.assertEqual("ZAP", d.action["action"])
        s["status"] = "targeting"
        d = p.choose(s)
        self.assertEqual({"type": "cell", "cell": 26}, d.action)

    def test_no_guessing_unexpected_target(self):
        s = state()
        s["status"] = "targeting"
        with self.assertRaises(Finished) as error:
            SurvivalPolicy().choose(s)
        self.assertEqual("blocked", error.exception.outcome)

    def test_goo_warning_takes_priority_over_attack(self):
        s = state()
        s["depth"] = 5
        s["objects"] = [{"cell": 25, "name": "Goo"}]
        s["boss_health_text"] = "80/100"
        s["danger_cells"] = [24, 25, 17, 18, 31, 32, 26, 19, 33]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("cell", d.action["type"])
        self.assertNotIn(d.action["cell"], s["danger_cells"])

    def test_healing_before_fighting(self):
        s = state()
        s["hero"]["hp"] = 5
        s["objects"] = [{"cell": 25, "name": "sewer crab"}]
        s["inventory"].append({"id": "item-1", "name": "potion of healing", "actions": ["DRINK"]})
        self.assertEqual("item-1", SurvivalPolicy().choose(s).action["id"])

    def test_finishes_weak_adjacent_rat_without_spending_charge(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "marsupial rat", "health_bar": [1, 10]}]
        self.assertEqual({"type": "cell", "cell": 25}, SurvivalPolicy().choose(s).action)

    def test_does_not_wait_forever_for_stationary_enemy(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"][0]["actions"] = ["IMBUE"]
        s["objects"] = [{"cell": 26, "name": "gnoll scout"}]
        self.assertEqual("wait", p.choose(s).action["type"])
        self.assertEqual("wait", p.choose(s).action["type"])
        self.assertEqual("cell", p.choose(s).action["type"])

    def test_does_not_wake_sleeping_enemy_while_recovering(self):
        s = state()
        s["hero"]["hp"] = 12
        s["objects"] = [{"cell": 26, "name": "sewer crab", "sleeping": True}]
        self.assertEqual("recover: natural healing", SurvivalPolicy().choose(s).reason)

    def test_sleeping_snake_behind_cover_does_not_interrupt_loot_route(self):
        s = state()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        s["objects"] = [{"cell": 26, "name": "sewer snake", "sleeping": True},
                        {"cell": 17, "name": "ration of food", "top_item": {"name": "ration of food"}}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("loot: collect/open", d.reason)
        self.assertEqual(17, d.action["cell"])

    def test_sleeping_snake_with_clear_shot_does_not_trigger_retreat(self):
        s = state()
        s["objects"] = [{"cell": 26, "name": "sewer snake", "sleeping": True}]
        self.assertEqual("snake: safe opening shot", SurvivalPolicy().choose(s).reason)

    def test_allocate_only_advertised_available_talents(self):
        s = state()
        s["hero"]["talents"] = [{"name": "backup barrier", "points": 0, "max_points": 2, "available": 1}]
        self.assertEqual({"type": "talent", "name": "backup barrier"}, SurvivalPolicy().choose(s).action)

    def test_no_false_victory_before_boss_engagement(self):
        s = state()
        s["depth"] = 5
        self.assertIsInstance(SurvivalPolicy().choose(s), Decision)

    def test_journal_badges_window_is_safe_to_dismiss(self):
        s = state()
        s.update(modal=True, status="menu")
        s["ui"] = {"texts": ["This Run", "Overall"], "buttons": [
            {"id": str(i), "label": name} for i, name in enumerate(
                ("This Run", "Overall", "Adventuring Notes", "Dungeon Guide", "Alchemy Guide", "Catalogs", "Badges"))]}
        self.assertEqual({"type": "back"}, SurvivalPolicy().choose(s).action)

    def test_boss_bar_must_disappear_not_just_monster(self):
        s, p = state(), SurvivalPolicy(goal="goo")
        s["depth"] = 5
        s["boss_health_text"] = "100/100"
        p.choose(s)
        self.assertIsInstance(p.choose(s), Decision)
        s["boss_health_text"] = None
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertEqual("success", error.exception.outcome)

    def test_death_never_counts_as_victory(self):
        s, p = state(), SurvivalPolicy()
        p.boss_seen = True
        s.update(status="dead", depth=5)
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertEqual("dead", error.exception.outcome)

    def test_safe_startup_selects_mage(self):
        s = {"scene": "HeroSelectScene", "ui": {"texts": ["Choose Your Hero"],
             "buttons": [{"id": "button-1", "label": "mage"}]}}
        self.assertEqual("button-1", SurvivalPolicy().choose(s).action["id"])

    def test_fresh_profile_reads_tutorial_via_journal(self):
        s = state()
        s["ui"] = {"texts": ["Select the flashing journal button (J) to read the book."],
                   "buttons": [{"id": "button-1", "label": "Journal"}]}
        d = SurvivalPolicy().choose(s)
        self.assertEqual({"type": "button", "id": "button-1"}, d.action)

    def test_unknown_potions_are_not_treated_as_healing(self):
        s = state()
        s["hero"]["hp"] = 3
        s["objects"] = [{"cell": 25, "name": "sewer crab"}]
        s["inventory"].append({"id": "item-1", "name": "charcoal potion", "actions": ["DRINK"]})
        self.assertNotEqual("DRINK", SurvivalPolicy().choose(s).action.get("action"))

    def test_rest_does_not_automatically_starve(self):
        s = state()
        s["hero"]["hp"] = 12
        s["hero"]["buffs"] = [{"name": "starving"}]
        self.assertNotEqual("recover: natural healing", SurvivalPolicy().choose(s).reason)

    def test_starving_mage_eats_at_full_health_instead_of_waiting_for_damage(self):
        s = state()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["inventory"].append({"id": "food", "name": "ration of food", "actions": ["EAT"]})
        self.assertEqual({"type": "item", "id": "food", "action": "EAT"}, SurvivalPolicy().choose(s).action)

    def test_hungry_mage_without_food_descends_instead_of_resting(self):
        s = fully_known(state())
        s["hero"].update(hp=12, buffs=[{"name": "hungry"}])
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        self.assertEqual("stairs: conserve food and health", SurvivalPolicy().choose(s).reason)

    def test_hungry_mage_collects_nearby_food_before_descending(self):
        s = fully_known(state())
        s["hero"]["buffs"] = [{"name": "hungry"}]
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        s["objects"] = [{"cell": 23, "name": "ration of food", "top_item": {"name": "ration of food"}}]
        self.assertEqual("loot: nearby food before descent", SurvivalPolicy().choose(s).reason)

    def test_recharges_staff_before_engaging_sleeping_goo(self):
        s = state()
        s["depth"] = 5
        s["inventory"][0]["status"] = "2/7"
        s["objects"] = [{"cell": 26, "name": "Goo", "sleeping": True}]
        self.assertEqual("boss: goo prepare wand charges before engagement", SurvivalPolicy().choose(s).reason)

    def test_no_pointless_natural_healing_waits_on_locked_floor(self):
        s = state()
        s["hero"]["hp"] = 12
        s["hero"]["buffs"] = [{"name": "locked floor"}]
        self.assertNotEqual("recover: natural healing", SurvivalPolicy().choose(s).reason)

    def test_floor_change_does_not_reuse_previous_level_navigation(self):
        s, p = state(), SurvivalPolicy()
        p.update(s)
        p.blocked.add(25)
        s["depth"] = 2
        p.update(s)
        self.assertNotIn(25, p.blocked)

    def test_enemy_positions_are_not_remembered_as_loot(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "sewer crab"}]
        p.update(s)
        self.assertNotIn(25, p.loot)

    def test_fully_explored_floor_descends(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        decision = explored_policy(s).choose(s)
        self.assertEqual("stairs: descend after floor exploration", decision.reason)
        self.assertEqual(25, decision.action["cell"])

    def test_closed_visited_door_does_not_cause_backtracking_loop(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 5
        p = explored_policy(s)
        self.assertEqual("stairs: descend after floor exploration", p.choose(s).reason)

    def test_unhandled_modal_stops_without_clicking_choices(self):
        s = state()
        s.update(status="menu", modal=True)
        s["ui"]["buttons"] = [{"id": "button-0", "label": "Jump into the chasm"}]
        with self.assertRaises(Finished) as error:
            SurvivalPolicy().choose(s)
        self.assertEqual("blocked", error.exception.outcome)

    def test_staff_upgrade_uses_menu_button_handles(self):
        p, s = SurvivalPolicy(), state()
        s["inventory"].append({"id": "item-1", "name": "scroll of upgrade", "actions": ["READ"]})
        self.assertEqual("READ", p.choose(s).action["action"])
        s.update(status="menu", modal=True)
        s["ui"]["buttons"] = [{"id": "button-9", "label": "staff of magic missile"}]
        self.assertEqual("button-9", p.choose(s).action["id"])
        s["ui"]["buttons"] = [{"id": "button-4", "label": "Upgrade"}]
        self.assertEqual("button-4", p.choose(s).action["id"])

    def test_wraith_magic_has_priority_over_adjacent_rat(self):
        s = state()
        s["objects"] = [{"cell": 23, "name": "marsupial rat"}, {"cell": 26, "name": "wraith"}]
        p = SurvivalPolicy()
        self.assertEqual("wraith: guaranteed magic damage", p.choose(s).reason)
        self.assertEqual(26, p.target)

    def test_uses_spare_damage_wand_for_wraith_when_staff_empty(self):
        s = state()
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["inventory"].append({"id": "item-2", "name": "wand of frost", "status": "1/2", "actions": ["ZAP"]})
        s["objects"] = [{"cell": 25, "name": "wraith"}]
        self.assertEqual("item-2", SurvivalPolicy().choose(s).action["id"])

    def test_unknown_or_nondamaging_wand_is_not_assumed_to_kill_wraith(self):
        s = state()
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["inventory"].append({"id": "item-2", "name": "wand of regrowth", "status": "2/2", "actions": ["ZAP"]})
        s["objects"] = [{"cell": 25, "name": "wraith"}]
        self.assertEqual("cell", SurvivalPolicy().choose(s).action["type"])
        self.assertNotEqual(25, SurvivalPolicy().choose(s).action.get("cell"))

    def test_empty_staff_wraith_is_kited_instead_of_meleed(self):
        s = state()
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["objects"] = [{"cell": 25, "name": "wraith"}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("wraith: kite while magic recharges", d.reason)
        self.assertGreater(distance(d.action["cell"], 25, 7), 1)

    def test_trapped_wraith_stops_instead_of_spamming_misses(self):
        s = state()
        s["map"]["cells"] = [{"cell": 24, "terrain": 1, "visible": True}, {"cell": 25, "terrain": 1, "visible": True}]
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["objects"] = [{"cell": 25, "name": "wraith"}]
        with self.assertRaises(Finished) as error:
            SurvivalPolicy().choose(s)
        self.assertIn("refusing futile melee", error.exception.reason)

    def test_last_charge_is_reserved_against_ordinary_rat(self):
        s = state()
        s["inventory"][0]["status"] = "1/4"
        s["objects"] = [{"cell": 25, "name": "marsupial rat"}]
        self.assertEqual("combat: melee", SurvivalPolicy().choose(s).reason)

    def test_two_charges_are_reserved_against_healthy_ordinary_rat(self):
        s = state()
        s["inventory"][0]["status"] = "2/4"
        s["objects"] = [{"cell": 25, "name": "marsupial rat"}]
        self.assertEqual("combat: melee", SurvivalPolicy().choose(s).reason)

    def test_healthy_mage_finishes_wounded_snake_instead_of_abandoning_run(self):
        s = state()
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["objects"] = [{"cell": 25, "name": "sewer snake", "health_bar": [8, 32]}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("snake: bounded finishing melee", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_finishing_snake_attempts_are_bounded(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["objects"] = [{"cell": 25, "name": "sewer snake", "health_bar": [8, 32]}]
        for _ in range(4):
            self.assertEqual("snake: bounded finishing melee", p.choose(s).reason)
        self.assertNotEqual("snake: bounded finishing melee", p.choose(s).reason)

    def test_low_health_mage_does_not_take_finishing_risk(self):
        s = state()
        s["hero"]["hp"] = 10
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["objects"] = [{"cell": 25, "name": "sewer snake", "health_bar": [8, 32]}]
        self.assertNotEqual("snake: bounded finishing melee", SurvivalPolicy().choose(s).reason)

    def test_charged_magic_is_preferred_for_finishing_snake(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "sewer snake", "health_bar": [8, 32]}]
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action.get("action"))

    def test_two_floor_checkpoint_requires_both_observed_descents(self):
        s, p = state(), SurvivalPolicy(goal="two-floors")
        p.choose(s)
        p.cell(25, "stairs: descend after floor exploration", intent=Intent.DESCEND)
        s["depth"] = 2
        p.choose(s)
        p.cell(25, "stairs: descend after floor exploration", intent=Intent.DESCEND)
        s["depth"] = 3
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertEqual("success", error.exception.outcome)
        self.assertEqual([1, 2], p.cleared_floors)
        self.assertIn("floor 3", error.exception.reason)

    def test_attaching_on_floor_three_is_not_a_two_floor_success(self):
        s = state()
        s["depth"] = 3
        with self.assertRaises(Finished) as error:
            SurvivalPolicy(goal="two-floors").choose(s)
        self.assertEqual("blocked", error.exception.outcome)

    def test_death_never_counts_as_two_floor_success(self):
        s, p = state(), SurvivalPolicy(goal="two-floors")
        p.cleared_floors = [1, 2]
        s.update(depth=3, status="dead")
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertEqual("dead", error.exception.outcome)

    def test_doorway_surprise_attack_for_wraith_and_snake(self):
        for name, kind in (("wraith", "wraith"), ("sewer snake", "snake")):
            with self.subTest(enemy=name):
                s, p = state(), SurvivalPolicy()
                s["inventory"][0].update(status="0/4", actions=["IMBUE"])
                s["hero"]["cell"] = 24
                next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
                s["objects"] = [{"cell": 25, "name": name}]
                p.update(s)
                p.last_state = copy.deepcopy(s)
                p.last_state["hero"]["cell"] = 25
                p.ambush_plan = {"door": 25, "hide": 24, "waits": 0, "kind": kind, "last_enemy": 26}
                d = p.choose(s)
                self.assertEqual(f"{kind}: doorway surprise attack", d.reason)
                self.assertEqual(25, d.action["cell"])

    def test_door_ambush_persists_while_enemy_is_out_of_sight(self):
        s, p = state(), SurvivalPolicy()
        p.update(s)
        # update initializes per-floor state, so establish the plan on this floor.
        p.ambush_plan = {"door": 25, "hide": 24, "waits": 0, "kind": "wraith", "last_enemy": 26}
        self.assertEqual("wraith: await doorway ambush", p.choose(s).reason)
        self.assertIsNotNone(p.ambush_plan)

    def test_doorway_setup_crosses_breaks_sight_and_then_strikes(self):
        for name, kind in (("wraith", "wraith"), ("sewer snake", "snake")):
            with self.subTest(enemy=name):
                s, p = state(), SurvivalPolicy()
                s["map"]["cells"] = [{"cell": c, "terrain": 5 if c == 24 else 1, "visible": True}
                                     for c in (22, 23, 24, 25, 26)]
                s["hero"]["cell"] = 23
                s["inventory"][0].update(status="0/4", actions=["IMBUE"])
                s["objects"] = [{"cell": 26, "name": name}]
                self.assertEqual(24, p.choose(s).action["cell"])
                s = copy.deepcopy(s)
                s["hero"]["cell"] = 24
                s["objects"][0]["cell"] = 25
                next(t for t in s["map"]["cells"] if t["cell"] == 24)["terrain"] = 6
                self.assertEqual(23, p.choose(s).action["cell"])
                s = copy.deepcopy(s)
                s["hero"]["cell"] = 23
                s["objects"][0]["cell"] = 24
                self.assertEqual(f"{kind}: doorway surprise attack", p.choose(s).reason)

    def test_magic_ray_does_not_ignore_other_monsters(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "marsupial rat"}, {"cell": 26, "name": "wraith"}]
        p.update(s)
        self.assertFalse(p.shot_clear(s, 26))


class ExplorationTests(unittest.TestCase):
    def lock_state(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": {24: 1, 25: 10, 26: 1, 23: 8}.get(c, 4), "visible": True}
                             for c in range(49)]
        return s

    def test_collect_keys_before_other_loot(self):
        s = state()
        s["objects"] = [{"cell": 17, "name": "ration of food", "top_item": {"name": "ration of food"}},
                        {"cell": 26, "name": "iron key", "top_item": {"name": "iron key"}}]
        self.assertEqual("loot: collect key", SurvivalPolicy().choose(s).reason)

    def test_unlocks_door_with_matching_floor_iron_key(self):
        s = self.lock_state()
        s["keys"] = [{"name": "iron key", "quantity": 1, "depth": 1}]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("explore: unlock iron door", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_crystal_door_uses_crystal_not_iron_key(self):
        s = self.lock_state()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 31
        s["keys"] = [{"name": "crystal key", "quantity": 1, "depth": 1}]
        self.assertEqual("explore: unlock crystal door", SurvivalPolicy().choose(s).reason)

    def test_key_from_different_floor_cannot_unlock_door(self):
        s = self.lock_state()
        s["keys"] = [{"name": "iron key", "quantity": 1, "depth": 2}]
        p = explored_policy(s)
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))
        self.assertEqual(0, p.keys["iron"])
        self.assertIn(25, p.exploration_report(s, p.paths(s))["unresolved_doors"])

    def test_missing_keys_are_logged_without_blocking_descent(self):
        s = self.lock_state()
        p = explored_policy(s)
        self.assertEqual("stairs: descend with deferred rooms", p.choose(s).reason)
        self.assertEqual([25], p.exploration_report(s, p.paths(s))["unresolved_doors"])

    def test_missing_key_does_not_trigger_search_when_exit_is_known(self):
        s, p = self.lock_state(), SurvivalPolicy()
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))
        self.assertEqual(0, p.searches)

    def test_distant_well_is_remembered_on_the_floor_below(self):
        s, p = state(), SurvivalPolicy()
        next(t for t in s["map"]["cells"] if t["cell"] == 26).update(terrain=0, name="Distant well")
        p.update(s)
        self.assertIn(2, p.drop_room_expected_on)
        s = self.lock_state()
        s["depth"] = 2
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 31
        p.update(s)
        report = p.exploration_report(s, p.paths(s))
        self.assertTrue(report["drop_room_expected"])
        self.assertEqual([1], report["observed_distant_well_floors"])
        note = next(r for r in report["skipped_special_rooms"] if r["kind"] == "possible one-way drop-room exit")
        self.assertEqual([25], note["cells"])

    def test_plain_chasm_is_not_invented_as_a_well(self):
        s, p = state(), SurvivalPolicy()
        next(t for t in s["map"]["cells"] if t["cell"] == 26).update(terrain=0, name="Chasm")
        p.update(s)
        self.assertFalse(p.drop_room_expected_on)

    def test_locked_door_is_not_assumed_open_in_paths(self):
        s, p = self.lock_state(), SurvivalPolicy()
        s["keys"] = [{"name": "iron key", "quantity": 1, "depth": 1}]
        p.update(s)
        self.assertIn(25, p.paths(s))
        self.assertNotIn(26, p.paths(s))

    def test_new_key_reenables_previously_failed_lock(self):
        s, p = self.lock_state(), SurvivalPolicy()
        p.update(s)
        p.blocked.add(25)
        p.failed_moves[25] = 2
        s["keys"] = [{"name": "iron key", "quantity": 1, "depth": 1}]
        d = p.choose(s)
        self.assertEqual("explore: unlock iron door", d.reason)
        self.assertNotIn(25, p.blocked)

    def test_enters_newly_unlocked_room_before_stairs(self):
        s = self.lock_state()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        p = explored_policy(s)
        p.visits[25] = p.visits[26] = 0
        d = p.choose(s)
        self.assertEqual("explore: unopened door", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_visible_but_unvisited_empty_floor_does_not_delay_descent(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        p = explored_policy(s)
        p.visits[26] = 0
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))

    def test_stairs_are_never_a_transit_shortcut(self):
        s = self.lock_state()
        for tile in s["map"]["cells"]:
            if tile["cell"] == 25:
                tile["terrain"] = 8
        p = SurvivalPolicy()
        p.update(s)
        self.assertNotIn(26, p.paths(s))

    def test_secret_search_moves_to_new_vantage(self):
        s = self.lock_state()
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 1
        p = explored_policy(s)
        p.searches = 0
        first = p.choose(s)
        self.assertTrue(first.reason.startswith("explore:"))
        self.assertFalse(first.reason.startswith("stairs:"))
        self.assertLessEqual(p.searches, 1)

    def test_no_extra_secret_search_when_exit_and_ordinary_rooms_are_resolved(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
        p = SurvivalPolicy()
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))
        self.assertEqual(0, p.searches)

    def test_tries_to_clear_known_enemy_before_leaving(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 8
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        s["objects"] = [{"cell": 26, "name": "gnoll scout", "sleeping": True}]
        p = explored_policy(s)
        self.assertEqual("explore: clear ordinary enemy sighting", p.choose(s).reason)

    def test_clear_sweep_is_bounded_rather_than_patrolling_for_respawns(self):
        s = fully_known(state())
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 8
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 5
        s["objects"] = [{"cell": 26, "name": "gnoll scout", "sleeping": True}]
        p = explored_policy(s)
        p.clear_steps = 80
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))
        self.assertTrue(p.exploration_report(s, p.paths(s))["remaining_enemy_sightings"])

    def test_last_seen_enemy_is_forgotten_when_cell_is_visibly_empty(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 26, "name": "gnoll scout", "sleeping": True}]
        p.update(s)
        self.assertIn(26, p.enemy_sightings)
        s["objects"] = []
        p.update(s)
        self.assertNotIn(26, p.enemy_sightings)


class SpecialRoomTests(unittest.TestCase):
    def sentry_state(self):
        s = state()
        terrain = {24: 1, 23: 1, 22: 8, 25: 5, 26: 11, 19: 14, 18: 14, 12: 14, 11: 11}
        s["map"]["cells"] = [{"cell": c, "terrain": terrain.get(c, 4), "visible": True} for c in range(49)]
        s["objects"] = [{"cell": 26, "name": "red sentry"}, {"cell": 11, "name": "Chest"}]
        return s

    def test_red_sentry_is_not_loot_and_exposed_floor_is_avoided(self):
        s, p = self.sentry_state(), SurvivalPolicy()
        p.update(s)
        self.assertNotIn(26, p.loot)
        self.assertFalse(p.walkable(18))
        self.assertNotIn(18, p.paths(s))

    def test_skipped_sentry_room_does_not_block_ordinary_floor_completion(self):
        s = self.sentry_state()
        p = explored_policy(s)
        self.assertTrue(p.choose(s).reason.startswith("stairs:"))
        report = p.exploration_report(s, p.paths(s))
        self.assertIn(11, report["skipped_special_cells"])
        self.assertTrue(any(r["kind"] == "sentry" for r in report["skipped_special_rooms"]))

    def test_retreats_instead_of_resting_under_sentry_fire(self):
        s = self.sentry_state()
        s["hero"].update(cell=18, hp=8)
        d = SurvivalPolicy().choose(s)
        self.assertEqual("room: retreat to safe ground", d.reason)
        self.assertIn(d.action["cell"], (24, 25))

    def test_piranha_pool_is_not_walked_into(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": {16: 1, 24: 1, 23: 8, 25: 29, 26: 29}.get(c, 4), "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 26, "name": "giant piranha"}]
        p = explored_policy(s)
        self.assertFalse(p.walkable(25))
        self.assertFalse(p.walkable(24))  # The bank is also within melee reach.
        self.assertEqual("room: retreat to safe ground", p.choose(s).reason)

    def test_does_not_rest_on_diagonal_piranha_bank(self):
        s, p = state(), SurvivalPolicy()
        s["hero"]["hp"] = 10
        next(t for t in s["map"]["cells"] if t["cell"] == 32)["terrain"] = 29
        s["objects"] = [{"cell": 32, "name": "giant piranha"}]
        d = p.choose(s)
        self.assertEqual("room: retreat to safe ground", d.reason)
        self.assertNotIn(d.action["cell"], p.room_blocked)

    def test_unknown_actor_is_not_assumed_to_be_collectible(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "unknown guardian"}]
        p.update(s)
        self.assertNotIn(25, p.loot)
        self.assertFalse(p.walkable(25))

    def test_unseen_gas_is_not_assumed_to_have_expired(self):
        s, p = state(), SurvivalPolicy()
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        tile["effects"] = ["A deadly cloud of toxic gas"]
        p.update(s)
        tile.pop("effects")
        tile["visible"] = False
        p.update(s)
        self.assertFalse(p.walkable(25))
        tile.update(visible=True, effects=[])
        p.update(s)
        self.assertTrue(p.walkable(25))

    def test_an_isolated_ordinary_trap_does_not_excuse_unfinished_floor(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": {24: 1, 23: 8, 25: 18, 26: 1}.get(c, 4), "visible": True}
                             for c in range(49)]
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["trap"] = "poison dart trap"
        p = explored_policy(s)
        self.assertEqual("stairs: descend with deferred rooms", p.choose(s).reason)
        report = p.exploration_report(s, p.paths(s))
        self.assertIn(26, report["unreachable_known_floor"])
        self.assertNotIn(26, report["skipped_special_cells"])

    def sheep_state(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": {24: 1, 23: 8, 25: 1, 26: 1}.get(c, 4), "visible": True}
                             for c in range(49)]
        s["objects"] = [{"cell": 25, "name": "sheep"}]
        return s

    def test_waits_for_temporary_sheep_instead_of_declaring_floor_inaccessible(self):
        d = SurvivalPolicy().choose(self.sheep_state())
        self.assertEqual("obstacle: wait for magic sheep to fade", d.reason)
        self.assertEqual({"type": "wait"}, d.action)

    def test_sheep_wait_is_bounded(self):
        s, p = self.sheep_state(), SurvivalPolicy()
        for _ in range(12):
            self.assertEqual("obstacle: wait for magic sheep to fade", p.choose(s).reason)
        with self.assertRaises(Finished) as error:
            p.choose(s)
        self.assertIn("12 waits", error.exception.reason)

    def test_paths_reopen_when_sheep_fade(self):
        s, p = self.sheep_state(), SurvivalPolicy()
        p.choose(s)
        self.assertNotIn(26, p.paths(s))
        s["objects"] = []
        p.update(s)
        self.assertIn(26, p.paths(s))
        self.assertEqual(0, p.temporary_block_waits)

    def test_does_not_wait_for_sheep_while_an_enemy_can_attack(self):
        s = self.sheep_state()
        next(t for t in s["map"]["cells"] if t["cell"] == 17)["terrain"] = 1
        s["objects"].append({"cell": 17, "name": "marsupial rat"})
        self.assertNotEqual("obstacle: wait for magic sheep to fade", SurvivalPolicy().choose(s).reason)

    def test_sheep_also_block_magic_projectiles(self):
        s, p = self.sheep_state(), SurvivalPolicy()
        s["objects"].append({"cell": 26, "name": "marsupial rat"})
        p.update(s)
        self.assertFalse(p.shot_clear(s, 26))


class LoopGuardTests(unittest.TestCase):
    def test_funnel_gap_close_oscillation_is_bounded_despite_health_changes(self):
        guard, s = NavigationLoopGuard(repetitions=3), state()
        guard.visited.update({(1, 0, 23), (1, 0, 24)})
        for _ in range(2):
            s["hero"]["cell"] = 24
            guard.check(s, Decision({"type": "cell", "cell": 23}, "combat: funnel enemies to fight one at a time", intent=Intent.REPOSITION))
            s["hero"]["cell"] = 23
            s["hero"]["hp"] -= 1
            guard.check(s, Decision({"type": "cell", "cell": 24}, "ranged: close distance to stop ranged zaps", intent=Intent.REPOSITION))
        s["hero"]["cell"] = 24
        with self.assertRaises(Finished):
            guard.check(s, Decision({"type": "cell", "cell": 23}, "combat: funnel enemies to fight one at a time", intent=Intent.REPOSITION))

    def test_detects_retreat_loot_oscillation_despite_visibility_and_recharge(self):
        guard, s = NavigationLoopGuard(repetitions=3), state()
        with self.assertRaises(Finished) as error:
            for index in range(12):
                s["hero"]["cell"] = 24 if index % 2 == 0 else 23
                s["inventory"][0]["status"] = f"{index % 5}/4"
                s["objects"] = [] if index % 2 else [{"cell": 26, "name": "sewer snake", "sleeping": True}]
                for tile in s["map"]["cells"]:
                    tile["visible"] = bool(index % 2)
                d = Decision({"type": "cell", "cell": 23 if index % 2 == 0 else 24},
                             "loot: collect/open" if index % 2 == 0 else "snake: reposition for surprise/recharge",
                             intent=Intent.LOOT if index % 2 == 0 else Intent.RETREAT)
                guard.check(s, d)
        self.assertIn("No-progress navigation loop", error.exception.reason)

    def test_new_coverage_is_progress_even_on_an_already_visible_map(self):
        guard, s = NavigationLoopGuard(repetitions=2), state()
        for cell in (24, 23, 24, 17, 24, 18, 24, 19):
            s["hero"]["cell"] = cell
            guard.check(s, Decision({"type": "cell", "cell": 25}, "explore: cover remaining floor", intent=Intent.EXPLORE))

    def test_collecting_loot_resets_navigation_loop_count(self):
        guard, s = NavigationLoopGuard(repetitions=2), state()
        for quantity in range(1, 5):
            s["inventory"][0]["quantity"] = quantity
            guard.check(s, Decision({"type": "cell", "cell": 25}, "loot: collect/open", intent=Intent.LOOT))

    def test_healing_waits_and_combat_are_not_navigation_loops(self):
        guard, s = NavigationLoopGuard(repetitions=2), state()
        for _ in range(20):
            guard.check(s, Decision({"type": "wait"}, "recover: natural healing"))
            guard.check(s, Decision({"type": "cell", "cell": 25}, "combat: melee"))


class RunnerTests(unittest.TestCase):

    def test_watch_delay_and_action_budget(self):
        class FakeAPI:
            observation = state()
            def step(self, action):
                return copy.deepcopy(self.observation)
        class FakePolicy:
            target = menu_plan = None
            tutorial_read = False
            def choose(self, observation):
                return Decision({"type": "wait"}, "test")
        with tempfile.TemporaryDirectory() as directory, patch("time.sleep") as sleep:
            result = run(FakeAPI(), FakePolicy(), 2, 0.25, Path(directory) / "run.jsonl")
            self.assertEqual("limit", result["outcome"])
            self.assertEqual(2, result["actions"])
            self.assertEqual(2, sleep.call_count)
            sleep.assert_called_with(0.25)


if __name__ == "__main__":
    unittest.main()
