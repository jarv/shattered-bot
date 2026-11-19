import copy
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from tools.challenge_combat import champion, reach, magic_factor, exposure
from tools.survival_bot import Finished, distance, neighbors, line_clear, run
from tools.player_api import PlayerAPIError
from tools.test_survival_bot import state, fully_known
from tools.test_nine_challenge import verified_policy, selected_mage
from tools.nine_challenge import NineChallengePolicy
from tools.alchemy_tactics import plan_brew, Brew, alchemy_menu
from tools.artifact_tactics import equip_artifact, use_artifact
from tools.resource_tactics import choose_enchantment
from tools.combat_items import unencumbered
from tools.combat_positioning import rinse_ooze
from tools.mage_tactics import prepare_mage, mage_menu, warp_escape
from tools.runestone_tactics import choose_runestone, prepare_intuition, intuition_menu, prepare_inventory_stone, inventory_stone_menu, prepare_mapping, blink_escape
from tools.room_tactics import plan_journey, remaining, safe_tile, prepare_containers, sentry_geometry, sentry_route_safe, awareness_well, crystal_choice
from tools.boss_strategies import create_challenge_strategies, DM300Strategy, YogStrategy, DwarfKingStrategy, BossEscapeBlocked


def item(name, action, **fields):
    return dict(id=name, name=name, actions=[action], **fields)


def ready():
    s, p = fully_known(state()), verified_policy()
    p.update(s)
    return s, p


class ChallengeCombatTests(unittest.TestCase):
    def test_healthy_weak_rat_finish_preserves_charge_for_farther_snake_at_40_percent_bar(self):
        s,p=ready()
        s["hero"]["hp"]=16
        enemies=[{"name":"marsupial rat","cell":25,"health_bar":[16,43]},
                 {"name":"sewer snake","cell":27}]
        s["objects"]=enemies
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual(25,action.action.get("cell"))
        self.assertEqual(1,p.challenge_combat.rat_finishes)

    def test_lone_weakened_ordinary_pursuer_can_receive_two_known_charge_finishing_attempts(self):
        s,p=ready()
        s["inventory"][0]["curse_known"]=True
        s["hero"]["hp"]=6
        p.retreat=lambda *a,**k:None
        enemy={"name":"gnoll scout","cell":25,"health_bar":[19,32]}
        for _ in range(2):self.assertEqual("ZAP",p.challenge_withdrawal(s,[enemy]).action.get("action"))
        with self.assertRaises(Finished):p.challenge_withdrawal(s,[enemy])
        p.challenge_combat.lone_finishing_casts=0
        s["hero"]["hp"]=2
        with self.assertRaises(Finished):p.challenge_withdrawal(s,[enemy])

    def test_invisible_withdrawal_does_not_resume_loot_when_recent_pursuer_leaves_view(self):
        from tools.combat_positioning import invisible_withdrawal
        s,p=ready()
        s["hero"].update(hp=8,buffs=[{"name":"invisible"}])
        p.recent_threats[25]={"name":"hermit crab","cell":25,"observations_ago":1}
        p.paths=lambda *a,**k:{24:None,23:24,22:23,21:22}
        action=invisible_withdrawal(p,s,[],distance,line_clear)
        self.assertEqual("retreat",action.intent)
        self.assertEqual(23,action.action["cell"])

    def test_quiet_healthy_intuition_precedes_optional_corridor_detour(self):
        from unittest.mock import patch
        s,p=ready()
        s["inventory"] += [item("stone of intuition","USE"),item("golden potion","DRINK")]
        with patch("tools.mage_policy.seek_corridor_end",side_effect=AssertionError("identification should precede detour")):
            action=p.challenge_preparation(s,[])
        self.assertEqual("USE",action.action.get("action"))
        self.assertEqual("potion of strength",p.intuition_plan["guess"])
        self.assertFalse(s["inventory"][-1].get("identified",False))

    def test_last_torch_reservation_never_blocks_required_fire_room_staging(self):
        s,p=ready()
        p.tiles[26]["terrain"]=8
        p.tiles[12]["effects"]=["A wall of dense bright green fire, caused by magic; extinguish it."]
        s["inventory"].append(item("torch","LIGHT"))
        self.assertEqual("LIGHT",p.challenge_preparation(s,[]).action.get("action"))

    def test_last_torch_can_be_reserved_after_healthy_floor_one_exit_discovery(self):
        s,p=ready()
        p.tiles[26]["terrain"]=8
        s["inventory"].append(item("torch","LIGHT"))
        action=p.challenge_preparation(s,[])
        self.assertFalse(action and action.action.get("action")=="LIGHT")
        s["depth"]=2
        self.assertEqual("LIGHT",p.challenge_preparation(s,[]).action.get("action"))
    def test_weak_rat_focus_precedes_retreat_that_still_trades_with_multiple_attackers(self):
        s,p=ready()
        p.retreat=lambda *a,**k:p.cell(23,"retreat",intent="retreat")
        enemies=[{"name":"marsupial rat","cell":25,"health_bar":[16,43]},
                 {"name":"marsupial rat","cell":31},{"name":"marsupial rat","cell":17}]
        s["objects"]=enemies
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(25,p.target)
        self.assertEqual(1,p.challenge_combat.boxed_focus_casts)

    def test_legacy_snake_lure_cannot_bypass_rejected_dry_blazing_contact(self):
        from unittest.mock import patch
        from tools.survival_policy import SurvivalPolicy
        s,p=ready()
        enemies=[{"name":"sewer snake","cell":30,"description":"_Blazing Champion_"}]
        with patch.object(SurvivalPolicy,"door_ambush",return_value=p.cell(23,"arbitrary",intent="retreat")):
            self.assertIsNone(p.door_ambush(s,enemies,enemies,kind="snake"))
            p.tiles[23]["terrain"]=29
            self.assertEqual(23,p.door_ambush(s,enemies,enemies,kind="snake").action["cell"])

    def test_isolated_rat_reserves_magic_at_65_percent_but_not_below(self):
        s,p=ready()
        rat={"name":"marsupial rat","cell":25}
        s["objects"]=[rat]
        p.challenge_combat.sight_inputs=4
        s["hero"]["hp"]=13
        self.assertEqual(25,p.best_attack(s,rat).action.get("cell"))
        s["hero"]["hp"]=12
        self.assertEqual("ZAP",p.best_attack(s,rat).action.get("action"))

    def test_final_extinguishing_tick_is_not_misclassified_as_unseen_attack(self):
        import copy
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"burning"}]
        p.update(copy.deepcopy(s))
        s["hero"]["buffs"]=[]
        s["hero"]["hp"]=18
        p.update(s)
        self.assertEqual(0,p.unseen_damage_turns)

    def test_isolated_blazing_water_fallback_can_fight_at_45_percent_but_is_bounded(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        s["hero"]["hp"]=9
        p.tiles[24]["terrain"]=29
        p.paths=lambda *a,**k:{24:None}
        p.retreat=lambda *a,**k:None
        enemies=[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}]
        for _ in range(3):self.assertEqual(25,p.challenge_withdrawal(s,enemies).action.get("cell"))
        with self.assertRaises(Finished):p.challenge_withdrawal(s,enemies)

    def test_public_barrier_counts_for_immediate_critical_reserve_not_unknown_shield(self):
        from tools.challenge_combat import visible_shield
        s,p=ready()
        s["hero"]["hp"]=8
        s["hero"]["buffs"]=[{"name":"barrier","description":"Shielding remaining: _4_."}]
        p.retreat=lambda *a,**k:None
        p.paths=lambda *a,**k:{24:None}
        enemies=[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":31}]
        self.assertEqual(4,visible_shield(s))
        p.challenge_withdrawal(s,enemies)  # 8 HP + 4 public shielding is not critical.
        s["hero"]["buffs"][0]["description"]="A protective barrier."
        self.assertEqual(0,visible_shield(s))
        p.challenge_combat.boxed_casts=2
        with self.assertRaises(Finished):p.challenge_withdrawal(s,enemies)

    def test_protected_water_finishes_weak_blazing_before_exposed_multi_rat_retreat(self):
        s,p=ready()
        s["hero"]["hp"]=15
        p.tiles[24]["terrain"]=29
        enemies=[{"name":"marsupial rat","cell":25,"health_bar":[11,43],"description":"_Blazing Champion_"},
                 {"name":"marsupial rat","cell":31},{"name":"marsupial rat","cell":17}]
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(25,p.target)
        self.assertEqual(1,p.challenge_combat.water_finish_casts)

    def test_boxed_pair_has_bounded_charged_depth_attempt_not_unlimited_critical_trade(self):
        s,p=ready()
        s["hero"]["hp"]=8
        p.retreat=lambda *a,**k:None
        enemies=[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":31}]
        for _ in range(2):self.assertEqual("ZAP",p.challenge_withdrawal(s,enemies).action.get("action"))
        with self.assertRaises(Finished):p.challenge_withdrawal(s,enemies)

    def test_safe_scroll_discovery_can_supply_control_before_full_health_but_not_during_recent_pursuit(self):
        from tools.consumable_tactics import choose_consumable
        s,p=ready()
        s["hero"]["hp"]=14
        s["inventory"].append(item("scroll of ODAL","READ"))
        action=choose_consumable(p,s,[],distance,neighbors)
        self.assertEqual("READ",action.action.get("action"))
        p.tested_scrolls.clear()
        p.consumable_cooldown=0
        p.recent_threats[26]={"name":"gnoll scout","cell":26}
        self.assertIsNone(choose_consumable(p,s,[],distance,neighbors))

    def test_frontier_tie_prefers_known_door_escape_without_overriding_visit_penalty(self):
        s,p=ready()
        p.tiles[25]["terrain"]=6
        paths={24:None,25:24,23:24,22:23,26:25}
        self.assertLess(p.frontier_cost(s,paths,26),p.frontier_cost(s,paths,22))
        p.visits[26]=2
        self.assertGreater(p.frontier_cost(s,paths,26),p.frontier_cost(s,paths,22))

    def test_empty_healthy_mage_can_fight_blazing_from_water_without_assuming_fire_plants(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        p.tiles[24]["terrain"]=29
        enemies=[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"},
                 {"name":"sewer snake","cell":27}]
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual(25,action.action.get("cell"))
        self.assertIn("from water",action.reason)
        self.assertEqual(1,p.challenge_combat.water_melee_attempts)

    def test_isolated_snake_fallback_is_high_health_and_strictly_bounded(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        s["hero"]["hp"]=15
        p.door_ambush=lambda *a,**k:None
        p.retreat=lambda *a,**k:None
        p.snake_reposition=lambda *a,**k:None
        enemies=[{"name":"sewer snake","cell":25}]
        for _ in range(2):self.assertEqual(25,p.snake_combat(s,enemies,"").action.get("cell"))
        with self.assertRaises(Finished):p.snake_combat(s,enemies,"")
        p.snake_melee_attempts.clear()
        s["hero"]["hp"]=14
        with self.assertRaises(Finished):p.snake_combat(s,enemies,"")

    def test_wounded_rat_finish_does_not_force_repeated_melee_with_charges_available(self):
        s,p=ready()
        s["hero"]["hp"]=12
        p.challenge_combat.sight_inputs=5
        enemy={"name":"marsupial rat","cell":25}
        action=p.challenge_withdrawal(s,[enemy])
        self.assertEqual("ZAP",action.action.get("action"))

    def test_healthy_blazing_escape_can_take_bounded_exposed_step_toward_near_water(self):
        s,p=ready()
        p.tiles[22]["terrain"]=29
        p.paths=lambda state,occupied=():{24:None,23:24,22:23}
        enemies=[{"name":"marsupial rat","cell":30,"description":"_Blazing Champion_"}]
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual(23,action.action.get("cell"))
        self.assertEqual("retreat",action.intent)
        self.assertIn("known water",action.reason)

    def test_protected_water_uses_charge_before_repeated_bank_retreat(self):
        s,p=ready()
        p.tiles[24]["terrain"]=29
        enemies=[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"},
                 {"name":"marsupial rat","cell":27}]
        action=p.challenge_withdrawal(s,enemies)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(25,p.target)
        self.assertIn("protected water",action.reason)

    def test_pre_attack_water_route_does_not_cross_stairs_or_locked_room_boundaries(self):
        for terrain in (7,8,21,31):
            s,p=ready()
            p.tiles[22]["terrain"]=29
            p.tiles[23]["terrain"]=terrain
            p.paths=lambda state,occupied=():{24:None,23:24,22:23}
            action=p.challenge_withdrawal(s,[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}])
            self.assertIsNone(action,terrain)

    def test_blazing_encounter_can_stage_two_steps_to_known_water_before_cast(self):
        s,p=ready()
        p.tiles[22]["terrain"]=29
        p.paths=lambda state,occupied=():{24:None,23:24,22:23}
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}])
        self.assertEqual(23,action.action.get("cell"))
        self.assertIn("known water",action.reason)
        self.assertEqual("retreat",action.intent)

    def test_available_backup_barrier_is_allocated_before_combat_preparation(self):
        s,p=ready()
        s["hero"]["talents"]=[{"name":"backup barrier","points":0,"max_points":2,"available":1}]
        action=p.challenge_preparation(s,[{"name":"marsupial rat","cell":25}])
        self.assertEqual({"type":"talent","name":"backup barrier"},action.action)
        s["danger_cells"]=[24]
        self.assertIsNone(p.challenge_preparation(s,[{"name":"marsupial rat","cell":25}]))

    def test_two_adjacent_attackers_need_more_reserve_than_a_lone_pursuer(self):
        s,p=ready()
        s["hero"]["hp"]=8
        s["inventory"][0]["status"]="0/4"
        p.retreat=lambda *args:None
        with self.assertRaisesRegex(Finished,"Critical swarm"):
            p.combat_override(s,[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":31}])

    def test_lone_pursuer_cannot_force_an_exposed_move_at_critical_hp(self):
        s,p=ready()
        s["hero"]["hp"]=2
        p.retreat=lambda *args:None
        with self.assertRaisesRegex(Finished,"Critical pursuit"):
            p.combat_override(s,[{"name":"marsupial rat","cell":25}])

    def test_fleeing_prefers_safe_doorway_over_larger_open_room_gap(self):
        s,p=ready()
        p.tiles[17]["terrain"]=6
        action=p.retreat(s,[{"name":"marsupial rat","cell":26}])
        self.assertEqual(17,action.action.get("cell"))
        for c in (10,16,18):p.tiles[c]["terrain"]=4
        self.assertNotEqual(17,p.retreat(s,[{"name":"marsupial rat","cell":26}]).action.get("cell"))

    def test_critical_burning_does_not_assume_distant_water_is_an_immediate_cure(self):
        s,p=ready()
        s["hero"]["hp"]=2
        s["hero"]["buffs"]=[{"name":"burning"}]
        p.tiles[26]["terrain"]=29
        with self.assertRaisesRegex(Finished,"another dry turn"):
            rinse_ooze(p,s,[],distance,neighbors)
        p.tiles[25]["terrain"]=29
        self.assertEqual(25,rinse_ooze(p,s,[],distance,neighbors).action.get("cell"))

    def test_full_health_blazing_encounter_stages_in_water_before_attacking(self):
        s,p=ready()
        p.tiles[23]["terrain"]=29
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}])
        self.assertEqual(23,action.action.get("cell"))
        self.assertIn("stage water",action.reason)

    def test_empty_staff_lone_rat_can_use_unexposed_door_ambush_instead_of_circling(self):
        s,p=ready()
        s["hero"]["hp"]=9
        s["inventory"][0]["status"]="0/4"
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"rat: reach ambush doorway")
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25}])
        self.assertIn("rat: reach ambush doorway",action.reason)

    def test_greedy_retreat_keeps_door_preference_without_sacrificing_enemy_gap(self):
        s,p=ready()
        p.tiles[23]["terrain"]=6
        p.visits[23]=5
        action=p.retreat(s,[{"name":"marsupial rat","cell":25}])
        self.assertEqual(23,action.action.get("cell"))

    def test_withdrawal_does_not_mask_existing_bounded_wounded_lone_snake_finish(self):
        s,p=ready()
        s["hero"]["hp"]=13
        s["inventory"][0]["status"]="0/4"
        action=p.combat_override(s,[{"name":"sewer snake","cell":25,"health_bar":[8,32]}])
        self.assertEqual(25,action.action.get("cell"))
        self.assertEqual("snake: bounded finishing melee",action.reason)

    def test_withdrawal_prefers_immediate_sight_break_over_distant_cover(self):
        s,p=ready()
        s["hero"]["hp"]=8
        p.paths=lambda state,occupied=():{24:None,23:24,22:23,16:24,8:16}
        with patch("tools.challenge_combat.enemy_line",side_effect=lambda p,e,c,w,l:c not in {16,22}):
            action=p.combat_override(s,[{"name":"gnoll scout","cell":25}])
        self.assertEqual(16,action.action.get("cell"))

    def test_critical_swarm_guard_includes_followup_pursuer_before_last_charge_trade(self):
        s,p=ready()
        s["hero"]["hp"]=5
        s["inventory"][0]["status"]="1/4"
        p.retreat=lambda *args:None
        with self.assertRaisesRegex(Finished,"Critical swarm"):
            p.combat_override(s,[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":26}])

    def test_low_health_lone_snake_can_take_unexposed_doorway_step(self):
        s,p=ready()
        s["hero"]["hp"]=7
        s["inventory"][0]["status"]="0/4"
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"snake: reach ambush doorway")
        action=p.combat_override(s,[{"name":"sewer snake","cell":25}])
        self.assertIn("ambush doorway",action.reason)

    def test_boxed_healthy_rat_group_uses_charge_before_prolonged_damage(self):
        s,p=ready()
        p.retreat=lambda *args:None
        s["objects"]=[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":31}]
        action=p.combat_override(s,s["objects"])
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertIn("boxed ordinary rat",action.reason)

    def test_existing_swarm_ambush_can_continue_at_moderate_health(self):
        s,p=ready()
        s["hero"]["hp"]=11
        p.ambush_plan={"kind":"swarm"}
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"swarm: reach ambush doorway")
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":31}])
        self.assertIn("ambush doorway",action.reason)

    def test_failed_retreat_prefers_evasive_snake_over_unwounded_rat(self):
        s,p=ready()
        s["hero"]["hp"]=11
        p.challenge_combat.last_withdrawal=(13,2)
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25},
                                    {"name":"sewer snake","cell":31}])
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(31,p.target)

    def test_withdrawal_penalizes_repeating_same_directed_edge_not_only_reversal(self):
        s,p=ready()
        s["hero"]["hp"]=8
        p.paths=lambda state,occupied=():{24:None,23:24,22:23,16:24,8:16}
        p.challenge_combat.edges.extend([(24,23)]*4)
        action=p.combat_override(s,[{"name":"gnoll scout","cell":25}])
        self.assertEqual(16,action.action.get("cell"))

    def test_nine_challenge_door_can_be_reused_but_not_indefinitely(self):
        s,p=ready()
        s["hero"]["cell"]=23
        p.tiles={c:{"cell":c,"terrain":5 if c==24 else 1,"visible":True} for c in (22,23,24,25,26)}
        enemy={"name":"sewer snake","cell":26}
        p.ambush_attempts[24]=1
        action=p.door_ambush(s,[enemy],[enemy],kind="snake")
        self.assertEqual(24,action.action.get("cell"))
        p.ambush_plan=None
        p.ambush_attempts[24]=3
        self.assertIsNone(p.door_ambush(s,[enemy],[enemy],kind="snake"))

    def test_ordinary_group_can_take_verified_door_ambush_before_open_room_zap(self):
        s,p=ready()
        calls=[]
        def ambush(*args,**kwargs):
            calls.append(kwargs["kind"])
            return p.cell(23,"swarm: reach ambush doorway")
        p.door_ambush=ambush
        action=p.combat_override(s,[{"name":"sewer snake","cell":26},{"name":"marsupial rat","cell":25}])
        self.assertEqual(["doorway"],calls)
        self.assertIn("ambush doorway",action.reason)

    def test_full_health_group_can_use_nearby_door_before_exposure_timer(self):
        s,p=ready()
        p.tiles[23]["terrain"]=6
        action=p.combat_override(s,[{"name":"gnoll scout","cell":25},{"name":"gnoll scout","cell":32}])
        self.assertIsNotNone(action)
        self.assertEqual(23,action.action.get("cell"))

    def test_wounded_rat_finish_preserves_magic_but_is_bounded(self):
        s,p=ready()
        enemies=[{"name":"marsupial rat","cell":25,"health_bar":[11,43]},
                 {"name":"marsupial rat","cell":31}]
        for _ in range(2):
            self.assertIn("bounded healthy melee",p.combat_override(s,enemies).reason)
        action=p.combat_override(s,enemies)
        self.assertFalse(action and "bounded healthy melee" in action.reason)

    def test_wounded_rat_finish_never_overrides_low_hp_or_champion(self):
        for hp,description in ((8,""),(20,"_Blazing Champion_")):
            s,p=ready()
            s["hero"]["hp"]=hp
            action=p.combat_override(s,[{"name":"marsupial rat","cell":25,"health_bar":[11,43],"description":description}])
            self.assertFalse(action and "bounded healthy melee" in action.reason)

    def test_lone_rat_approach_wait_is_bounded_and_does_not_apply_to_champions(self):
        s,p=ready()
        rat={"name":"marsupial rat","cell":26}
        self.assertEqual("wait",p.combat_override(s,[rat]).action["type"])
        p.challenge_combat.sight_inputs=4
        self.assertIsNone(p.combat_override(s,[rat]))
        p.challenge_combat.sight_inputs=0
        rat["description"]="_Blazing Champion_"
        action=p.combat_override(s,[rat])
        self.assertFalse(action and action.action.get("type")=="wait")

    def test_dry_blazing_retreat_prefers_reachable_water_step(self):
        s,p=ready()
        s["hero"]["hp"]=9
        s["inventory"][0]["status"]="0/4"
        p.tiles[23]["terrain"]=29
        p.paths=lambda state,occupied=():{24:None,23:24,22:23,16:24,8:16}
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}])
        self.assertEqual(23,action.action.get("cell"))

    def test_healthy_lone_adjacent_rat_preserves_magic_for_evasive_pursuers(self):
        s,p=ready()
        enemy={"name":"marsupial rat","cell":25}
        s["objects"]=[enemy]
        self.assertNotEqual("ZAP",p.best_attack(s,enemy).action.get("action"))

    def test_lone_ordinary_snake_prefers_available_door_ambush_to_generic_retreat(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        s["hero"]["hp"]=12
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"snake: reach ambush doorway")
        self.assertIn("ambush doorway",p.combat_override(s,[{"name":"sewer snake","cell":25}]).reason)

    def test_critical_swarm_does_not_spend_last_health_on_snake_zap(self):
        s,p=ready()
        s["hero"]["hp"]=3
        p.retreat=lambda *args: None
        with self.assertRaisesRegex(Finished,"Critical swarm"):
            p.combat_override(s,[{"name":"sewer snake","cell":25},
                                 {"name":"marsupial rat","cell":31}])

    def test_healthy_rat_pursuit_fights_instead_of_circling(self):
        s,p=ready()
        p.challenge_combat.sight_inputs=5
        s["hero"]["hp"]=18
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25},
                                    {"name":"marsupial rat","cell":33}])
        self.assertIn("finish ordinary adjacent rat",action.reason)

    def test_rat_focus_melee_does_not_override_two_adjacent_attackers(self):
        s,p=ready()
        p.challenge_combat.sight_inputs=5
        action=p.combat_override(s,[{"name":"marsupial rat","cell":25},
                                    {"name":"marsupial rat","cell":31}])
        self.assertFalse(action and "finish ordinary adjacent rat" in action.reason)

    def test_mixed_swarm_snake_uses_magic_before_full_health_funnel(self):
        s,p=ready()
        action=p.combat_override(s,[{"name":"sewer snake","cell":26},
                                    {"name":"marsupial rat","cell":25}])
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(26,p.target)

    def test_mixed_swarm_does_not_zap_antimagic_snake(self):
        s,p=ready()
        action=p.combat_override(s,[{"name":"sewer snake","cell":26,"description":"_Antimagic Champion_"},
                                    {"name":"marsupial rat","cell":25}])
        self.assertFalse(action and action.action.get("action")=="ZAP" and p.target==26)

    def test_blazing_pursuit_does_not_leave_water_for_static_two_tile_gap(self):
        s,p=ready()
        s["hero"]["hp"]=5
        s["inventory"][0]["status"]="0/4"
        p.tiles[24]["terrain"]=29
        p.paths=lambda state,occupied=(): {24:None,23:24,22:23}
        enemy={"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}
        with self.assertRaises(Finished):
            p.combat_override(s,[enemy])

    def test_blazing_pursuit_can_retreat_along_water(self):
        s,p=ready()
        s["hero"]["hp"]=5
        s["inventory"][0]["status"]="0/4"
        for c in (24,23,22):
            p.tiles[c]["terrain"]=29
        p.paths=lambda state,occupied=(): {24:None,23:24,22:23}
        enemy={"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}
        self.assertEqual(23,p.combat_override(s,[enemy]).action.get("cell"))

    def test_snake_controller_does_not_bypass_champion_immunity_filter(self):
        s,p=ready()
        enemy={"name":"sewer snake","cell":26,"description":"_Antimagic Champion_"}
        action=p.snake_combat(s,[enemy],"")
        self.assertNotEqual("ZAP",action.action.get("action"))

    def test_critical_empty_retreat_cannot_rely_on_static_distant_endpoint(self):
        s,p=ready()
        s["hero"]["hp"]=3
        s["inventory"][0]["status"]="0/4"
        p.challenge_combat.stalled_withdrawals=2
        p.paths=lambda state, occupied=(): {24:None,23:24,22:23}
        # Giant reach covers the first step but not the static endpoint.
        enemy={"name":"gnoll scout","cell":25,"description":"_Giant Champion_"}
        with self.assertRaises(Finished):
            p.combat_override(s,[enemy])

    def test_unseen_damage_disables_rest_and_seeks_previously_safe_ground(self):
        s,p=ready()
        p.last_safe_cell=24
        hurt=copy.deepcopy(s)
        hurt["hero"].update(cell=25,hp=15)
        p.update(hurt)
        self.assertEqual(0,p.recovery_limit(hurt,False))
        action=p.challenge_preparation(hurt,[])
        self.assertIn("unexplained HP loss",action.reason)
        self.assertEqual(24,action.action.get("cell"))

    def test_group_retreat_prefers_nearby_open_doorway(self):
        s,p=ready()
        s["hero"]["hp"]=9
        p.tiles[23]["terrain"]=6
        action=p.combat_override(s,[{"name":"gnoll scout","cell":25},{"name":"gnoll scout","cell":32}])
        self.assertEqual(23,action.action.get("cell"))

    def test_group_retreat_can_cross_normal_closed_door_into_unexposed_landing(self):
        s,p=ready()
        s["hero"]["hp"]=9
        p.tiles[23]["terrain"]=5
        action=p.combat_override(s,[{"name":"gnoll scout","cell":25},{"name":"gnoll scout","cell":32}])
        self.assertEqual(23,action.action.get("cell") if action else None)

    def test_champion_is_not_treated_as_ordinary_rat_for_charge_reservation(self):
        s,p=ready()
        s["inventory"][0]["status"]="1/4"
        enemy={"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}
        self.assertEqual("ZAP",p.best_attack(s,enemy,reserve=True,reserve_magic=True).action.get("action"))

    def test_empty_staff_can_fight_lone_fast_pursuer_after_failing_retreat(self):
        s, p = ready()
        s["hero"]["hp"] = 12
        s["inventory"][0]["status"] = "0/4"
        p.challenge_combat.last_withdrawal = (14,1)
        enemy = {"name": "sewer crab", "cell": 25, "description": "They are extremely fast."}
        action = p.combat_override(s, [enemy])
        self.assertEqual(25, action.action.get("cell"))
        self.assertIn("lone faster pursuer", action.reason)

    def test_projecting_snake_is_zapped_before_ordinary_escort_funnel(self):
        s, p = ready()
        s["hero"]["hp"] = 13
        enemy = {"name": "sewer snake", "cell": 26, "description": "_Projecting Champion_"}
        action = p.combat_override(s, [enemy, {"name": "albino rat", "cell": 31}])
        self.assertEqual("ZAP", action.action.get("action"))
        self.assertEqual(26, p.target)

    def test_damaging_withdrawal_uses_recharged_magic_on_wounded_pursuer(self):
        s, p = ready()
        s["hero"]["hp"] = 11
        s["inventory"][0]["status"] = "2/4"
        enemies = [{"name": "marsupial rat", "cell": 25, "health_bar": [11,43]},
                   {"name": "marsupial rat", "cell": 31}]
        p.challenge_combat.last_withdrawal = (13, 2)
        action = p.combat_override(s, enemies)
        self.assertEqual("ZAP", action.action.get("action"))
        self.assertEqual(25, p.target)
        self.assertIn("failing withdrawal", action.reason)

    def test_two_nonprogressing_retreats_use_magic_even_without_hp_loss(self):
        s, p = ready()
        s["hero"]["hp"] = 9
        p.challenge_combat.last_withdrawal = (9, 1)
        p.challenge_combat.stalled_withdrawals = 1
        action = p.combat_override(s, [{"name": "marsupial rat", "cell": 25}])
        self.assertEqual("ZAP", action.action.get("action"))

    def test_failing_retreat_does_not_zap_antimagic_champion(self):
        s, p = ready()
        s["hero"]["hp"] = 7
        p.challenge_combat.last_withdrawal = (9, 1)
        enemy = {"name": "marsupial rat", "cell": 25, "description": "_Antimagic Champion_"}
        try:
            action = p.combat_override(s, [enemy])
        except Finished:
            pass
        else:
            self.assertNotEqual("ZAP", action.action.get("action") if action else None)

    def test_breaking_visible_pursuit_resets_retreat_failure_ledger(self):
        s, p = ready()
        p.challenge_combat.last_withdrawal = (10, 1)
        p.challenge_combat.stalled_withdrawals = 2
        p.challenge_combat.observe(p, s, [], line_clear)
        self.assertIsNone(p.challenge_combat.last_withdrawal)
        self.assertEqual(0, p.challenge_combat.stalled_withdrawals)

    def test_elemental_immunity_does_not_waste_frost_wand(self):
        s, p = ready()
        s["inventory"].append(item("wand of frost", "ZAP", status="3/3", identified=True,
                                   description="Deals 20-30 damage."))
        enemy = {"name": "frost elemental", "cell": 26}
        self.assertFalse(p.target_allowed(s["inventory"][-1], enemy))
        self.assertNotEqual("wand of frost", p.best_attack(s, enemy).action.get("id"))

    def test_burning_death_spacing_requires_cover_not_merely_a_static_gap(self):
        s, p = ready()
        enemy = {"name": "gnoll scout", "cell": 25, "description": "_Blazing Champion_", "health_bar": [1,10]}
        action = p.combat_override(s, [enemy])
        self.assertIsNone(action)
        self.assertEqual("ZAP",p.best_attack(s,enemy).action.get("action"))

    def test_fog_is_safe_cover_but_explosive_smoke_is_not(self):
        s, p = ready()
        next(t for t in s["map"]["cells"] if t["cell"] == 24)["effects"] = ["A cloud of thick black smoke is swirling here."]
        p.update(s)
        self.assertTrue(p.walkable(24))
        p.challenge_combat.observe(p, s, [{"name": "gnoll scout", "cell": 26}], line_clear)
        self.assertEqual(0, p.challenge_combat.sight_inputs)
        self.assertFalse(p.harmless_effect("A cloud of superheated smoke is billowing here. Watch out, it's going to explode!"))

    def test_only_public_champion_description_is_used(self):
        e = {"name": "gnoll scout", "cell": 26, "champion": "projecting", "hp": 999}
        self.assertIsNone(champion(e))
        self.assertEqual(1, reach(e))
        e["description"] = "_Projecting Champion_\nExtra melee range."
        self.assertEqual(4, reach(e))

    def test_antimagic_is_not_zapped(self):
        s, p = ready()
        enemy = {"name": "gnoll scout", "cell": 25, "description": "_Antimagic Champion_"}
        self.assertEqual(0, magic_factor(enemy))
        self.assertEqual("cell", p.best_attack(s, enemy).action["type"])

    def test_projecting_and_fast_crab_contribute_exposure_before_adjacent(self):
        s, p = ready()
        enemy = {"name": "gnoll scout", "cell": 26, "description": "_Projecting Champion_"}
        self.assertEqual(1, exposure(p, s, [enemy], 24, distance, line_clear)["melee"])
        enemy = {"name": "sewer crab", "cell": 26, "description": "They are extremely fast."}
        self.assertEqual(1, exposure(p, s, [enemy], 24, distance, line_clear)["fast_pursuit"])

    def test_flies_and_blazing_melee_are_discounted_not_labeled_ordinary(self):
        s, p = ready()
        e = {"name": "swarm of flies", "cell": 25, "description": "_Blazing Champion_"}
        self.assertLess(p.attack_score(s, e, "melee", 10), 1)

    def test_low_hp_empty_staff_never_returns_fatal_melee(self):
        s, p = ready()
        s["hero"]["hp"] = 3
        s["inventory"][0]["status"] = "0/4"
        s["inventory"][0]["actions"] = ["IMBUE"]
        enemies = [{"name": "sewer crab", "cell": 25, "description": "Extremely fast"}]
        p.update(s)
        try:
            action = p.combat_override(s, enemies)
        except Finished as stopped:
            self.assertEqual("blocked", stopped.outcome)
        else:
            self.assertIsNotNone(action)
            self.assertNotEqual(25, action.action.get("cell"))

    def test_visible_exposure_resets_after_door_breaks_line(self):
        s, p = ready()
        e = {"name": "gnoll scout", "cell": 26}
        for _ in range(5):
            p.challenge_combat.observe(p, s, [e], line_clear)
        self.assertEqual(5, p.challenge_combat.sight_inputs)
        p.tiles[25]["terrain"] = 5
        p.challenge_combat.observe(p, s, [e], line_clear)
        self.assertEqual(0, p.challenge_combat.sight_inputs)

    def test_recovery_budget_cannot_reset_when_moving(self):
        s, p = ready()
        p.floor_recovery = 24
        s["hero"]["cell"] = 25
        p.update(s)
        self.assertEqual(0, p.recovery_limit(s, False))
        s["depth"] = 2
        p.update(s)
        self.assertGreater(p.recovery_limit(s, False), 0)


class ExpandedAlchemyTests(unittest.TestCase):
    def test_safe_food_prevents_unnecessary_urgent_meat_stewing(self):
        s, p = ready()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["inventory"] += [item("mystery meat", "EAT"), item("food ration", "EAT")]
        self.assertIsNone(plan_brew(s))
        self.assertEqual(["food ration"], [i["name"] for i in p.food_items(s)])

    def test_starving_mage_can_stew_raw_meat_with_correct_bulk_cost(self):
        s = state()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["inventory"].append(item("mystery meat", "THROW", quantity=3))
        brew = plan_brew(s)
        self.assertEqual(("mystery meat",)*3, brew.ingredients)
        self.assertEqual("stewed meat", brew.output)
        self.assertEqual(2, brew.energy)

    def test_expensive_scroll_falls_back_only_to_declared_public_stone_recipe(self):
        s, p = ready()
        p.alchemy_plan = {"brew": Brew(("scroll of mirror image",), "scroll of prismatic image", "test", 6, "stone of flock"),
                          "stage": "slot", "index": 1, "steps": 0, "reserve": 2}
        s["ui"] = {"texts": [], "energy_text": "Energy 0", "buttons": [{"id": "flock", "label": "Craft: stone of flock x2"}]}
        self.assertEqual("flock", alchemy_menu(p, s).action["id"])

    def test_energy_reserve_requires_rendered_label_not_inventory_guess(self):
        s, p = ready()
        def plan():
            return {"brew": Brew(("potion of purity",), "potion of cleansing", "test", 4),
                    "stage": "slot", "index": 1, "steps": 0, "reserve": 2}
        s["ui"]["buttons"] = [{"id": "craft", "label": "Craft: potion of cleansing"}]
        p.alchemy_plan = plan()
        self.assertEqual("back", alchemy_menu(p, s).action["type"])
        s["ui"]["energy_text"] = "Energy 4+2"
        p.alchemy_plan = plan()
        self.assertEqual("craft", alchemy_menu(p, s).action["id"])
        s["ui"]["energy_text"] = "Energy 4"
        p.alchemy_plan = plan()
        self.assertEqual("back", alchemy_menu(p, s).action["type"])

    def test_spare_recharging_becomes_shock_not_last_recharge(self):
        s = state()
        s["inventory"].append(item("scroll of recharging", "READ", quantity=1))
        self.assertIsNone(plan_brew(s))
        s["inventory"][-1]["quantity"] = 2
        self.assertEqual("stone of shock", plan_brew(s).output)

    def test_known_non_healing_exotic_recipe_and_cost(self):
        s = state()
        s["inventory"].append(item("potion of paralytic gas", "THROW"))
        brew = plan_brew(s)
        self.assertEqual("potion of earthen armor", brew.output)
        self.assertEqual(4, brew.energy)

    def test_urgent_cleansing_does_not_consume_gas_room_protection(self):
        s = state()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["inventory"].append(item("potion of purity", "DRINK"))
        self.assertEqual("potion of cleansing", plan_brew(s).output)
        self.assertIsNone(plan_brew(s, {"gas"}))

    def test_spare_frost_preserves_extinguishing_potion(self):
        s = state()
        s["inventory"].append(item("potion of frost", "THROW"))
        self.assertIsNone(plan_brew(s))
        s["inventory"][-1]["quantity"] = 2
        self.assertEqual("potion of snap freeze", plan_brew(s).output)


class ProgressionTests(unittest.TestCase):
    def test_minion_talent_is_omitted_without_public_wraith_alignment(self):
        s, p = ready()
        priorities = p.talent_priority(s)
        self.assertNotIn("necromancer's minions", priorities)
        self.assertLess(priorities.index("soul eater"), priorities.index("soul siphon"))

    def test_unknown_or_overstrength_robe_invalidates_movement_timing(self):
        s, p = ready()
        robe = item("mage robe", "UNEQUIP", equipped=True,
                    description="This armor blocks 0-2 damage and requires 12 strength.")
        s["inventory"].append(robe)
        self.assertFalse(unencumbered(s))
        robe["identified"] = True
        s["hero"]["strength"] = 10
        self.assertFalse(unencumbered(s))
        s["hero"]["strength"] = 12
        self.assertTrue(unencumbered(s))

    def test_public_enemy_inspection_cache_expires_on_next_world_action(self):
        s, p = ready()
        enemy = {"name": "gnoll scout", "cell": 25}
        self.assertEqual("inspect", p.inspect_enemy(enemy).action["type"])
        s["ui"] = {"texts": ["Gnoll Scout"], "buttons": [{"id": "mark", "label": "Soul Marked"}]}
        self.assertEqual("back", p.menu(s).action["type"])
        self.assertEqual({"soul marked"}, p.inspection_cache["buffs"])
        self.assertGreater(p.attack_score(s, enemy, "melee", 3), 3)
        p.cell(23, "test: world action")
        self.assertIsNone(p.inspection_cache)

    def test_enemy_inspection_does_not_accept_wrong_title(self):
        s, p = ready()
        p.inspect_enemy({"name": "gnoll scout", "cell": 25})
        s["ui"]["texts"] = ["Settings"]
        with self.assertRaises(Finished):
            p.menu(s)

    def test_crown_matches_rendered_warping_beacon_description(self):
        s, p = ready()
        s["inventory"].append(item("Dwarf King's crown", "WEAR"))
        self.assertEqual("WEAR", prepare_mage(p, s).action["action"])
        s["ui"]["buttons"] = [{"id": "warp", "label": "The Mage places a _Warping Beacon_ at his current location."}]
        self.assertEqual("warp", mage_menu(p, s).action["id"])

    def test_warp_return_requires_visible_safe_same_floor_anchor_and_charge(self):
        s, p = ready()
        s["hero"].update(hp=5, cell=8, armor_ability="warp beacon")
        s["inventory"].append(item("mage robe", "ABILITY", equipped=True, status="100%"))
        p.warp_anchor = (1, 0, 40)
        enemies = [{"name": "gnoll scout", "cell": 9}]
        self.assertIsNotNone(warp_escape(p, s, enemies, distance))
        s["ui"] = {"texts": ["Your beacon is currently placed on floor 2."], "buttons": [
            {"id": "go", "label": "teleport to beacon"}, {"id": "cancel", "label": "cancel"}]}
        self.assertEqual("cancel", mage_menu(p, s).action["id"])

    def test_mask_explicitly_selects_warlock_and_confirms_matching_title(self):
        s, p = ready()
        s["inventory"].append(item("Tengu's mask", "WEAR"))
        self.assertEqual("WEAR", prepare_mage(p, s).action["action"])
        s["ui"]["buttons"] = [{"id": "warlock", "label": "The _Warlock_ heals by consuming marked souls."}]
        self.assertEqual("warlock", mage_menu(p, s).action["id"])
        s["ui"] = {"texts": ["Warlock", "Are you sure?"], "buttons": [{"id": "yes", "label": "Yes, I've made my choice."}]}
        self.assertEqual("yes", mage_menu(p, s).action["id"])
        self.assertIsNone(p.mage_plan)

    def test_wrong_subclass_confirmation_is_not_accepted(self):
        s, p = ready()
        p.mage_plan = {"kind": "choice", "choice": "warlock", "stage": "confirm", "steps": 0}
        s["ui"] = {"texts": ["Battlemage"], "buttons": [{"id": "yes", "label": "Yes, I've made my choice."}]}
        self.assertEqual("back", mage_menu(p, s).action["type"])

    def test_imbue_rejects_loss_even_with_preservation_points(self):
        s, p = ready()
        p.mage_plan = {"kind": "imbue", "choice": "wand of frost", "stage": "confirm", "steps": 0}
        s["ui"] = {"texts": ["The old wand will be lost."], "buttons": [
            {"id": "yes", "label": "Yes, I'm sure"}, {"id": "no", "label": "No, I changed my mind"}]}
        self.assertEqual("no", mage_menu(p, s).action["id"])

    def test_warlock_is_still_a_mage_run(self):
        s, p = ready()
        s["hero"].update(name="warlock", hero_class="mage")
        self.assertIsNotNone(p.choose(s))


class ActiveStoneTests(unittest.TestCase):
    def test_shock_can_target_empty_ground_beside_pursuers_without_self_hit(self):
        s, p = ready()
        s["map"] = {"width": 9, "height": 9, "cells": [
            {"cell": c, "terrain": 1, "visible": True} for c in range(81)]}
        s["hero"]["cell"] = 40
        enemies = [{"name": "marsupial rat", "cell": c} for c in (31,32,33)]
        s["objects"] = enemies
        s["inventory"].append(item("stone of shock", "THROW"))
        p.update(s)
        action = choose_runestone(p, s, enemies, distance, neighbors)
        self.assertEqual("stone of shock", action.action["id"])
        self.assertGreater(distance(40, p.target, 9), 2)
        self.assertGreaterEqual(sum(distance(p.target, e["cell"], 9) <= 2 for e in enemies), 2)

    def test_blink_does_not_land_within_projecting_champion_reach(self):
        s, p = ready()
        s["inventory"].append(item("stone of blink", "THROW"))
        enemies = [{"name": "gnoll scout", "cell": 25, "description": "_Projecting Champion_"}]
        self.assertIsNone(blink_escape(p, s, enemies, distance, neighbors))

    def test_detect_magic_and_augmentation_use_explicit_inventory_targets(self):
        s, p = ready()
        s["inventory"] += [item("stone of detect magic", "USE"), item("ethereal chains", "EQUIP")]
        self.assertEqual("USE", prepare_inventory_stone(p, s).action["action"])
        s["ui"]["buttons"] = [{"id": "chains", "label": "ethereal chains"}]
        self.assertEqual("chains", inventory_stone_menu(p, s).action["id"])
        self.assertIsNone(p.inventory_stone_plan)

    def test_clairvoyance_is_once_per_floor_after_real_search_inputs(self):
        s, p = ready()
        s["inventory"].append(item("stone of clairvoyance", "THROW"))
        self.assertIsNone(prepare_mapping(p, s))
        p.searches = 2
        self.assertEqual("THROW", prepare_mapping(p, s).action["action"])
        self.assertIsNone(prepare_mapping(p, s))

    def test_sleep_is_not_wasted_on_boss(self):
        s, p = ready()
        s["hero"]["hp"] = 8
        s["inventory"].append(item("stone of deep sleep", "THROW"))
        enemies = [{"name": "goo", "cell": 25}]
        self.assertIsNone(choose_runestone(p, s, enemies, distance, neighbors))

    def test_shock_keeps_hero_outside_paralysis_radius(self):
        s, p = ready()
        s["hero"]["cell"] = 8
        s["inventory"][0].update(status="0/4", actions=["IMBUE"])
        s["inventory"].append(item("stone of shock", "THROW"))
        enemies = [{"name": "sewer crab", "cell": 32}, {"name": "gnoll scout", "cell": 33}]
        s["objects"] = enemies
        p.update(s)
        action = choose_runestone(p, s, enemies, distance, neighbors)
        self.assertEqual("stone of shock", action.action["id"])
        self.assertGreater(distance(s["hero"]["cell"], p.target, 7), 2)

    def test_intuition_is_only_a_hypothesis_and_attempt_is_bounded(self):
        s, p = ready()
        s["inventory"] += [item("stone of intuition", "USE"), item("crimson potion", "DRINK")]
        self.assertEqual("USE", prepare_intuition(p, s).action["action"])
        s["ui"]["buttons"] = [{"id": "item", "label": "Crimson potion"}]
        self.assertEqual("item", intuition_menu(p, s).action["id"])
        s["ui"]["buttons"] = [{"id": "strength", "label": "Potion of strength"}]
        self.assertEqual("strength", intuition_menu(p, s).action["id"])
        s["ui"]["texts"] = ["Potion of strength"]
        self.assertEqual("strength", intuition_menu(p, s).action["id"])
        self.assertIsNone(prepare_intuition(p, s))
        self.assertFalse(s["inventory"][-1].get("identified", False))


class ProtectedRoomTests(unittest.TestCase):
    def test_crystal_choice_does_not_value_combat_deferred_chest(self):
        s, p = ready()
        for t in s["map"]["cells"]:
            t["terrain"] = 31 if t["cell"] in {17,25} else 1 if t["cell"] in {10,24,26} else 4
        s["keys"] = [{"name": "crystal key", "depth": 1, "quantity": 1}]
        s["objects"] = [{"name": "crystal chest", "cell": 10, "description": "Contains a wand."}]
        p.update(s)
        p.combat_deferred_loot.add(10)
        self.assertIsNone(crystal_choice(p, s, [], neighbors))
        self.assertIn(10, p.loot)

    def test_deferred_crystal_choices_stay_deferred_outside_vision(self):
        s, p = ready()
        for c in (17,25):
            next(t for t in s["map"]["cells"] if t["cell"] == c)["terrain"] = 31
        s["keys"] = [{"name": "crystal key", "depth": 1, "quantity": 1}]
        p.update(s)
        self.assertIsNone(crystal_choice(p, s, [], neighbors))
        self.assertEqual({17,25}, p.deferred_crystal_doors)
        for t in s["map"]["cells"]:
            if t["cell"] in (17,25):
                t["visible"] = False
        p.update(s)
        self.assertTrue({17,25}.issubset(p.optional_locks))

    def test_crystal_key_prefers_observed_strength_not_poisonous_healing(self):
        s, p = ready()
        for t in s["map"]["cells"]:
            t["terrain"] = 31 if t["cell"] in {17,25} else 1 if t["cell"] in {10,24,26} else 4
        s["keys"] = [{"name": "crystal key", "depth": 1, "quantity": 1}]
        s["objects"] = [{"name": "potion of strength", "cell": 10, "top_item": {"name": "potion of strength"}},
                        {"name": "potion of healing", "cell": 26, "top_item": {"name": "potion of healing"}}]
        p.update(s)
        self.assertEqual(17, crystal_choice(p, s, [], neighbors).action["cell"])

    def test_awareness_well_uses_rendered_knowledge_description_not_well_guess(self):
        s, p = ready()
        next(t for t in s["map"]["cells"] if t["cell"] == 25).update(terrain=24, effects=["Power of knowledge radiates from the water of this well."])
        p.update(s)
        self.assertEqual(25, awareness_well(p, s, [], neighbors).action["cell"])
        self.assertIsNone(awareness_well(p, s, [], neighbors))

    def test_sentry_requires_complete_observed_enclosure_and_haste_timing(self):
        s, p = ready()
        for tile in s["map"]["cells"]:
            x, y = tile["cell"] % 7, tile["cell"]//7
            tile["terrain"] = 4 if x in {0,6} or y in {0,6} else 14
            if x in {1,2} and 1 <= y <= 5 and y != 3:
                tile["terrain"] = 1
        next(t for t in s["map"]["cells"] if t["cell"] == 7)["terrain"] = 6
        for c in (22,23,24):
            next(t for t in s["map"]["cells"] if t["cell"] == c)["terrain"] = 25
        for c in (26,29):
            next(t for t in s["map"]["cells"] if t["cell"] == c)["terrain"] = 11
        s["hero"]["cell"] = 15
        s["objects"] = [{"name": "red sentry", "cell": 26}, {"name": "chest", "cell": 29}]
        s["inventory"].append(item("potion of haste", "DRINK"))
        p.update(s)
        region, delay = sentry_geometry(p, s)
        self.assertTrue(region)
        self.assertGreater(delay, 1)
        action = plan_journey(p, s, [], neighbors)
        self.assertEqual("potion of haste", action.action["id"])
        self.assertEqual("sentry", p.room_journey.kind)
        self.assertTrue(sentry_route_safe(p, p.room_journey.route, delay))
        p.tiles.pop(0)
        self.assertEqual((set(), 0), sentry_geometry(p, s))

    def corridor(self):
        s, p = ready()
        for t in s["map"]["cells"]:
            t["terrain"] = 1 if t["cell"] in {23, 24, 26} else 0 if t["cell"] == 25 else 4
        s["objects"] = [{"cell": 26, "name": "chest"}]
        s["inventory"].append(item("potion of levitation", "DRINK"))
        p.update(s)
        return s, p

    def test_flight_plans_complete_known_return_not_blind_crossing(self):
        s, p = self.corridor()
        action = plan_journey(p, s, [], neighbors)
        self.assertEqual("DRINK", action.action["action"])
        self.assertEqual([24, 25, 26], p.room_journey.route)
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns of levitation remaining: 19."}]
        self.assertEqual(25, p.room_journey.advance(p, s, [], neighbors).action["cell"])

    def test_flight_does_not_spend_protection_on_combat_deferred_reward(self):
        s, p = self.corridor()
        p.combat_deferred_loot.add(26)
        self.assertIsNone(plan_journey(p, s, [], neighbors))
        self.assertIsNone(p.room_journey)

    def test_new_combat_deferral_returns_without_collecting_protected_reward(self):
        s, p = self.corridor()
        plan_journey(p, s, [], neighbors)
        p.combat_deferred_loot.add(26)
        s["hero"]["cell"] = 26
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 19."}]
        self.assertEqual(25, p.room_journey.advance(p, s, [], neighbors).action["cell"])
        self.assertEqual("return", p.room_journey.stage)
        self.assertEqual(0, p.room_journey.interactions)
        s["hero"]["cell"] = 24
        p.loot.pop(26)
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))
        self.assertFalse(p.completed_room_rewards)

    def test_no_protection_never_enters_hazard(self):
        s, p = self.corridor()
        plan_journey(p, s, [], neighbors)
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))
        self.assertIsNone(p.room_journey)

    def test_vertigo_invalidates_deterministic_protected_route(self):
        s, p = self.corridor()
        plan_journey(p, s, [], neighbors)
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 19."}, {"name": "vertigo"}]
        with self.assertRaises(Finished):
            p.room_journey.advance(p, s, [], neighbors)

    def test_new_warning_on_return_route_is_not_entered(self):
        s, p = self.corridor()
        plan_journey(p, s, [], neighbors)
        s["hero"]["cell"] = 26
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 19."}]
        s["danger_cells"] = [25]
        with self.assertRaises(Finished):
            p.room_journey.advance(p, s, [], neighbors)

    def test_short_remaining_duration_returns_from_origin_without_entry(self):
        s, p = self.corridor()
        plan_journey(p, s, [], neighbors)
        s["hero"]["buffs"] = [{"name": "levitating", "description": "Turns remaining: 3."}]
        self.assertEqual(3, remaining(s, "levitating"))
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))

    def test_gas_protection_does_not_allow_fire(self):
        s, p = ready()
        p.tiles[25]["effects"] = ["A fire is raging here."]
        self.assertFalse(safe_tile(p, 25, "gas", set()))

    def test_hidden_room_ids_do_not_change_plan(self):
        s, p = self.corridor()
        before = copy.deepcopy(s)
        s["map"]["room_id"] = "safe"
        a = plan_journey(p, s, [], neighbors)
        q = verified_policy()
        q.update(before)
        b = plan_journey(q, before, [], neighbors)
        self.assertEqual(a.action, b.action)


class LaterBossTests(unittest.TestCase):
    def test_tengu_emergency_blink_excludes_entire_observed_bomb_radius(self):
        s, p = ready()
        s["objects"] = [{"name": "smoke bomb", "cell": 25,
                         "description": "Tengu has thrown a smoke bomb here."}]
        s["inventory"].append(item("stone of blink", "THROW"))
        action = p.emergency_transport(s, [])
        self.assertIsNotNone(action)
        self.assertGreater(distance(p.target, 25, 7), 2)

    def test_tengu_staged_escape_uses_rendered_countdown_not_private_timer(self):
        s, p = ready()
        s["depth"] = 10
        s["hero"]["cell"] = 40
        s["map"] = {"width": 9, "height": 9, "cells": [
            {"cell": c, "terrain": 4 if c%9 in {0,8} or c//9 in {0,8} else 1, "visible": True}
            for c in range(81)]}
        s["objects"] = [{"name": "smoke bomb", "cell": 40, "description": "Tengu has thrown a smoke bomb here.",
                         "top_item": {"name": "smoke bomb"}}]
        p.update(s)
        boss = create_challenge_strategies()["tengu"]
        s["ui"]["texts"] = ["3..."]
        action = boss.evade(p, s, [], distance, neighbors)
        self.assertIn("rendered bomb countdown", action.reason)
        self.assertLessEqual(distance(action.action["cell"], 40, 9), 2)
        s["ui"]["texts"] = ["1..."]
        with self.assertRaises(BossEscapeBlocked):
            boss.evade(p, s, [], distance, neighbors)

    def test_trapped_badder_goo_uses_blink_outside_full_blast_not_partial_marker(self):
        s, p = ready()
        s.update(depth=5, danger_cells=[25], boss_health_text="100/120")
        s["objects"] = [{"name": "goo", "cell": 25}]
        s["inventory"].append(item("stone of blink", "THROW"))
        action = p.choose(s)
        self.assertEqual("stone of blink", action.action["id"])
        self.assertGreater(distance(p.target, 25, 7), 2)

    def test_tengu_intermission_is_not_reported_as_final_victory(self):
        s, p = ready()
        boss = create_challenge_strategies()["tengu"]
        s["boss_health_text"] = "100/200"
        self.assertFalse(boss.victory(p, s))
        s["boss_health_text"] = None
        self.assertFalse(boss.victory(p, s))
        s["inventory"].append(item("Tengu's mask", "WEAR"))
        self.assertTrue(boss.victory(p, s))

    def test_rotting_fist_with_public_bleeding_icon_is_not_repeatedly_zapped(self):
        s, p = ready()
        s["depth"] = 25
        p.update(s)
        fist = {"name": "rotting fist", "cell": 26}
        p.inspection_cache = dict(fist, buffs={"bleeding"})
        action = YogStrategy().choose(p, s, [fist], distance, neighbors)
        self.assertNotEqual("ZAP", action.action.get("action"))
        self.assertIn("bleeding", action.reason)

    def test_tengu_bomb_warning_with_no_exit_never_returns_unsafe_move(self):
        s, p = ready()
        s["depth"] = 10
        s["objects"] = [{"name": "smoke bomb", "cell": 24, "description": "Tengu has thrown a smoke bomb here."}]
        boss = create_challenge_strategies()["tengu"]
        with self.assertRaises(BossEscapeBlocked):
            boss.evade(p, s, [], distance, neighbors)

    def test_badder_goo_never_uses_normal_two_move_escape(self):
        s, p = ready()
        s["depth"] = 5
        s["danger_cells"] = [25]
        goo = {"name": "goo", "cell": 25}
        with self.assertRaises(BossEscapeBlocked):
            create_challenge_strategies()["goo"].evade(p, s, [goo], distance, neighbors)

    def test_yog_never_selects_fist_inside_observed_eye_shield_radius(self):
        boss = YogStrategy()
        eye = {"name": "Yog-Dzewa", "cell": 24}
        fist = {"name": "burning fist", "cell": 25}
        self.assertIsNone(boss.target({"map": {"width": 7}}, [eye, fist]))

    def test_all_five_bosses_are_separately_registered(self):
        self.assertEqual({5, 10, 15, 20, 25}, {b.depth for b in create_challenge_strategies().values()})

    def test_dm300_only_targets_publicly_active_pylon_while_immune(self):
        boss = {"name": "DM-300", "cell": 25, "description": "DM-300 cannot be damaged."}
        inactive = {"name": "power pylon", "cell": 26, "description": "currently inactive and immune"}
        active = {"name": "power pylon", "cell": 27, "description": "currently surging with electrical energy"}
        s = dict(objects=[inactive, active])
        self.assertEqual(active, DM300Strategy().target(s, [boss]))
        self.assertIsNone(DM300Strategy().target(dict(objects=[inactive]), [boss]))

    def test_yog_fists_and_king_summons_have_priority(self):
        fist = {"name": "burning fist"}
        self.assertEqual(fist, YogStrategy().target({}, [{"name": "Yog-Dzewa"}, fist]))
        warlock = {"name": "dwarf warlock"}
        self.assertEqual(warlock, DwarfKingStrategy().target({}, [{"name": "King of Dwarves"}, warlock]))

    def test_no_victory_before_observing_boss_bar(self):
        s, p = ready()
        boss = DM300Strategy()
        self.assertFalse(boss.victory(p, s))
        s["boss_health_text"] = "500/500"
        self.assertFalse(boss.victory(p, s))
        s["boss_health_text"] = None
        self.assertTrue(boss.victory(p, s))


class ArtifactBudgetTests(unittest.TestCase):
    def test_faith_armor_still_inscribes_known_safe_cloth(self):
        s, p = ready()
        s["inventory"] += [item("cloth armor", "UNEQUIP", equipped=True, identified=True,
                                description="This armor blocks 0-2 damage and requires 10 strength."),
                           item("arcane stylus", "INSCRIBE")]
        self.assertEqual("INSCRIBE", choose_enchantment(p, s).action["action"])
        self.assertEqual("cloth armor", p.enchant_target)

    def test_chalice_accepts_only_affordable_rendered_range(self):
        s, p = ready()
        s["hero"].update(hp=100, max_hp=100)
        p.artifact_menu = "chalice"
        s["ui"] = {"texts": ["Pricking yourself will deal _3-7 damage_."], "buttons": [{"id": "yes", "label": "Yes, I know what I'm doing"}]}
        self.assertEqual("yes", p.menu(s).action["id"])

    def test_sandals_invoke_inspected_sungrass_effect_without_planting(self):
        s, p = ready()
        s["hero"]["hp"] = 10
        s["inventory"].append(item("sandals of nature +0", "ROOT", equipped=True, identified=True,
                                   description="Imbued with seed of sungrass."))
        action = use_artifact(p, s, [])
        self.assertEqual("ROOT", action.action["action"])
        self.assertEqual(s["hero"]["cell"], p.target)

    def test_sandals_feed_does_not_take_three_seed_brewing_set(self):
        s, p = ready()
        s["inventory"] += [item("sandals of nature +0", "FEED", equipped=True, identified=True),
                           item("seed of blindweed", "THROW", quantity=3)]
        self.assertIsNone(use_artifact(p, s, []))
        s["inventory"][-1]["quantity"] = 4
        self.assertEqual("FEED", use_artifact(p, s, []).action["action"])

    def test_explicit_swap_un_equips_before_equipping(self):
        s, p = ready()
        s["inventory"] += [item("cape of thorns +0", "UNEQUIP", equipped=True, identified=True),
                           item("chalice of blood +0", "UNEQUIP", equipped=True, identified=True),
                           item("ethereal chains +0", "EQUIP", identified=True)]
        action = equip_artifact(p, s)
        self.assertEqual("UNEQUIP", action.action["action"])
        self.assertEqual("ethereal chains +0", p.artifact_swap)

    def test_chalice_unparsed_damage_is_rejected(self):
        s, p = ready()
        p.artifact_menu = "chalice"
        s["ui"] = {"texts": ["Prick?"], "buttons": [{"id": "no", "label": "No, I changed my mind"}]}
        self.assertEqual("no", p.menu(s).action["id"])


    def test_chalice_large_damage_is_rejected_despite_full_hp(self):
        s, p = ready()
        p.artifact_menu = "chalice"
        s["ui"] = {"texts": ["Pricking yourself will deal _7-99 damage_."], "buttons": [{"id": "no", "label": "No, I changed my mind"}]}
        self.assertEqual("no", p.menu(s).action["id"])


class RejectedInputTests(unittest.TestCase):
    def test_new_challenge_state_is_automatically_transactional(self):
        from tools.policy_runtime import Transaction
        p = verified_policy()
        p.future_tactic = {"steps": []}
        p.challenge_window_opened = False
        transaction = Transaction(p)
        p.future_tactic["steps"].append(1)
        p.challenge_window_opened = True
        transaction.rollback()
        self.assertEqual({"steps": []}, p.future_tactic)
        self.assertFalse(p.challenge_window_opened)
    def test_nine_challenge_startup_intent_is_rolled_back_on_rejected_button(self):
        class API:
            observation = selected_mage()
            calls = 0
            def state(self):
                return self.observation
            def step(self, action):
                self.calls += 1
                if self.calls == 1:
                    raise PlayerAPIError(409, "stale observation")
                return self.observation
        p = NineChallengePolicy()
        with tempfile.TemporaryDirectory() as directory:
            result = run(API(), p, 2, 0, Path(directory)/"run.jsonl", bounded=True)
        self.assertEqual(1, result["actions"])
        self.assertEqual(2, result["attempts"])
        self.assertEqual("limit", result["outcome"])


class RoomAuditCoverageTests(unittest.TestCase):
    def test_every_concrete_special_and_secret_room_has_a_documented_policy(self):
        root = Path(__file__).resolve().parents[1]
        import os
        game = Path(os.environ.get("SHATTERED_GAME_DIR", str(root.parent / "shattered-pixel-dungeon")))
        rooms = game/"core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms"
        if not rooms.is_dir():
            self.skipTest("Separate game checkout required for source room audit")
        document = (root/"docs/room-policies.md").read_text()
        for family in ("special", "secret"):
            for source in (rooms/family).glob("*.java"):
                if source.stem not in {"SpecialRoom", "SecretRoom"}:
                    self.assertIn(source.stem, document)
