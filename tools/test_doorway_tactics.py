import unittest
from unittest.mock import patch

from tools.test_challenge_systems import ready
from tools.doorway_tactics import doorway_first,hold_doorway,reset_snake_door
from tools.policy_decision import Intent
from tools.survival_bot import distance,neighbors,line_clear,Finished


class DoorwayFirstTests(unittest.TestCase):
    def test_healthy_doorway_lure_cannot_keep_trading_fast_crab_pursuit(self):
        s,p=ready()
        p.door_ambush=lambda *a,**k:p.cell(17,'reach a doorway',intent=Intent.RETREAT)
        crab={'name':'sewer crab','cell':26,'description':'They are extremely fast.'}
        self.assertIsNone(doorway_first(p,s,[crab],distance,neighbors,line_clear))
        self.assertIn('fast_pursuit_not_reduced',p.planner.report['doorway_first']['violations'])

    def test_doorway_lure_does_not_immediately_reverse_a_sight_break(self):
        s,p=ready()
        p.previous_position=23
        p.last_decision=p.cell(24,'break sight',intent=Intent.RETREAT)
        p.door_ambush=lambda *a,**k:p.cell(23,'reach a doorway',intent=Intent.RETREAT)
        enemy={'name':'marsupial rat','cell':27}
        self.assertIsNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))
        self.assertEqual('decline immediate empty-step lure reversal',p.planner.report['doorway_first']['status'])

    def test_critical_weak_projecting_fly_gets_one_known_charge_not_forced_melee(self):
        s,p=self.corridor()
        s["hero"]["hp"]=4
        s["inventory"][0]["curse_known"]=True
        p.tiles[24]["terrain"]=6
        p.door_ambush=lambda *a,**k:p.cell(24,"entry strike")
        p.retreat=lambda *a,**k:None
        fly={"name":"swarm of flies","cell":24,"health_bar":[6,43],"description":"_Projecting Champion_"}
        action=doorway_first(p,s,[fly],distance,neighbors,line_clear)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(24,p.target)
        with self.assertRaises(Finished):doorway_first(p,s,[fly],distance,neighbors,line_clear)

    def test_held_choke_can_press_nearest_enemy_dart_trap_with_full_waterskin(self):
        s,p=self.hold()
        s["inventory"].append({"id":"skin","name":"waterskin","status":"20/20","actions":["THROW"]})
        p.tiles[18].update(terrain=18,trap="worn dart trap")
        enemy={"name":"marsupial rat","cell":25}
        s["objects"]=[enemy]
        action=hold_doorway(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual("THROW",action.action.get("action"))
        self.assertEqual("skin",action.action["id"])
        self.assertEqual(18,p.target)
        self.assertIsNotNone(p.doorway_hold)
        self.assertIsNotNone(p.trap_payload_return)

    def test_hold_replans_after_two_unconfirmed_empty_snake_melee_strikes(self):
        s,p=self.hold()
        s["inventory"][0]["status"]="0/4"
        p.retreat=lambda *a,**k:None
        enemy={"name":"sewer snake","cell":25}
        for _ in range(2):
            self.assertEqual(25,hold_doorway(p,s,[enemy],distance,neighbors,line_clear).action.get("cell"))
        self.assertIsNone(hold_doorway(p,s,[enemy],distance,neighbors,line_clear))
        self.assertIsNone(p.doorway_hold)

    def test_water_exit_guard_tracks_blazing_followup_not_farther_ordinary_pursuer(self):
        s,p=ready()
        s["hero"]["hp"]=8
        p.tiles[24]["terrain"]=29
        p.door_ambush=lambda *a,**k:p.cell(23,"arbitrary prose",intent=Intent.RETREAT)
        enemies=[{"name":"sewer snake","cell":25},
                 {"name":"marsupial rat","cell":26,"description":"_Blazing Champion_"}]
        action=doorway_first(p,s,enemies,distance,neighbors,line_clear)
        self.assertEqual(23,action.action.get("cell"))

    def test_very_healthy_single_rat_hold_preserves_magic_for_champions_and_snakes(self):
        s,p=self.hold()
        s["hero"]["hp"]=13
        action=hold_doorway(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertEqual(25,action.action.get("cell"))
        s["hero"]["hp"]=12
        action=hold_doorway(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertEqual("ZAP",action.action.get("action"))

    def test_snake_can_be_drawn_off_door_then_door_rearmed_for_surprise(self):
        s,p=self.hold()
        s["hero"]["hp"]=9
        s["inventory"][0]["status"]="0/4"
        p.retreat=lambda *a,**k:p.cell(23,"draw",intent=Intent.RETREAT)
        snake={"name":"sewer snake","cell":25}
        action=hold_doorway(p,s,[snake],distance,neighbors,line_clear)
        self.assertEqual(23,action.action["cell"])
        self.assertIsNotNone(p.snake_door_reset)
        s["hero"]["cell"]=23
        snake["cell"]=24
        for _ in range(8):
            old_pos=s["hero"]["cell"]
            old_draws=p.snake_door_reset.get("draw_steps",0)
            action=reset_snake_door(p,s,[snake],distance,neighbors,line_clear)
            self.assertIsNotNone(action)
            s["hero"]["cell"]=action.action["cell"]
            if p.snake_door_reset and p.snake_door_reset.get("draw_steps",0)>old_draws:
                snake["cell"]=old_pos
            if p.ambush_plan:break
        self.assertIsNone(p.snake_door_reset)
        self.assertIsNotNone(p.ambush_plan)
        self.assertNotEqual(25,s["hero"]["cell"])
        snake["cell"]=25
        action=doorway_first(p,s,[snake],distance,neighbors,line_clear)
        self.assertEqual(25,action.action["cell"])
        self.assertIsNotNone(p.doorway_hold)

    def test_snake_door_reset_abandons_new_flanker_or_damage_budget(self):
        for mode in ("flanker","damage"):
            s,p=self.hold()
            p.snake_door_reset={"depth":1,"door":25,"hp":20,"steps":0,"waits":0}
            enemies=[{"name":"sewer snake","cell":26}]
            if mode=="flanker":enemies.append({"name":"marsupial rat","cell":31})
            else:s["hero"]["hp"]=16
            self.assertIsNone(reset_snake_door(p,s,enemies,distance,neighbors,line_clear))
            self.assertIsNone(p.snake_door_reset)

    def test_empty_staff_snake_hold_can_withdraw_instead_of_repeated_evasive_melee(self):
        s,p=self.hold()
        s["inventory"][0]["status"]="0/4"
        action=hold_doorway(p,s,[{"name":"sewer snake","cell":25}],distance,neighbors,line_clear)
        self.assertEqual("retreat",action.intent)
        self.assertGreater(distance(action.action["cell"],25,7),1)
        self.assertIsNone(p.doorway_hold)

    def test_preparation_retains_cached_lure_when_pursuer_temporarily_leaves_sight(self):
        s,p=self.corridor()
        p.tiles[24]["terrain"]=6
        p.ambush_plan={"kind":"doorway","door":24,"hide":23,"waits":0,"last_enemy":25}
        action=p.challenge_preparation(s,[])
        self.assertEqual("wait",action.action["type"])
        self.assertIsNotNone(p.ambush_plan)
        enemy={"name":"gnoll scout","cell":24}
        action=doorway_first(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual(24,action.action.get("cell"))
        self.assertIsNotNone(p.doorway_hold)

    def test_unexplored_scout_does_not_spend_protected_water_turn_without_exposure_gain(self):
        s,p=ready()
        p.tiles[24]["terrain"]=p.tiles[31]["terrain"]=29
        with patch.object(p,"door_ambush",return_value=None), patch("tools.doorway_tactics.unexplored_door",return_value=(p.cell(31,"arbitrary prose"),None)):
            action=doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertIsNone(action)
        self.assertIn("water_scout_no_gain",p.planner.report["doorway_first"]["violations"])

    def test_doorway_snake_strike_does_not_ignore_new_blazing_flanker(self):
        s,p=self.corridor()
        p.tiles[24]["terrain"]=6
        p.tiles[16]={"cell":16,"terrain":1,"visible":True}
        p.ambush_plan={"kind":"doorway","door":24,"hide":23,"waits":0,"last_enemy":25}
        enemies=[{"name":"sewer snake","cell":24},
                 {"name":"marsupial rat","cell":16,"description":"_Blazing Champion_"}]
        self.assertIsNone(doorway_first(p,s,enemies,distance,neighbors,line_clear))
        self.assertIn("flanked",p.planner.report["doorway_first"]["status"])

    def test_wounded_mage_can_zap_publicly_revealed_mimic_at_the_established_door(self):
        s,p=self.corridor()
        s["hero"].update(hp=10,max_hp=25)
        p.tiles[24]["terrain"]=6
        p.ambush_plan={"kind":"doorway","door":24,"hide":23,"waits":0,"last_enemy":25}
        enemy={"name":"mimic","cell":24,"health_bar":[17,43]}
        action=doorway_first(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(24,p.target)
        self.assertIsNotNone(p.doorway_hold)

    def test_cached_hide_is_revalidated_when_a_flanker_appears(self):
        s,p=self.corridor()
        s["hero"]["cell"]=24
        p.tiles[24]["terrain"]=6
        p.tiles[16]={"cell":16,"terrain":1,"visible":True}
        p.ambush_plan={"kind":"doorway","door":24,"hide":23,"waits":0}
        enemies=[{"name":"marsupial rat","cell":25},{"name":"marsupial rat","cell":16}]
        action=p.door_ambush(s,enemies,enemies,kind="doorway")
        self.assertTrue(action is None or action.action.get("cell")!=23)

    def test_hold_does_not_mask_known_emergency_escape_at_critical_health(self):
        s,p=self.hold()
        s["hero"]["hp"]=5
        s["inventory"].append({"id":"escape","name":"potion of invisibility","actions":["DRINK"]})
        action=hold_doorway(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertEqual("DRINK",action.action.get("action"))
        self.assertIsNone(p.doorway_hold)

    def test_hold_can_read_known_recharging_before_empty_staff_melee(self):
        s,p=self.hold()
        s["inventory"][0]["status"]="0/4"
        s["inventory"].append({"id":"recharge","name":"scroll of recharging","actions":["READ"]})
        action=hold_doorway(p,s,[{"name":"sewer snake","cell":25}],distance,neighbors,line_clear)
        self.assertEqual("READ",action.action.get("action"))
        self.assertIsNotNone(p.doorway_hold)

    def test_healthy_hold_preserves_magic_on_wounded_rat_before_queued_snake(self):
        s,p=self.hold()
        s["hero"]["hp"]=13
        s["objects"]=[{"name":"marsupial rat","cell":25,"health_bar":[6,43]},
                      {"name":"sewer snake","cell":27}]
        action=hold_doorway(p,s,s["objects"],distance,neighbors,line_clear)
        self.assertEqual(25,action.action.get("cell"))
        self.assertNotEqual("ZAP",action.action.get("action"))

    def test_locked_door_is_not_treated_as_a_normal_crossing(self):
        s,p=ready()
        p.tiles[23]["terrain"]=21
        action=doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertIsNone(action)

    def hold(self):
        s,p=ready()
        p.tiles[25]["terrain"]=6
        p.doorway_hold={"depth":1,"door":25,"hide":24,"inputs":0,"quiet":0,"waits":0}
        return s,p

    def test_hold_keeps_fighting_door_enemy_instead_of_new_lure(self):
        s,p=self.hold()
        enemy={"name":"marsupial rat","cell":25}
        action=hold_doorway(p,s,[enemy],distance,neighbors,line_clear)
        self.assertIn("hold established choke",action.reason)
        self.assertEqual(24,s["hero"]["cell"])
        self.assertIsNotNone(p.doorway_hold)

    def test_hold_waits_for_observed_pursuer_and_releases_only_after_quiet_window(self):
        s,p=self.hold()
        action=hold_doorway(p,s,[{"name":"marsupial rat","cell":27}],distance,neighbors,line_clear)
        self.assertEqual("wait",action.action["type"])
        for _ in range(3):self.assertEqual("wait",hold_doorway(p,s,[],distance,neighbors,line_clear).action["type"])
        self.assertIsNone(hold_doorway(p,s,[],distance,neighbors,line_clear))
        self.assertIsNone(p.doorway_hold)

    def test_hold_is_abandoned_when_flanked_or_emergency_moves_hero(self):
        s,p=self.hold()
        self.assertIsNone(hold_doorway(p,s,[{"name":"marsupial rat","cell":31}],distance,neighbors,line_clear))
        self.assertIsNone(p.doorway_hold)
        s,p=self.hold()
        s["hero"]["cell"]=23
        self.assertIsNone(hold_doorway(p,s,[],distance,neighbors,line_clear))

    def test_lure_step_must_reduce_existing_multiple_melee_exposure(self):
        s,p=ready()
        p.door_ambush=lambda *args,**kwargs:p.cell(17,"doorway: reach ambush doorway")
        enemies=[{"name":"marsupial rat","cell":25},{"name":"sewer snake","cell":18}]
        self.assertIsNone(doorway_first(p,s,enemies,distance,neighbors,line_clear))

    def test_observed_lure_damage_is_bounded_before_another_setup(self):
        s,p=ready()
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"doorway: reach ambush doorway")
        enemy={"name":"marsupial rat","cell":25}
        self.assertIsNotNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))
        s["hero"]["hp"]=16
        self.assertIsNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))
        self.assertEqual(4,p.doorway_lure_cost["spent"])
        self.assertIn("damage budget",p.planner.report["doorway_first"]["status"])
        p.ambush_plan=None
        doorway_first(p,s,[],distance,neighbors,line_clear)
        self.assertEqual(0,p.doorway_lure_cost["spent"])

    def test_healthy_scout_avoids_dry_blazing_contact_but_can_step_into_water(self):
        s,p=ready()
        p.door_ambush=lambda *args,**kwargs:p.cell(31,"doorway: reach ambush doorway")
        enemy={"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}
        self.assertIsNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))
        p.tiles[31]["terrain"]=29
        self.assertEqual(31,doorway_first(p,s,[enemy],distance,neighbors,line_clear).action.get("cell"))

    def test_normal_closed_door_is_a_single_safe_move_when_landing_is_unexposed(self):
        s,p=ready()
        p.tiles[23]["terrain"]=5
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"doorway: reach ambush doorway")
        self.assertEqual(23,doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear).action.get("cell"))

    def test_moderately_low_health_scout_cannot_trade_more_melee_damage(self):
        s,p=ready()
        s["hero"]["hp"]=8
        p.door_ambush=lambda *args,**kwargs:p.cell(31,"doorway: reach ambush doorway")
        self.assertIsNone(doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear))
        self.assertIn("low_health_exposed",p.planner.report["doorway_first"]["violations"])

    def test_surprise_does_not_imply_a_safe_kill_at_critical_health(self):
        s,p=ready()
        s["hero"]["hp"]=2
        p.door_ambush=lambda *args,**kwargs:p.cell(25,"doorway: doorway surprise attack")
        p.retreat=lambda *args,**kwargs:None
        with self.assertRaisesRegex(Finished,"not a verified kill"):
            doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)

    def test_critical_entry_strike_can_abandon_for_unexposed_retreat(self):
        s,p=ready()
        s["hero"]["hp"]=4
        p.door_ambush=lambda *a,**k:p.cell(25,"arbitrary prose")
        action=doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertEqual("retreat",action.intent)
        self.assertGreater(distance(action.action["cell"],25,7),1)

    def test_unexplored_far_side_does_not_prevent_opening_observed_door(self):
        s,p=ready()
        s["hero"]["cell"]=23
        p.tiles={c:{"cell":c,"terrain":5 if c==24 else 1,"visible":True} for c in (21,22,23,24)}
        enemy={"name":"marsupial rat","cell":21}
        action=doorway_first(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual(24,action.action.get("cell"))
        self.assertIn("unexplored far side",action.reason)
        self.assertNotIn(25,p.tiles)
        self.assertIsNone(p.ambush_plan)
        self.assertIn((s["depth"],"doorway-scout",24,5),p.room_attempts)

    def test_critical_health_lure_cannot_accept_an_exposed_step(self):
        s,p=ready()
        s["hero"]["hp"]=4
        p.door_ambush=lambda *args,**kwargs:p.cell(31,"doorway: reach ambush doorway")
        self.assertIsNone(doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear))

    def test_lure_does_not_abandon_water_protection_against_blazing_pursuit(self):
        s,p=ready()
        p.tiles[24]["terrain"]=29
        p.door_ambush=lambda *args,**kwargs:p.cell(23,"doorway: reach ambush doorway")
        enemy={"name":"marsupial rat","cell":25,"description":"_Blazing Champion_"}
        self.assertIsNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))

    def corridor(self):
        s,p=ready()
        s["hero"]["cell"]=23
        p.tiles={c:{"cell":c,"terrain":5 if c==24 else 1,"visible":True} for c in (22,23,24,25,26)}
        s["objects"]=[{"name":"marsupial rat","cell":26}]
        return s,p

    def test_lure_happens_before_available_ranged_attack(self):
        s,p=self.corridor()
        action=p.combat_override(s,s["objects"])
        self.assertEqual(24,action.action.get("cell"))
        self.assertEqual("doorway: reach ambush doorway",action.reason)
        self.assertEqual("retreat",action.intent)
        self.assertEqual("lure before ordinary attack",p.planner.report["doorway_first"]["status"])

    def test_cross_hide_and_strike_entering_enemy(self):
        s,p=self.corridor()
        p.combat_override(s,s["objects"])
        s["hero"]["cell"]=24
        s["objects"][0]["cell"]=25
        p.tiles[24]["terrain"]=6
        self.assertEqual(23,p.combat_override(s,s["objects"]).action.get("cell"))
        s["hero"]["cell"]=23
        s["objects"][0]["cell"]=24
        action=p.combat_override(s,s["objects"])
        self.assertEqual("doorway: doorway surprise attack",action.reason)

    def test_no_door_is_an_explicit_failed_attempt_not_fabricated_cover(self):
        s,p=ready()
        enemy={"name":"marsupial rat","cell":25}
        self.assertIsNone(doorway_first(p,s,[enemy],distance,neighbors,line_clear))
        self.assertIn("no viable",p.planner.report["doorway_first"]["status"])

    def test_danger_and_boss_keep_dedicated_arbitration(self):
        s,p=self.corridor()
        s["danger_cells"]=[23]
        self.assertIsNone(doorway_first(p,s,s["objects"],distance,neighbors,line_clear))
        s["danger_cells"]=[]
        s["objects"][0]["name"]="goo"
        self.assertIsNone(doorway_first(p,s,s["objects"],distance,neighbors,line_clear))

    def test_does_not_wait_while_adjacent_enemy_can_attack(self):
        s,p=ready()
        p.door_ambush=lambda *args,**kwargs:p.decision({"type":"wait"},"doorway: await doorway ambush")
        action=doorway_first(p,s,[{"name":"marsupial rat","cell":25}],distance,neighbors,line_clear)
        self.assertIsNone(action)
        self.assertIn("unsafe",p.planner.report["doorway_first"]["status"])
