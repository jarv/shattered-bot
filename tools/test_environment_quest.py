import unittest

from tools.test_challenge_systems import ready, item
from tools.survival_bot import distance, neighbors, line_clear, Finished
from tools.environment_tactics import trigger_trap, use_bomb, observe_bombs, payload, recover_trap_payload
from tools.ghost_quest import visit_ghost, quest_menu, quest_combat, observe_quest
from tools.resource_tactics import choose_well
from tools.room_tactics import investigate_suspect_container, charge_suspect_container


class EnvironmentTests(unittest.TestCase):
    def test_full_waterskin_is_reusable_trap_weight_and_retrieved_only_after_disarm(self):
        s,p=self.setup_arena()
        skin=dict(item("waterskin","THROW"),status="20/20")
        s["inventory"]=[skin]
        p.tiles[43].update(terrain=18,trap="worn dart trap")
        enemy={"name":"gnoll scout","cell":34}
        s["objects"]=[enemy]
        action=trigger_trap(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual(skin["id"],action.action["id"])
        self.assertEqual("20/20",skin["status"])
        s["inventory"]=[]
        self.assertIsNone(recover_trap_payload(p,s,[enemy]))
        self.assertIsNone(recover_trap_payload(p,s,[]))
        p.tiles[43]["terrain"]=19
        p.loot[43]={"name":"waterskin","top_item":skin}
        self.assertEqual("loot",recover_trap_payload(p,s,[]).intent)
        s["inventory"]=[skin]
        self.assertIsNone(recover_trap_payload(p,s,[]))
        self.assertIsNone(p.trap_payload_return)

    def test_unretrievable_trap_payload_keeps_floor_unfinished(self):
        from unittest.mock import patch
        from tools.survival_policy import SurvivalPolicy
        from tools.policy_decision import Decision, Intent
        s,p=self.setup_arena()
        p.trap_payload_return={"cell":43,"name":"waterskin","depth":1,"steps":0}
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":25},"arbitrary",Intent.DESCEND)):
            with self.assertRaisesRegex(Finished,'Observed loot incomplete'):p.choose(s)
        self.assertIsNotNone(p.trap_payload_return)
        self.assertFalse(p.descent_counts_as_clear())

    def test_surplus_food_can_fund_one_bounded_safe_recovery_meal(self):
        s,p=self.setup_arena()
        s["hero"].update(hp=10,buffs=[{"name":"hungry"}])
        s["inventory"] += [item("ration of food","EAT"),item("pasty","EAT")]
        p.floor_recovery=24
        self.assertEqual("EAT",p.challenge_preparation(s,[]).action.get("action"))
        self.assertEqual(74,p.food_recovery_until)
        self.assertEqual(74,p.recovery_limit(s,True))
        p.floor_recovery=74
        self.assertEqual(0,p.recovery_limit(s,True))

    def test_required_suspect_charge_wait_is_bounded_and_rechecks_starvation(self):
        s,p=self.setup_arena()
        s["inventory"][0]["status"]="2/4"
        p.loot[44]={"name":"Crystal chest","description":"It feels off; opening is a bad idea."}
        s["hero"]["buffs"]=[{"name":"starving"}]
        self.assertIsNone(charge_suspect_container(p,s,[]))
        s["hero"]["buffs"]=[{"name":"hungry"}]
        for _ in range(40):
            action=charge_suspect_container(p,s,[])
            self.assertEqual("recover",action.intent)
        self.assertIsNone(charge_suspect_container(p,s,[]))

    def test_unlit_suspicious_chest_staging_uses_two_square_reveal_range(self):
        s,p=self.setup_arena()
        p.tiles[39]["terrain"]=6
        p.loot[44]={"name":"Crystal chest","cell":44,"description":"It feels off; opening is a bad idea."}
        p.tiles[44]["visible"]=False
        action=investigate_suspect_container(p,s,[],distance)
        self.assertIsNotNone(action)
        self.assertNotEqual("ZAP",action.action.get("action"))
        # Follow the ordinary movement outputs until the public target is in range.
        for _ in range(8):
            if action.action.get("action")=="ZAP":break
            s["hero"]["cell"]=action.action["cell"]
            p.tiles[44]["visible"]=distance(s["hero"]["cell"],44,9)<=2
            action=investigate_suspect_container(p,s,[],distance)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(2,distance(s["hero"]["cell"],44,9))

    def test_required_room_meal_never_masks_threats_burning_or_its_own_budget(self):
        for mode in ("enemy","burning","used"):
            s,p=self.setup_arena()
            s["hero"].update(hp=19,max_hp=30,buffs=[{"name":"hungry"}])
            s["inventory"].append({"id":"food","name":"pasty","actions":["EAT"]})
            p.loot[44]={"name":"Crystal chest","description":"It feels off; opening it is a bad idea."}
            enemies=[{"name":"marsupial rat","cell":41}] if mode=="enemy" else []
            if mode=="burning":s["hero"]["buffs"].append({"name":"burning"})
            if mode=="used":p.room_attempts.add((s["depth"],"suspect-room-meal"))
            action=p.challenge_preparation(s,enemies)
            self.assertFalse(action and action.action.get("action")=="EAT",mode)
            p.floor_recovery=104
            self.assertEqual(0,p.recovery_limit(s,False))

    def test_required_suspect_room_can_fund_recovery_without_lowering_attack_reserve(self):
        s,p=self.setup_arena()
        s["hero"].update(hp=19,max_hp=30)
        s["hero"]["buffs"]=[{"name":"hungry"}]
        s["inventory"].append({"id":"food","name":"pasty","actions":["EAT"]})
        p.loot[44]={"name":"Crystal chest","description":"It feels off; opening it is a bad idea."}
        self.assertEqual(0.9,p.recovery_target(s))
        self.assertEqual(104,p.recovery_limit(s,False))
        self.assertEqual("EAT",p.challenge_preparation(s,[]).action.get("action"))
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))

    def test_suspicious_crystal_container_requires_public_warning_charges_and_safe_exits_not_door_block(self):
        s,p=self.setup_arena()
        s["hero"]["cell"]=42
        p.loot[44]={"name":"Crystal chest","cell":44,"description":"Something feels off. Opening it might be a bad idea."}
        action=investigate_suspect_container(p,s,[],distance)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(44,p.target)
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))

    def test_hungry_full_health_mage_can_provoke_but_starving_mage_cannot(self):
        for buff,allowed in (("hungry",True),("starving",False)):
            s,p=self.setup_arena()
            s["hero"]["buffs"]=[{"name":buff}]
            p.tiles[39]["terrain"]=6
            p.loot[44]={"name":"Crystal chest","cell":44,"description":"It feels off; opening is a bad idea."}
            action=investigate_suspect_container(p,s,[],distance)
            self.assertEqual(allowed,action is not None)

    def test_no_suspect_test_without_public_warning_or_health(self):
        s,p=self.setup_arena()
        p.tiles[39]["terrain"]=6
        p.loot[44]={"name":"Crystal chest","cell":44,"description":"You can see a wand inside.","hidden_type":"mimic"}
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))
        p.loot[44]["description"]="It feels off; opening it is a bad idea."
        s["hero"]["hp"]=5
        self.assertIsNone(investigate_suspect_container(p,s,[],distance))

    def test_trap_weight_prefers_retrievable_missile_over_spare_weapon(self):
        s,p=ready()
        dagger=item("dagger","THROW",identified=True,
                    description="This melee weapon deals 1-5 damage and requires 10 strength.")
        dart=item("dart x3","THROW",identified=True,quantity=3,
                  description="This thrown weapons deals 1-3 damage and requires 10 strength.")
        s["inventory"]=[dagger,dart]
        self.assertEqual(dart,payload(s))

    def test_explosive_missiles_are_not_used_as_retrievable_trap_weights(self):
        s,p=ready()
        s["inventory"]=[item("explosive shuriken","THROW",identified=True,
            description="This thrown weapons deals 2-8 damage and requires 10 strength.")]
        self.assertIsNone(payload(s))

    def setup_arena(self):
        s,p=ready()
        s["map"]={"width":9,"height":9,"cells":[{"cell":c,"terrain":1,"visible":True} for c in range(81)]}
        s["hero"]["cell"]=40
        s["inventory"].append(item("dagger","THROW",identified=True,
            description="This melee weapon deals 1-5 damage and requires 10 strength."))
        p.update(s)
        return s,p

    def test_dart_trap_selects_enemy_not_hero_and_retrieval_requires_triggered_tile(self):
        s,p=self.setup_arena()
        p.tiles[43].update(terrain=18,trap="worn dart trap")
        enemies=[{"name":"gnoll scout","cell":34}]
        s["objects"]=enemies
        action=trigger_trap(p,s,enemies,distance,neighbors,line_clear)
        self.assertEqual("THROW",action.action["action"])
        self.assertEqual(43,p.target)
        self.assertFalse(p.walkable(43))
        p.tiles[43]["terrain"]=19
        self.assertTrue(p.walkable(43))
        self.assertIsNone(trigger_trap(p,s,enemies,distance,neighbors,line_clear))

    def test_dart_trap_rejects_hero_or_friendly_nearest(self):
        s,p=self.setup_arena()
        p.tiles[41].update(terrain=18,trap="poison dart trap")
        enemies=[{"name":"gnoll scout","cell":43}]
        self.assertIsNone(trigger_trap(p,s,enemies,distance,neighbors,line_clear))
        p.tiles[41]["terrain"]=1
        p.tiles[43].update(terrain=18,trap="poison dart trap")
        s["objects"]=[*enemies,{"name":"sad ghost","cell":34}]
        self.assertIsNone(trigger_trap(p,s,enemies,distance,neighbors,line_clear))

    def test_no_guessing_unknown_traps_or_throwing_food(self):
        s,p=self.setup_arena()
        p.tiles[43].update(terrain=18,trap="summoning trap")
        enemies=[{"name":"gnoll scout","cell":34}]
        self.assertIsNone(trigger_trap(p,s,enemies,distance,neighbors,line_clear))
        s["inventory"]=[item("ration of food","THROW")]
        p.tiles[43]["trap"]="worn dart trap"
        self.assertIsNone(trigger_trap(p,s,enemies,distance,neighbors,line_clear))

    def test_bomb_uses_lightthrow_with_no_self_or_loot_collateral(self):
        s,p=self.setup_arena()
        s["inventory"].append(item("bomb","LIGHTTHROW"))
        enemies=[{"name":"gnoll scout","cell":33},{"name":"gnoll scout","cell":34}]
        s["objects"]=list(enemies)
        action=use_bomb(p,s,enemies,distance,neighbors)
        self.assertEqual("LIGHTTHROW",action.action["action"])
        self.assertGreater(distance(40,p.target,9),1)
        self.assertIn(p.target,p.bomb_cells)
        target=p.target
        s["status"]="targeting"
        self.assertTrue(observe_bombs(p,s,distance))
        s["status"]="ready"
        s["objects"].append({"name":"bomb","cell":target,"top_item":{
            "name":"bomb","description":"The bomb's fuse is burning away, keep your distance or put it out!"}})
        observe_bombs(p,s,distance)
        self.assertFalse(p.walkable(target))
        s["objects"]=enemies
        observe_bombs(p,s,distance)
        self.assertFalse(p.bomb_cells)

    def test_unmodeled_enhanced_bomb_is_not_treated_as_small_blast(self):
        s,p=self.setup_arena()
        s["inventory"].append(item("shrapnel bomb","LIGHTTHROW"))
        self.assertIsNone(use_bomb(p,s,[{"name":"great crab","cell":43}],distance,neighbors))

    def test_bomb_can_throw_two_tiles_without_entering_one_tile_blast(self):
        s,p=self.setup_arena()
        s["inventory"].append(item("bomb","LIGHTTHROW"))
        enemies=[{"name":"marsupial rat","cell":32},{"name":"marsupial rat","cell":33}]
        s["objects"]=enemies
        original=p.shot_clear
        p.shot_clear=lambda state,c: distance(40,c,9)<=2 and original(state,c)
        action=use_bomb(p,s,enemies,distance,neighbors)
        self.assertIsNotNone(action)
        self.assertEqual(2,distance(40,p.target,9))


class GhostQuestTests(unittest.TestCase):
    def test_unparsed_reward_stats_do_not_authorize_blind_confirmation(self):
        s,p=ready()
        p.ghost_menu={"stage":"next","steps":5,"index":1,
            "options":["weapon","armor"],"scores":[-100,-100]}
        self.assertEqual("back",quest_menu(p,s).action["type"])
        self.assertIsNone(p.ghost_menu)

    def test_start_ghost_only_when_prepared_and_never_other_quest_npc(self):
        s,p=ready()
        s["depth"]=2
        s["objects"]=[{"name":"sad ghost","cell":25}]
        p.update(s)
        self.assertEqual(25,visit_ghost(p,s,[],distance,neighbors).action["cell"])
        p.ghost_menu=None
        s["hero"]["hp"]=5
        self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))
        s["hero"]["hp"]=20
        s["objects"]=[{"name":"old wandmaker","cell":25}]
        self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))

    def test_quest_type_comes_from_actual_dialogue_not_depth(self):
        s,p=ready()
        p.ghost_menu={"stage":"dialogue","steps":0}
        s["ui"]["texts"]=["Sad Ghost", "Slay the great crab... Beware its claw."]
        self.assertEqual("back",quest_menu(p,s).action["type"])
        self.assertEqual("great crab",p.ghost_quest["target"])
        self.assertEqual("active",p.ghost_quest["stage"])

    def test_no_reward_assumed_from_enemy_disappearance(self):
        s,p=ready()
        p.ghost_quest={"stage":"active","target":"fetid rat"}
        observe_quest(p,s)
        self.assertEqual("active",p.ghost_quest["stage"])
        s["ui"]["texts"]=["Thank you... come find me..."]
        observe_quest(p,s)
        self.assertEqual("reward",p.ghost_quest["stage"])

    def test_great_crab_never_receives_unaware_direct_zap(self):
        s,p=ready()
        foe={"name":"great crab","cell":25}
        # This fixture has no second exit: do not replace a blocked zap with
        # a blind retreat into the same confined room.
        from tools.policy_decision import TacticalBlocked
        with self.assertRaises(TacticalBlocked):
            quest_combat(p,s,[foe],distance,neighbors)
        foe["sleeping"]=True
        action=quest_combat(p,s,[foe],distance,neighbors)
        self.assertIn("surprise",action.reason)

    def test_fetid_rat_uses_ranged_damage_at_distance(self):
        s,p=ready()
        foe={"name":"fetid rat","cell":26}
        action=quest_combat(p,s,[foe],distance,neighbors)
        self.assertEqual("ZAP",action.action["action"])
        self.assertIn("fetid rat",action.reason)

    def test_trickster_uses_ranged_attack_even_when_adjacent(self):
        s,p=ready()
        foe={"name":"gnoll trickster","cell":25}
        self.assertEqual("ZAP",quest_combat(p,s,[foe],distance,neighbors).action["action"])

    def test_lone_trickster_does_not_chase_melee_without_cover_or_charge(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        foe={"name":"gnoll trickster","cell":26}
        with self.assertRaises(Finished):
            quest_combat(p,s,[foe],distance,neighbors)

    def test_ghost_reward_compares_two_rendered_previews_and_confirms_choice(self):
        s,p=ready()
        s["hero"]["strength"]=10
        p.ghost_menu={"stage":"dialogue","steps":0}
        rewards=[{"id":"weapon","label":"spear"},{"id":"armor","label":"leather armor"}]
        s["ui"]={"texts":["DEFEATED FETID RAT","Please take one of these items"],"buttons":rewards}
        self.assertEqual("weapon",quest_menu(p,s).action["id"])
        s["ui"]={"texts":["spear","This melee weapon deals 2-12 damage and requires 12 strength"],
            "buttons":[{"id":"cancel","label":"Cancel"}]}
        self.assertEqual("cancel",quest_menu(p,s).action["id"])
        s["ui"]={"texts":["DEFEATED FETID RAT"],"buttons":rewards}
        self.assertEqual("armor",quest_menu(p,s).action["id"])
        s["ui"]={"texts":["leather armor","This armor blocks 0-4 damage and requires 10 strength"],
            "buttons":[{"id":"cancel","label":"Cancel"}]}
        self.assertEqual("cancel",quest_menu(p,s).action["id"])
        s["ui"]={"texts":["DEFEATED FETID RAT"],"buttons":rewards}
        self.assertEqual("armor",quest_menu(p,s).action["id"])
        s["ui"]={"texts":["leather armor"],"buttons":[{"id":"confirm","label":"Confirm"}]}
        self.assertEqual("confirm",quest_menu(p,s).action["id"])
        self.assertEqual("claiming",p.ghost_quest["stage"])
        s["inventory"].append(item("leather armor +1","EQUIP"))
        s["ui"]["texts"]=["Farewell, adventurer!"]
        observe_quest(p,s)
        self.assertEqual("done",p.ghost_quest["stage"])


class WellAdvantageTests(unittest.TestCase):
    def well(self):
        s,p=ready()
        s["hero"].update(hp=16,max_hp=20,strength=12,buffs=[{"name":"starving"}])
        next(t for t in s["map"]["cells"] if t["cell"]==25).update(terrain=24,
            effects=["Power of health radiates from the water of this well."])
        s["inventory"].append(item("leather armor","EQUIP",known_cursed=True,
            description="This armor blocks 0-4 damage and requires 12 strength."))
        p.update(s)
        return s,p

    def test_use_well_to_clear_known_curse_after_equipping_upgrade(self):
        s,p=self.well()
        action=choose_well(p,s,[],distance,neighbors)
        self.assertEqual("EQUIP",action.action["action"])
        armor=s["inventory"][-1]
        armor["equipped"]=True
        self.assertEqual(25,choose_well(p,s,[],distance,neighbors).action["cell"])

    def test_urgent_low_hp_skips_gear_setup(self):
        s,p=self.well()
        s["hero"]["hp"]=4
        self.assertEqual(25,choose_well(p,s,[],distance,neighbors).action["cell"])

    def test_hungry_hurt_without_food_uses_well_and_never_overweight_armor(self):
        s,p=self.well()
        s["hero"].update(strength=10,buffs=[{"name":"hungry"}])
        s["inventory"]=[i for i in s["inventory"] if "food" not in i["name"].lower()]
        self.assertEqual(25,choose_well(p,s,[],distance,neighbors).action["cell"])
