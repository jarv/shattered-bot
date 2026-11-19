import copy
import unittest
from unittest.mock import patch

from tools.test_challenge_systems import ready, item
from tools.test_nine_challenge import selected_mage
from tools.nine_challenge import NineChallengePolicy
from tools.survival_bot import SurvivalPolicy, Decision, Finished, distance, neighbors
from tools.ghost_quest import visit_ghost, observe_quest
from tools.room_completion import obligations
from tools.seed_startup import normalize
from tools.special_rooms import fire_barrier
from tools.puzzle_supplies import demands
from tools.room_tactics import extinguish


FIRE_TEXT = ("A wall of dense bright green fire is here, seemingly caused by magic. "
             "It's so dense that you can't move through it, and it ignites anything that gets too close. "
             "It shows no signs of burning down naturally, you'll need to use something to extinguish it.")


class CompletionTests(unittest.TestCase):
    def test_journal_keys_are_scoped_to_current_floor_only(self):
        s,p=ready()
        s["keys"]=[{"name":"iron key x2","depth":s["depth"],"quantity":2},
                   {"name":"iron key x5","depth":s["depth"]+1,"quantity":5},
                   {"name":"Crystal key","depth":s["depth"]+1,"quantity":1}]
        p.update(s)
        self.assertEqual(2,p.keys["iron"])
        self.assertEqual(0,p.keys["crystal"])

    def test_actionable_locked_room_descent_conflict_is_soft_and_replans_without_descending(self):
        from tools.policy_decision import Intent, TacticalBlocked
        s,p=ready()
        for tile in s["map"]["cells"]:
            if tile["cell"]==25:tile["terrain"]=8
            if tile["cell"]==26:tile["terrain"]=10
        s["keys"]=[{"name":"iron key","depth":1,"quantity":1}]
        p.update(s)
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":25},"descend",Intent.DESCEND)):
            with self.assertRaises(TacticalBlocked) as caught:p.choose(s)
        self.assertEqual("descent-obligation",caught.exception.code)
        action=p.recover_tactical_block(s,caught.exception)
        self.assertEqual(Intent.EXPLORE,action.intent)
        self.assertNotEqual(25,action.action.get("cell"))

    def test_route_to_locked_room_avoids_stairs_without_waiving_descent_gate(self):
        from tools.policy_decision import Intent
        s,p=ready()
        p.tiles[25]["terrain"]=8
        p.tiles[26]["terrain"]=10
        p.keys["iron"]=1
        paths={24:None,25:24,26:25,17:24,18:17,19:18}
        action=p.toward(s,26,"unlock room",paths,intent=Intent.EXPLORE)
        self.assertNotEqual(25,action.action.get("cell"))
        self.assertEqual(25,p.toward(s,25,"descend",paths,intent=Intent.DESCEND).action["cell"])
        self.assertIsNone(p.toward(s,26,"unlock room",{24:None,25:24,26:25},intent=Intent.EXPLORE))

    def test_missing_required_chest_key_can_fund_bounded_search_before_descent(self):
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"hungry"}]
        s["inventory"].append(item("ration of food","EAT"))
        p.loot[26]={"name":"Locked chest","description":"Needs a golden key."}
        self.assertEqual(12,p.search_limit(s,0,True))
        p.keys["golden"]=1
        self.assertEqual(0,p.search_limit(s,0,True))
        p.keys["golden"]=0
        s["hero"]["hp"]=10
        self.assertEqual(12,p.search_limit(s,0,True))

    def test_pause_menu_is_closed_without_clicking_settings_or_main_menu(self):
        s,p=ready()
        s["modal"]=True
        s["ui"]={"texts":["Settings","Challenges","Main Menu"],"buttons":[
            {"id":str(i),"label":name} for i,name in enumerate(("Settings","Challenges","Main Menu"))]}
        self.assertEqual({"type":"back"},p.menu(s).action)

    def test_unresolved_fire_barrier_is_logged_unfinished_then_descent_is_permitted(self):
        s,p=ready()
        p.tiles[26].update(terrain=14,effects=[FIRE_TEXT],visible=True)
        self.assertTrue(fire_barrier(p.tiles[26]))
        self.assertIn("frost",[d.kind for d in demands(p,s,distance)])
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":25},"stairs: descend after floor exploration", intent="descend")):
            action=p.choose(s)
        self.assertEqual("descend",action.intent)
        self.assertEqual("magical fire barrier",p.deferred_obligations[0]["obligation"]["kind"])
        self.assertEqual("deferred-unfinished",p.deferred_obligations[0]["status"])
        self.assertTrue(obligations(p,s))  # Logging a deferral is not fake completion.
        p.tiles[26]["effects"]=[]
        self.assertFalse(obligations(p,s))

    def test_actual_fire_text_is_throw_target_not_drink_identification(self):
        s,p=ready()
        p.tiles[27].update(terrain=14,effects=[FIRE_TEXT],visible=True)
        s["inventory"].append(item("potion of frost","THROW"))
        action=extinguish(p,s,[],distance)
        self.assertEqual("THROW",action.action.get("action"))
        self.assertEqual(27,p.target)

    def test_ordinary_fire_is_not_a_permanent_puzzle_barrier(self):
        self.assertFalse(fire_barrier({"effects":["A fire is raging here."]}))

    def test_uncollectable_ghost_reward_can_be_deferred_without_claiming_pickup(self):
        s,p=ready()
        p.ghost_quest.update(stage="reward",depth=1)
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":25},"stairs: descend after floor exploration", intent="descend")):
            self.assertEqual("descend",p.choose(s).intent)
        self.assertEqual("reward",p.ghost_quest["stage"])
        self.assertEqual("Sad Ghost quest/reward",p.deferred_obligations[0]["obligation"]["kind"])

    def test_pending_special_reward_blocks_nonstairs_labeled_exit_click(self):
        s,p=ready()
        p.tiles[25]["terrain"]=8
        p.loot[26]={"name":"locked chest","cell":26}
        with patch.object(SurvivalPolicy,"choose",return_value=Decision({"type":"cell","cell":25},"explore: frontier")):
            with self.assertRaisesRegex(Finished,"Ordinary navigation attempted a stair"):
                p.choose(s)

    def test_unopened_room_and_landmark_remain_obligations_not_skips(self):
        s,p=ready()
        p.tiles[25].update(terrain=13)
        p.tiles[26].update(terrain=0,name="Distant well")
        kinds={o["kind"] for o in obligations(p,s)}
        self.assertIn("unopened barricade",kinds)
        self.assertIn("uncompleted distant-well drop",kinds)
        self.assertFalse(p.conserve_descent_allowed(s))

    def test_empty_ordinary_chasm_is_not_invented_as_unfinished_treasure_room(self):
        s,p=ready()
        p.tiles[25].update(terrain=0,name="Chasm")
        s["map"]["generated_room_id"]="secret vault"
        self.assertFalse(obligations(p,s))

    def test_resolved_mutually_exclusive_branch_is_not_required_again(self):
        s,p=ready()
        p.tiles[25]["terrain"]=31
        p.loot[26]={"name":"crystal chest","cell":26}
        p.resolved_crystal_alternatives.update({25,26})
        self.assertFalse(obligations(p,s))


class GhostCollectionTests(unittest.TestCase):
    def test_reward_does_not_require_starting_quest_health_or_magic(self):
        s,p=ready()
        s["depth"]=2
        s["hero"]["hp"]=4
        s["inventory"][0]["status"]="0/4"
        s["objects"]=[{"name":"sad ghost","cell":25}]
        p.ghost_quest.update(stage="reward")
        self.assertEqual(25,visit_ghost(p,s,[],distance,neighbors).action.get("cell"))

    def test_reward_confirmation_not_completion_when_inventory_was_full(self):
        s,p=ready()
        p.ghost_quest.update(stage="claiming",selected="leather armor",count_before=0)
        s["ui"]["texts"]=["Farewell, adventurer!"]
        observe_quest(p,s)
        self.assertEqual("collect_dropped",p.ghost_quest["stage"])
        p.loot[25]={"cell":25,"name":"leather armor +1","top_item":{"name":"leather armor +1"}}
        self.assertEqual(25,visit_ghost(p,s,[],distance,neighbors).action.get("cell"))
        s["inventory"].append(item("leather armor +1","EQUIP"))
        observe_quest(p,s)
        self.assertEqual("done",p.ghost_quest["stage"])

    def test_existing_same_reward_does_not_fake_pickup(self):
        s,p=ready()
        s["inventory"].append(item("leather armor","EQUIP"))
        p.ghost_quest.update(stage="claiming",selected="leather armor",count_before=1)
        s["ui"]["texts"]=["Farewell, adventurer!"]
        observe_quest(p,s)
        self.assertNotEqual("done",p.ghost_quest["stage"])

    def test_disappearing_foe_can_trigger_public_ghost_recheck_not_assumed_victory(self):
        s,p=ready()
        s["depth"]=2
        p.ghost_quest.update(stage="active",target="fetid rat")
        s["objects"]=[{"name":"fetid rat","cell":26}]
        observe_quest(p,s)
        s["objects"]=[{"name":"sad ghost","cell":25}]
        observe_quest(p,s)
        self.assertEqual("active",p.ghost_quest["stage"])
        self.assertIn("completion evidence",visit_ghost(p,s,[],distance,neighbors).reason)


class SeedStartupTests(unittest.TestCase):
    def test_seed_normalization_rejects_noncode_input(self):
        self.assertEqual("ABC-DEF-GHI",normalize("abcdefghi"))
        with self.assertRaises(ValueError):
            normalize("../../profile")

    def test_seed_is_typed_saved_reopened_and_verified_before_start(self):
        p=NineChallengePolicy(seed="ABC-DEF-GHI")
        p.challenges_verified=True
        s=selected_mage()
        s["ui"]["buttons"].append({"id":"seed","label":"Custom Seed"})
        self.assertEqual("seed",p.choose(s).action["id"])
        dialog=copy.deepcopy(s)
        dialog["modal"]=True
        dialog["ui"]={"texts":["Enter a Custom Seed"],"text_input":"","buttons":[{"id":"set","label":"Set"}]}
        self.assertEqual({"type":"text","text":"ABC-DEF-GHI"},p.choose(dialog).action)
        dialog["ui"]["text_input"]="ABC-DEF-GHI"
        self.assertEqual("set",p.choose(dialog).action["id"])
        self.assertIsNone(p.verified_seed)
        self.assertEqual("seed",p.choose(s).action["id"])
        self.assertEqual("set",p.choose(dialog).action["id"])
        self.assertEqual("ABC-DEF-GHI",p.verified_seed)
        self.assertEqual("start",p.choose(s).action["id"])

    def test_mismatched_reopened_seed_blocks_not_silently_random(self):
        p=NineChallengePolicy(seed="ABC-DEF-GHI")
        p.challenges_verified=True
        p.seed_submitted=True
        s=selected_mage()
        s["ui"].update(text_input="ZZZ-ZZZ-ZZZ",texts=["Enter a Custom Seed"])
        with self.assertRaisesRegex(Finished,"does not match"):
            p.choose(s)
