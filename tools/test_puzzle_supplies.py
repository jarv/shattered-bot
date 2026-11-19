import unittest

from tools.test_challenge_systems import ready, item
from tools.survival_bot import distance, neighbors, Finished
from tools.puzzle_supplies import demands, prepare_supplies, recover_probe, identify_menu, safe_test_bank
from tools.drop_tactics import fall_budget, prepare_drop, drop_menu, recover_drop
from tools.alchemy_tactics import plan_brew
from tools.room_tactics import plan_journey


def puzzle():
    s,p=ready()
    for tile in s["map"]["cells"]:
        x,y=tile["cell"]%7,tile["cell"]//7
        tile["terrain"]=4 if x in {0,6} or y in {0,6} else 0 if x==4 else 1
        if tile["cell"]==23:
            tile["terrain"]=29
    s["hero"]["cell"]=23
    s["objects"]=[{"name":"chest","cell":26}]
    s["inventory"].append(item("crimson potion","DRINK"))
    p.update(s)
    return s,p


class PuzzleIdentificationTests(unittest.TestCase):
    def test_required_fire_recovery_funds_missing_health_before_test_not_only_final_five_percent(self):
        s,p=ready()
        s["hero"].update(hp=16,max_hp=25)
        s["inventory"] += [item("ration of food","EAT"),item("crimson potion","DRINK")]
        p.tiles[26]["effects"]=["A wall of dense bright green fire, caused by magic; extinguish it."]
        p.floor_recovery=24
        p.challenge_preparation(s,[])
        self.assertEqual(114,p.food_recovery_until)
        self.assertEqual(114,p.recovery_limit(s,False))
        s["inventory"]=[i for i in s["inventory"] if i["name"]!="ration of food"]
        self.assertEqual(0.95,p.recovery_target(s))
        p.floor_recovery=114
        self.assertEqual(0,p.recovery_limit(s,False))

    def test_hazard_escape_search_reroutes_around_forbidden_barrier_buffer(self):
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"burning"}]
        p.tiles={c:{"cell":c,"terrain":1,"visible":True,"effects":["A fire is raging here."] if c==24 else []}
                 for c in (23,24,25)}
        p.room_blocked=p.room_skipped={24}
        p.fire_buffer={23}
        action=p.escape_special_room(s)
        self.assertEqual(25,action.action.get("cell"))

    def test_burning_escape_can_cross_ignition_buffer_but_never_magical_barrier_buffer(self):
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"burning"}]
        for t in s["map"]["cells"]:
            if t["cell"]==32:t["effects"]=["A fire is raging here."]
            if t["cell"]==25:t["terrain"]=2
        p.update(s)
        self.assertTrue(p.walkable(25))
        p.fire_buffer.add(25)
        self.assertFalse(p.walkable(25))

    def test_natural_recovery_never_waits_through_burning_damage(self):
        from tools.policy_runtime import Context
        from tools.policy_nodes import preparation_and_recovery
        s,p=ready()
        s["hero"].update(hp=10,buffs=[{"name":"burning"}])
        self.assertIsNone(preparation_and_recovery(Context(p,s)))
    def test_visible_fire_blocks_adjacent_flammable_ground_but_not_stone_or_water(self):
        s,p=ready()
        for tile in s["map"]["cells"]:
            if tile["cell"]==32:tile["effects"]=["A fire is raging here."]
            if tile["cell"]==25:tile["terrain"]=2
            if tile["cell"]==24:tile["terrain"]=29
        p.update(s)
        self.assertFalse(p.walkable(25))
        self.assertTrue(p.walkable(24))
        self.assertTrue(p.walkable(26))

    def test_active_burning_barrier_blocks_adjacent_tiles_until_publicly_extinguished(self):
        s,p=ready()
        barrier=next(t for t in s["map"]["cells"] if t["cell"]==26)
        barrier["effects"]=["A wall of dense bright green fire, caused by magic; extinguish it."]
        p.update(s)
        self.assertFalse(p.walkable(25))
        self.assertFalse(p.walkable(18))
        self.assertTrue(p.walkable(24))  # One intervening square for potion testing.
        barrier["effects"]=[]
        p.update(s)
        self.assertTrue(p.walkable(25))

    def test_chilled_probe_escapes_through_public_cold_air_instead_of_waiting_blindly(self):
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"chilled"}]
        p.puzzle_probe={"depth":s["depth"],"kind":"frost","turns":0}
        for c in (24,23,25,17,31,16,18,30,32):
            p.tiles[c]["effects"]=["The air is unnaturally frigid here."]
        p.paths=lambda *a,**k:{24:None}
        action=recover_probe(p,s,[],distance,neighbors)
        self.assertEqual("cell",action.action["type"])
        self.assertEqual("retreat",action.intent)
        self.assertIn(action.action["cell"],(23,25,17,31,16,18,30,32))

    def test_fire_puzzle_recovery_target_matches_the_drink_reserve(self):
        s,p=ready()
        self.assertEqual(0.8,p.recovery_target(s))
        p.tiles[26]["effects"]=["A wall of magical fire."]
        s["inventory"] += [item("ration of food","EAT"),item("crimson potion","DRINK")]
        self.assertEqual(0.95,p.recovery_target(s))
        s["hero"]["hp"]=18
        s["hero"]["max_hp"]=20
        self.assertLess(s["hero"]["hp"]/s["hero"]["max_hp"],p.recovery_target(s))

    def test_full_health_hungry_fire_solver_can_eat_one_bounded_puzzle_meal(self):
        s,p=self.frost_bank()
        s["hero"]["buffs"]=[{"name":"hungry"}]
        s["inventory"].append(item("ration of food","EAT"))
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("EAT",action.action.get("action"))
        self.assertIn("puzzle-backed",action.reason)
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))
        self.assertFalse(p.puzzle_drinks)

    def test_fire_puzzle_can_budget_food_backed_recovery_without_relaxing_drink_hp(self):
        s,p=ready()
        s["hero"]["hp"]=18
        s["inventory"] += [item("ration of food","EAT"),item("crimson potion","DRINK")]
        p.tiles[26]["effects"]=["A wall of magical fire."]
        p.floor_recovery=24
        self.assertEqual(64,p.recovery_limit(s,False))
        self.assertEqual(0,p.recovery_limit(s,True))
        p.floor_recovery=64
        self.assertEqual(0,p.recovery_limit(s,False))

    def test_safe_known_identify_does_not_require_unknown_drink_health_reserve(self):
        s,p=puzzle()
        s["hero"]["hp"]=12
        s["inventory"].append(item("scroll of identify","READ"))
        self.assertEqual("READ",prepare_supplies(p,s,[],distance,neighbors).action.get("action"))
        self.assertFalse(p.puzzle_drinks)

    def frost_bank(self):
        s,p=ready()
        p.tiles[26].update(terrain=14,visible=True,effects=["A wall of dense bright green fire, caused by magic; extinguish it."])
        s["inventory"].append(item("crimson potion","DRINK"))
        p.paths=lambda state,occupied=():{24:None}
        return s,p

    def test_frost_hypothesis_can_be_drunk_with_one_intervening_square(self):
        s,p=self.frost_bank()
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("DRINK",action.action.get("action"))
        self.assertIn("one intervening square",action.reason)
        self.assertEqual("frost",p.puzzle_probe["kind"])
        self.assertIsNone(p.potion_probe_permit)
        self.assertFalse(s["inventory"][-1].get("identified",False))
        self.assertTrue(any(d.kind=="frost" for d in demands(p,s,distance)))
        recover_probe(p,s,[],distance,neighbors)
        self.assertTrue(any(d.kind=="frost" for d in demands(p,s,distance)))

    def test_frost_fallback_rejects_adjacent_fire_low_hp_enemies_and_exhausted_budget(self):
        for mode in ("adjacent","hp","enemy","budget","flammable","loot"):
            s,p=self.frost_bank()
            enemies=[]
            if mode=="adjacent":
                p.tiles[25]["effects"]=p.tiles[26].pop("effects")
            elif mode=="hp":s["hero"]["hp"]=10
            elif mode=="enemy":enemies=[{"name":"marsupial rat","cell":32}]
            elif mode=="budget":p.puzzle_drinks={(1,"golden potion"),(1,"silver potion")}
            elif mode=="flammable":p.tiles[23]["terrain"]=2
            elif mode=="loot":p.loot[23]={"name":"ration of food"}
            self.assertIsNone(prepare_supplies(p,s,enemies,distance,neighbors),mode)

    def test_identify_still_precedes_barrier_adjacent_frost_drinking(self):
        s,p=self.frost_bank()
        s["inventory"].append(item("scroll of identify","READ"))
        self.assertEqual("READ",prepare_supplies(p,s,[],distance,neighbors).action.get("action"))

    def test_remembered_fire_is_revisited_before_visible_only_potion_staging(self):
        s,p=self.frost_bank()
        p.tiles[26]["visible"]=False
        s["hero"]["cell"]=8
        p.paths=lambda state,occupied=():{8:None,16:8,24:16}
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("cell",action.action["type"])
        self.assertIn("revisit observed fire",action.reason)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)

    def test_long_protected_route_budgets_remaining_trip_not_original_full_trip(self):
        s,p=ready()
        s["map"]={"width":11,"height":5,"cells":[
            {"cell":c,"terrain":(1 if c in {12,19} else 0 if 13<=c<=18 else 4),"visible":True}
            for c in range(55)]}
        s["hero"]["cell"]=12
        s["hero"]["buffs"]=[{"name":"levitating","description":"Turns remaining: 19."}]
        s["objects"]=[{"name":"chest","cell":19}]
        p.update(s)
        self.assertEqual(13,plan_journey(p,s,[],neighbors).action.get("cell"))
        s["hero"]["cell"]=13
        s["hero"]["buffs"][0]["description"]="Turns remaining: 18."
        self.assertEqual(14,p.room_journey.advance(p,s,[],neighbors).action.get("cell"))

    def test_floor_test_budget_prevents_unbounded_experimentation(self):
        s,p=puzzle()
        p.puzzle_drinks={(s["depth"],"silver potion"),(s["depth"],"azure potion")}
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))

    def test_room_supply_is_only_hypothesis_and_does_not_read_hidden_room_ids(self):
        s,p=puzzle()
        before=demands(p,s,distance)
        s["map"]["room_id"]="frost chamber"
        s["inventory"][-1]["hidden_type"]="healing"
        self.assertEqual(before,demands(p,s,distance))
        self.assertIn("potion of levitation",[d.potion for d in before])
        self.assertFalse(s["inventory"][-1].get("identified",False))

    def test_prefers_identify_to_rune_or_drinking(self):
        s,p=puzzle()
        s["inventory"] += [item("scroll of identify","READ"),item("stone of intuition","USE")]
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("scroll of identify",action.action["id"])
        self.assertIsNone(p.puzzle_probe)
        s["ui"]["buttons"]=[{"label":"Crimson potion","id":"candidate"}]
        self.assertEqual("candidate",identify_menu(p,s).action["id"])

    def test_rune_guess_is_driven_by_room_not_strength_default(self):
        s,p=puzzle()
        s["inventory"].append(item("stone of intuition","USE"))
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("USE",action.action["action"])
        self.assertEqual("potion of levitation",p.intuition_plan["guess"])

    def test_unknown_test_is_authorized_once_on_safe_water_only(self):
        s,p=puzzle()
        potion=s["inventory"][-1]
        self.assertTrue(safe_test_bank(p,s,23,distance,neighbors))
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("DRINK",action.action["action"])
        self.assertIn("unconfirmed",action.reason)
        self.assertIsNone(p.potion_probe_permit)
        self.assertFalse(p.item_action_allowed(potion,"DRINK"))
        self.assertIsNotNone(p.puzzle_probe)

    def test_no_unsafe_ground_or_healthy_threshold_bypass(self):
        s,p=puzzle()
        for tile in p.tiles.values():
            if tile["terrain"]==29:
                tile["terrain"]=1
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))
        p.tiles[23]["terrain"]=29
        s["hero"]["hp"]=10
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))

    def test_flame_candidate_is_not_drunk_and_frost_needs_safe_staging(self):
        s,p=ready()
        p.tiles[26].update(terrain=13,visible=True)
        s["inventory"].append(item("crimson potion","DRINK"))
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))
        p.tiles[26].update(terrain=14,effects=["A wall of magical fire."])
        p.tiles[24]["plant"]="firebloom"
        p.paths=lambda state,occupied=():{24:None}
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))

    def test_success_requires_actual_protection_not_predicted_identity(self):
        s,p=puzzle()
        prepare_supplies(p,s,[],distance,neighbors)
        # A strength potion or failed hypothesis is not flight protection.
        self.assertIsNone(recover_probe(p,s,[],distance,neighbors))
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(plan_journey(p,s,[],neighbors))

    def test_observed_flight_from_a_test_is_reused_without_another_drink(self):
        s,p=puzzle()
        s["inventory"]=[i for i in s["inventory"] if "potion" not in i["name"]]
        s["hero"]["buffs"]=[{"name":"levitating","description":"Turns remaining: 19."}]
        action=plan_journey(p,s,[],neighbors)
        self.assertIsNotNone(action)
        self.assertEqual("cell",action.action["type"])
        self.assertIn("protected route",action.reason)

    def test_probe_complication_cannot_chain_experiments_or_ignore_health(self):
        s,p=puzzle()
        prepare_supplies(p,s,[],distance,neighbors)
        s["hero"]["buffs"]=[{"name":"poisoned"}]
        action=recover_probe(p,s,[],distance,neighbors)
        self.assertEqual("wait",action.action["type"])
        self.assertIsNone(prepare_supplies(p,s,[],distance,neighbors))
        s["hero"]["hp"]=5
        with self.assertRaises(Finished):
            recover_probe(p,s,[],distance,neighbors)


class PlannedDropTests(unittest.TestCase):
    def test_mageroyal_artifact_effect_can_cleanse_unexpected_landing_bleed(self):
        s,p=self.ledge()
        p.drop_plan={"depth":1,"stage":"confirm","steps":1,"bank":24,"cell":25}
        s["depth"]=2
        s["hero"]["buffs"]=[{"name":"bleeding"}]
        s["inventory"].append(item("sandals of nature","ROOT",equipped=True,
            description="Imbued with seed of mageroyal."))
        self.assertEqual("ROOT",recover_drop(p,s,[],distance,neighbors).action.get("action"))

    def test_drop_needs_charged_anti_wraith_reserve_for_unknown_landing(self):
        s,p=self.ledge()
        s["hero"]["buffs"]=[{"name":"feather fall","description":"Turns remaining: 49."}]
        s["inventory"][0]["status"]="0/4"
        self.assertIsNone(prepare_drop(p,s,[],distance,neighbors))

    def ledge(self):
        s,p=ready()
        s["hero"].update(strength=10,hp=20,max_hp=20)
        next(t for t in s["map"]["cells"] if t["cell"]==25).update(terrain=0,name="Distant well")
        p.update(s)
        return s,p

    def test_fall_estimate_includes_upfront_and_rough_bleeding_not_a_guarantee(self):
        budget=fall_budget({"hp":20,"max_hp":20})
        self.assertEqual(10,budget["direct_upper"])
        self.assertEqual(2,budget["initial_bleed_upper"])
        self.assertEqual(2,budget["rough_after_bleed"])

    def test_unprotected_drop_is_not_authorized_by_raw_seed_or_healing_potion(self):
        s,p=self.ledge()
        s["inventory"] += [item("seed of mageroyal","PLANT"),item("potion of healing","DRINK")]
        self.assertIsNone(prepare_drop(p,s,[],distance,neighbors))
        self.assertIsNone(p.drop_plan)

    def test_feather_recipe_uses_levitation_and_ten_energy(self):
        s,p=self.ledge()
        s["inventory"].append(item("potion of levitation","DRINK"))
        recipe=plan_brew(s,{"fall"})
        self.assertEqual("elixir of feather fall",recipe.output)
        self.assertEqual(10,recipe.energy)
        self.assertIsNone(plan_brew(s,{"fall","flight"}))

    def test_feather_is_used_then_observed_before_requesting_jump(self):
        s,p=self.ledge()
        s["inventory"].append(item("elixir of feather fall","DRINK"))
        self.assertEqual("DRINK",prepare_drop(p,s,[],distance,neighbors).action.get("action"))
        self.assertIsNone(p.drop_plan)
        s["hero"]["buffs"]=[{"name":"feather fall","description":"Turns remaining: 49."}]
        self.assertEqual(25,prepare_drop(p,s,[],distance,neighbors).action.get("cell"))
        self.assertEqual("confirm",p.drop_plan["stage"])

    def test_cleansing_can_prevent_bleed_but_cannot_erase_direct_damage_budget(self):
        s,p=self.ledge()
        s["inventory"].append(item("potion of cleansing","DRINK"))
        self.assertEqual("DRINK",prepare_drop(p,s,[],distance,neighbors).action.get("action"))
        s["hero"]["hp"]=12
        self.assertIsNone(prepare_drop(p,s,[],distance,neighbors))

    def test_jump_confirmation_revalidates_ledge_and_rendered_buff(self):
        s,p=self.ledge()
        s["hero"]["buffs"]=[{"name":"feather fall","description":"Turns remaining: 49."}]
        prepare_drop(p,s,[],distance,neighbors)
        s["ui"]={"texts":["Do you really want to jump into the chasm?"],"buttons":[
            {"id":"yes","label":"Yes, I know what I'm doing"},{"id":"no","label":"No, I changed my mind"}]}
        self.assertEqual("yes",drop_menu(p,s).action["id"])
        s["hero"]["buffs"]=[]
        self.assertEqual("no",drop_menu(p,s).action["id"])

    def test_normal_chasm_is_not_assumed_to_lead_to_well(self):
        s,p=self.ledge()
        p.tiles[25]["name"]="Chasm"
        s["hero"]["buffs"]=[{"name":"feather fall","description":"Turns remaining: 49."}]
        self.assertIsNone(prepare_drop(p,s,[],distance,neighbors))

    def test_landing_bleed_uses_known_cleansing_before_loot(self):
        s,p=self.ledge()
        p.drop_plan={"depth":1,"stage":"confirm","steps":1,"bank":24,"cell":25}
        s["depth"]=2
        s["hero"]["buffs"]=[{"name":"bleeding"}]
        s["inventory"].append(item("potion of cleansing","DRINK"))
        action=recover_drop(p,s,[],distance,neighbors)
        self.assertEqual("potion of cleansing",action.action["id"])

    def test_no_landing_bleed_cure_is_invented_from_raw_seed(self):
        s,p=self.ledge()
        p.drop_plan={"depth":1,"stage":"confirm","steps":1,"bank":24,"cell":25}
        s["depth"]=2
        s["hero"]["buffs"]=[{"name":"bleeding"}]
        s["inventory"].append(item("seed of mageroyal","PLANT"))
        with self.assertRaises(Finished):
            recover_drop(p,s,[],distance,neighbors)
