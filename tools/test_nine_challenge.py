import unittest

from tools.nine_challenge import NineChallengePolicy, CHALLENGES, POISONOUS
from tools.survival_bot import Finished, distance, neighbors
from tools.test_survival_bot import state, fully_known
from tools.seed_tactics import choose_seed
from tools.resource_tactics import choose_meat
from tools.alchemy_tactics import Brew, plan_brew, alchemy_menu
from tools.artifact_tactics import equip_artifact, use_artifact
from tools.mage_tactics import shield_battery
from tools.shop_tactics import priority


def selected_mage():
    return {"scene": "HeroSelectScene", "status": "menu", "modal": False,
            "ui": {"texts": ["Mage"], "buttons": [
                {"id": "challenges", "label": "Challenges"}, {"id": "start", "label": "Start"}]}}


def verified_policy():
    p = NineChallengePolicy()
    s = selected_mage()
    assert p.choose(s).action["id"] == "challenges"
    s["modal"] = True
    s["ui"]["buttons"] = [{"id": str(i), "label": name, "checked": True} for i, name in enumerate(CHALLENGES)]
    assert p.choose(s).action["type"] == "back"
    return p


class NineChallengeTests(unittest.TestCase):
    def test_game_options_opened_before_challenges_and_never_looped(self):
        p, s = NineChallengePolicy(), selected_mage()
        s["ui"]["buttons"] = [{"id": "options", "label": "Game Options"}, {"id": "start", "label": "Start"}]
        self.assertEqual("options", p.choose(s).action["id"])
        self.assertFalse(p.challenges_verified)
        with self.assertRaisesRegex(Finished, "verification unavailable"):
            p.choose(s)
        self.assertEqual("challenges", p.choose(selected_mage()).action["id"])

    def test_first_run_missing_options_does_not_guess_unlabeled_button(self):
        p, s = NineChallengePolicy(), selected_mage()
        s["ui"]["buttons"] = [{"id": "start", "label": "Start"}, {"id": "unknown", "label": ""}]
        with self.assertRaisesRegex(Finished, "verification unavailable"):
            p.choose(s)
        self.assertFalse(p.challenges_verified)

    def test_start_requires_nine_observed_checkmarks(self):
        p, s = NineChallengePolicy(), selected_mage()
        self.assertEqual("challenges", p.choose(s).action["id"])
        s["modal"] = True
        s["ui"]["buttons"] = [{"id": str(i), "label": name, "checked": i != 3} for i, name in enumerate(CHALLENGES)]
        self.assertEqual("3", p.choose(s).action["id"])
        self.assertFalse(p.challenges_verified)
        s["ui"]["buttons"][3]["checked"] = True
        self.assertEqual("back", p.choose(s).action["type"])
        self.assertTrue(p.challenges_verified)
        self.assertEqual("start", p.choose(selected_mage()).action["id"])

    def test_existing_run_cannot_claim_challenges_are_enabled(self):
        with self.assertRaisesRegex(Finished, "visibly verified"):
            NineChallengePolicy().choose(state())

    def test_locked_or_old_api_does_not_start_normal_mode(self):
        p, s = NineChallengePolicy(), selected_mage()
        p.choose(s)
        s["modal"] = True
        with self.assertRaises(Finished):
            p.choose(s)

    def test_all_poisonous_recipes_and_unknown_drinks_are_vetoed(self):
        p = NineChallengePolicy()
        for name in POISONOUS | {"crimson potion"}:
            with self.subTest(name=name):
                self.assertFalse(p.item_action_allowed({"name": name}, "DRINK"))
        self.assertTrue(p.item_action_allowed({"name": "potion of cleansing"}, "DRINK"))
        self.assertTrue(p.item_action_allowed({"name": "potion of healing"}, "THROW"))

    def test_seeds_are_reserved_for_alchemy_not_planted_or_thrown(self):
        s, p = state(), verified_policy()
        s["inventory"] += [{"id": "seed", "name": "seed of icecap", "actions": ["PLANT", "THROW"]},
                           {"id": "meat", "name": "mystery meat", "actions": ["THROW"]}]
        p.update(s)
        self.assertIsNone(choose_seed(p, s, [], distance, neighbors))
        self.assertIsNone(choose_meat(p, s, [], distance, neighbors))
        self.assertFalse(p.item_action_allowed(s["inventory"][-2], "THROW"))

    def test_poisonous_healing_is_not_selected_at_critical_hp(self):
        s, p = state(), verified_policy()
        s["hero"]["hp"] = 4
        s["inventory"].append({"id": "heal", "name": "potion of healing", "actions": ["DRINK"]})
        d = p.choose(s)
        self.assertNotEqual("heal", d.action.get("id"))

    def test_current_mage_talent_names_and_priorities(self):
        s, p = state(), verified_policy()
        s["hero"]["talents"] = [{"name": "inscribed power", "available": 1, "points": 0, "max_points": 2}]
        self.assertEqual({"type": "talent", "name": "inscribed power"}, p.choose(s).action)

    def test_unknown_artifact_fills_empty_slot_unless_known_cursed(self):
        s, p = state(), verified_policy()
        artifact = {"id": "horn", "name": "horn of plenty +0", "actions": ["EQUIP"]}
        s["inventory"].append(artifact)
        self.assertEqual("horn", equip_artifact(p, s).action["id"])
        artifact["curse_known"] = True
        self.assertEqual("horn", equip_artifact(p, s).action["id"])
        artifact["known_cursed"] = True
        self.assertIsNone(equip_artifact(p, s))

    def test_horn_uses_meal_action_only_while_equipped(self):
        s, p = state(), verified_policy()
        s["hero"]["buffs"] = [{"name": "starving"}]
        s["inventory"].append({"id": "horn", "name": "horn of plenty +0", "equipped": True, "actions": ["EAT", "SNACK"]})
        self.assertEqual("EAT", use_artifact(p, s, []).action["action"])

    def test_chains_require_known_charge_and_anchor_then_target_observed_ground(self):
        s, p = fully_known(state()), verified_policy()
        s["hero"]["hp"] = 3
        s["objects"] = [{"cell": 25, "name": "gnoll scout"}]
        chains = {"id": "chains", "name": "ethereal chains +0", "equipped": True, "actions": ["CAST"], "status": "?"}
        s["inventory"].append(chains)
        p.update(s)
        self.assertIsNone(use_artifact(p, s, s["objects"]))
        chains["status"] = "4"
        self.assertEqual("CAST", use_artifact(p, s, s["objects"]).action["action"])
        self.assertTrue(p.tiles[p.target]["visible"])
        self.assertGreaterEqual(distance(p.target, 25, 7), 3)

    def test_hourglass_selects_freeze_not_stasis(self):
        s, p = state(), verified_policy()
        s["hero"]["hp"] = 3
        s["inventory"].append({"id": "glass", "name": "timekeeper's hourglass +0", "equipped": True, "actions": ["ACTIVATE"]})
        self.assertEqual("ACTIVATE", use_artifact(p, s, [{"cell": 25}]).action["action"])
        s["ui"]["buttons"] = [{"id": "freeze", "label": "Freeze time around me"}, {"id": "stasis", "label": "Put myself in stasis"}]
        self.assertEqual("freeze", p.menu(s).action["id"])

    def test_shop_never_buys_poison_as_healing(self):
        self.assertIsNone(priority("potion of healing", [], pharmacophobia=True))
        self.assertIsNotNone(priority("potion of healing", []))

    def test_battery_keeps_offensive_staff_and_never_tests_unknown_wand(self):
        s, p = state(), verified_policy()
        s["hero"].update(hp=3, talents=[{"name": "shield battery", "points": 1}])
        wand = {"id": "spare", "name": "wand of frost", "actions": ["ZAP"], "status": "2/2"}
        s["inventory"].append(wand)
        self.assertIsNone(shield_battery(p, s, [{"cell": 25}]))
        wand["identified"] = True
        self.assertEqual("spare", shield_battery(p, s, [{"cell": 25}]).action["id"])
        self.assertEqual(s["hero"]["cell"], p.target)
        self.assertIsNone(shield_battery(p, s, [{"cell": 25}]))


class AlchemyTests(unittest.TestCase):
    def test_matching_seeds_and_never_healing(self):
        s = state()
        s["inventory"].append({"name": "seed of blindweed", "quantity": 3})
        brew = plan_brew(s)
        self.assertEqual(("seed of blindweed",)*3, brew.ingredients)
        s["inventory"][-1]["name"] = "seed of sungrass"
        self.assertIsNone(plan_brew(s))

    def test_upgrades_and_last_escape_are_preserved(self):
        s = state()
        s["inventory"] += [{"name": "scroll of upgrade"}, {"name": "scroll of teleportation"}, {"name": "scroll of lullaby"}]
        self.assertIsNone(plan_brew(s))
        s["inventory"][-1]["quantity"] = 2
        self.assertEqual("stone of deep sleep", plan_brew(s).output)

    def test_ui_recipe_requires_exact_preview_and_is_bounded(self):
        p = NineChallengePolicy()
        p.alchemy_plan = {"brew": Brew(("potion of purity",), "potion of cleansing", "test"),
                          "index": 1, "stage": "slot", "steps": 0}
        s = {"ui": {"buttons": [{"id": "wrong", "label": "Craft: potion of shielding"}]}}
        self.assertEqual("back", alchemy_menu(p, s).action["type"])
        self.assertIsNone(p.alchemy_plan)

    def test_three_seed_ui_sequence(self):
        p = NineChallengePolicy()
        p.alchemy_plan = {"brew": Brew(("seed of blindweed",)*3, "random potion", "test"),
                          "index": 0, "stage": "slot", "steps": 0}
        for _ in range(3):
            s = {"ui": {"buttons": [{"id": "add", "label": "Add Item"}]}}
            self.assertEqual("add", alchemy_menu(p, s).action["id"])
            s["ui"]["buttons"] = [{"id": "seed", "label": "Seed of blindweed x3"}]
            self.assertEqual("seed", alchemy_menu(p, s).action["id"])
        s["ui"]["buttons"] = [{"id": "craft", "label": "Craft: Random Potion"}]
        self.assertEqual("craft", alchemy_menu(p, s).action["id"])
        self.assertEqual("back", alchemy_menu(p, s).action["type"])

    def test_ingredient_bag_search_does_not_loop(self):
        p = NineChallengePolicy()
        p.alchemy_plan = {"brew": Brew(("seed of blindweed",)*3, "random potion", "test"),
                          "index": 0, "stage": "bag", "steps": 0}
        s = {"ui": {"buttons": [{"id": "pouch", "label": "Velvet Pouch"}]}}
        self.assertEqual("pouch", alchemy_menu(p, s).action["id"])
        self.assertEqual("back", alchemy_menu(p, s).action["type"])
