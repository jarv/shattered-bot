import unittest

from tools.consumable_tactics import discovery_score, learn_sources
from tools.survival_bot import SurvivalPolicy
from tools.test_survival_bot import state,fully_known


def potion(name="azure potion", quantity=1):
    return {"id": name, "name": name, "quantity": quantity, "identified": name.startswith("potion of "),
            "actions": ["DRINK", "THROW"]}


class ConsumableTests(unittest.TestCase):
    def test_repeated_early_floor_pairs_are_strength_clues_not_identification(self):
        repeated = potion(quantity=2)
        common = potion("golden potion", quantity=3)
        scores = {"azure potion": {1, 3}, "golden potion": {2}}
        self.assertGreater(discovery_score(repeated, scores), discovery_score(common, scores))
        self.assertFalse(repeated["identified"])

    def test_holding_same_potion_on_next_floor_is_not_a_new_drop(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"].append(potion())
        learn_sources(p, s)
        s["depth"] = 2
        learn_sources(p, s)
        self.assertEqual({1}, p.consumable_sources["azure potion"])

    def test_mage_knows_upgrade_and_reads_an_unknown_scroll_once(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"].append({"id": "rune", "name": "scroll of SOWILO", "actions": ["READ"], "identified": False})
        d = p.choose(s)
        self.assertEqual("rune", d.action["id"])
        self.assertTrue(p.upgrade_known)
        self.assertEqual("discover-scroll", p.menu_plan)
        self.assertNotEqual("READ", p.choose(s).action.get("action"))

    def test_identify_scroll_precedes_risky_potion_drinking(self):
        s = state()
        s["inventory"] += [potion(), {"id": "identify", "name": "scroll of identify", "actions": ["READ"]}]
        self.assertEqual("identify", SurvivalPolicy().choose(s).action["id"])

    def test_justified_known_upgrade_precedes_risky_unknown_scroll_test(self):
        s = state()
        s["inventory"] += [{"id": "unknown", "name": "scroll of SOWILO", "actions": ["READ"]},
                           {"id": "upgrade", "name": "scroll of upgrade", "actions": ["READ"]}]
        self.assertEqual("upgrade", SurvivalPolicy().choose(s).action["id"])

    def test_known_strength_is_drunk_and_unknown_strength_candidate_is_tested(self):
        for name in ("potion of strength", "azure potion"):
            s = fully_known(state())
            s["inventory"].append(potion(name))
            d = SurvivalPolicy().choose(s)
            self.assertEqual("DRINK", d.action["action"])
            self.assertEqual(name, d.action["id"])

    def test_no_drink_testing_when_hurt_or_enemies_are_present(self):
        for danger in ("hurt", "sleeping enemy", "trap"):
            s = state()
            s["inventory"].append(potion())
            if danger == "hurt": s["hero"]["hp"] = 10
            if danger == "sleeping enemy": s["objects"] = [{"cell": 26, "name": "sewer crab", "sleeping": True}]
            if danger == "trap": next(t for t in s["map"]["cells"] if t["cell"] == 24)["trap"] = "dart trap"
            self.assertNotEqual("DRINK", SurvivalPolicy().choose(s).action.get("action"))

    def test_identify_selection_prefers_unknown_potion_not_bag(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"] += [potion(), {"id": "bag", "name": "potion bandolier", "identified": True, "actions": []}]
        s.update(status="menu", modal=True)
        s["ui"] = {"texts": ["Identify an item"], "buttons": [
            {"id": "bag-button", "label": "potion bandolier"}, {"id": "potion-button", "label": "azure potion"}]}
        p.menu_plan = "discover-scroll"
        self.assertEqual("potion-button", p.choose(s).action["id"])

    def test_identify_returns_from_seed_pouch_to_backpack(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"].append(potion())
        s.update(status="menu", modal=False)
        s["ui"] = {"texts": ["Identify an item"], "buttons": [
            {"id": "backpack", "label": "Backpack"}, {"id": "pouch", "label": "Velvet Pouch"}]}
        p.menu_plan = "discover-scroll"
        self.assertEqual("backpack", p.choose(s).action["id"])
        s["ui"]["buttons"].append({"id": "target", "label": "azure potion"})
        self.assertEqual("target", p.choose(s).action["id"])

    def test_failed_identify_selection_is_not_immediately_retried(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"] += [potion(), {"id": "identify", "name": "scroll of identify", "actions": ["READ"]}]
        s.update(status="menu", modal=True)
        s["ui"] = {"texts": ["Identify an item"], "buttons": []}
        p.menu_plan = "discover-scroll"
        self.assertEqual("back", p.choose(s).action["type"])
        s.update(status="ready", modal=False)
        s["ui"] = {"texts": [], "buttons": []}
        self.assertNotEqual("identify", p.choose(s).action.get("id"))

    def test_menu_loop_guard_stops_repeated_legal_cycles(self):
        from tools.survival_bot import Decision, Finished, MenuLoopGuard
        s = state()
        s.update(status="menu", modal=True)
        s["ui"] = {"texts": ["Identify an item"], "buttons": [{"id": "bag", "label": "Backpack"}]}
        d = Decision({"type": "button", "id": "bag"}, "identify: open item bag")
        guard = MenuLoopGuard(repetitions=3)
        guard.check(s, d)
        guard.check(s, d)
        with self.assertRaises(Finished) as error:
            guard.check(s, d)
        self.assertIn("menu loop", error.exception.reason)

    def test_unknown_transmutation_is_cancelled_not_applied_to_staff(self):
        s, p = state(), SurvivalPolicy()
        s.update(status="menu", modal=True)
        s["ui"] = {"texts": ["Transmute an item"], "buttons": [{"id": "staff", "label": "staff of magic missile"}]}
        p.menu_plan = "discover-scroll"
        self.assertEqual({"type": "back"}, p.choose(s).action)
        s["ui"] = {"texts": ["Do you really want to cancel this scroll usage? It will be consumed anyway."],
                   "buttons": [{"id": "yes", "label": "Yes, I'm positive"}]}
        self.assertEqual("yes", p.choose(s).action["id"])

    def test_known_frost_used_at_safe_range_against_durable_enemy(self):
        s = state()
        s["objects"] = [{"cell": 27, "name": "prison guard"}]
        s["map"]["cells"].append({"cell": 27, "terrain": 1, "visible": True})
        s["inventory"].append(potion("potion of frost"))
        self.assertEqual("THROW", SurvivalPolicy().choose(s).action["action"])
