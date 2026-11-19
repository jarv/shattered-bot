import unittest

from tools.survival_bot import SurvivalPolicy
from tools.test_survival_bot import state


def add_seed(s, kind):
    item = {"id": kind, "name": f"seed of {kind}", "actions": ["PLANT", "THROW"]}
    s["inventory"].append(item)
    return item


class SeedTests(unittest.TestCase):
    def test_sungrass_plant_activate_recover_sequence(self):
        s, p = state(), SurvivalPolicy()
        s["hero"]["hp"] = 10
        add_seed(s, "sungrass")
        self.assertEqual({"type": "item", "id": "sungrass", "action": "PLANT"}, p.choose(s).action)
        tile = next(t for t in s["map"]["cells"] if t["cell"] == 24)
        tile["plant"] = "Sungrass"
        self.assertEqual({"type": "cell", "cell": 24}, p.choose(s).action)
        tile.pop("plant")
        s["hero"]["buffs"] = [{"name": "herbal healing"}]
        self.assertEqual("seed: sheltered sungrass recovery", p.choose(s).reason)

    def test_threat_interrupts_sungrass_recovery(self):
        s, p = state(), SurvivalPolicy()
        s["hero"].update(hp=10, buffs=[{"name": "herbal healing"}])
        p.seed_plan = {"kind": "sungrass", "cell": 24, "stage": "recover", "waits": 0}
        s["objects"] = [{"cell": 25, "name": "sewer crab"}]
        self.assertNotIn("sungrass", p.choose(s).reason)
        self.assertIsNone(p.seed_plan)

    def test_no_sungrass_while_starving_or_on_trap(self):
        for scenario in ("starving", "trap"):
            s = state()
            s["hero"]["hp"] = 10
            add_seed(s, "sungrass")
            if scenario == "starving": s["hero"]["buffs"] = [{"name": "starving"}]
            else: next(t for t in s["map"]["cells"] if t["cell"] == 24)["trap"] = "worn dart trap"
            self.assertNotIn("sungrass", SurvivalPolicy().choose(s).reason)

    def corridor(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (22, 23, 24, 25, 26) else 4,
                               "visible": True} for c in range(49)]
        s["hero"]["cell"] = 23
        return s

    def test_prepares_earthroot_in_narrow_position_with_time_to_activate(self):
        s = self.corridor()
        add_seed(s, "earthroot")
        s["objects"] = [{"cell": 26, "name": "sewer crab"}]
        self.assertEqual("seed: prepare earthroot", SurvivalPolicy().choose(s).reason)

    def test_no_two_turn_setup_against_adjacent_enemy(self):
        s = self.corridor()
        add_seed(s, "earthroot")
        s["objects"] = [{"cell": 24, "name": "sewer crab"}]
        self.assertNotIn("earthroot", SurvivalPolicy().choose(s).reason)

    def test_poison_trap_is_placed_ahead_not_under_enemy(self):
        s = self.corridor()
        add_seed(s, "sorrowmoss")
        s["objects"] = [{"cell": 26, "name": "sewer crab"}]
        p = SurvivalPolicy()
        self.assertEqual("seed: sorrowmoss pursuit trap", p.choose(s).reason)
        self.assertEqual(24, p.target)

    def test_does_not_poison_a_nearly_dead_enemy(self):
        s = self.corridor()
        add_seed(s, "sorrowmoss")
        s["objects"] = [{"cell": 26, "name": "sewer crab", "health_bar": [3, 32]}]
        self.assertNotIn("pursuit trap", SurvivalPolicy().choose(s).reason)

    def test_goo_telegraph_precedes_seed_setup(self):
        s = self.corridor()
        add_seed(s, "earthroot")
        s["objects"] = [{"cell": 26, "name": "Goo"}]
        s["danger_cells"] = [23, 24, 25, 26]
        d = SurvivalPolicy().choose(s)
        self.assertEqual("combat: evade telegraph", d.reason)
        self.assertNotIn(d.action["cell"], s["danger_cells"])

    def test_mageroyal_for_observed_poison(self):
        s = state()
        add_seed(s, "mageroyal")
        s["hero"]["buffs"] = [{"name": "poison"}]
        self.assertEqual("seed: prepare mageroyal", SurvivalPolicy().choose(s).reason)

    def test_seed_cooldown_prevents_repeated_traps(self):
        s, p = self.corridor(), SurvivalPolicy()
        add_seed(s, "sorrowmoss")
        s["objects"] = [{"cell": 26, "name": "sewer crab"}]
        p.choose(s)
        p.target = None
        self.assertNotIn("pursuit trap", p.choose(s).reason)

    def test_blindweed_splits_multiple_pursuers(self):
        s, p = self.corridor(), SurvivalPolicy()
        add_seed(s, "blindweed")
        s["objects"] = [{"cell": 25, "name": "sewer crab"}, {"cell": 26, "name": "gnoll scout"}]
        self.assertEqual("seed: blindweed pursuit trap", p.choose(s).reason)
        self.assertEqual(24, p.target)

    def test_moving_abandons_seed_activation_plan(self):
        s, p = state(), SurvivalPolicy()
        p.seed_plan = {"kind": "earthroot", "cell": 23, "stage": "activate"}
        p.choose(s)
        self.assertIsNone(p.seed_plan)

    def test_seed_plan_does_not_spam_activation_if_plant_is_missing(self):
        s, p = state(), SurvivalPolicy()
        p.seed_plan = {"kind": "earthroot", "cell": 24, "stage": "activate"}
        self.assertNotIn("activate", p.choose(s).reason)
        self.assertIsNone(p.seed_plan)
