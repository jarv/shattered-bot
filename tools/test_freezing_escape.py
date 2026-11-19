import unittest

from tools.survival_bot import Finished, SurvivalPolicy
from tools.test_survival_bot import state


COLD = ["The air is unnaturally frigid here."]


class FreezingEscapeTests(unittest.TestCase):
    def corridor(self, exit_known=True):
        s = state()
        floors = {24, 25, 26} if exit_known else {24, 25}
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in floors else 4, "visible": True,
                               "effects": COLD if c in {24, 25} else []} for c in range(49)]
        return s

    def test_crosses_cold_to_reach_clear_ground(self):
        s = self.corridor()
        d = SurvivalPolicy().choose(s)
        self.assertEqual("room: retreat to safe ground", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_short_fire_escape_crosses_triggered_trap_not_active_trap(self):
        s = self.corridor()
        for tile in s["map"]["cells"]:
            if tile["cell"] in {24, 25}:
                tile["effects"] = ["A fire is raging here."]
        middle = next(t for t in s["map"]["cells"] if t["cell"] == 25)
        middle.update(terrain=19, trap="burning trap")
        self.assertEqual(25, SurvivalPolicy().choose(s).action["cell"])
        middle["terrain"] = 18
        with self.assertRaises(Finished):
            SurvivalPolicy().choose(s)

    def test_does_not_budget_fire_escape_as_harmless_cold(self):
        s = self.corridor()
        s["hero"]["hp"] = 8
        for tile in s["map"]["cells"]:
            if tile["cell"] in {24, 25}:
                tile["effects"] = ["A fire is raging here."]
        with self.assertRaises(Finished):
            SurvivalPolicy().choose(s)

    def test_leave_toxic_cloud_even_when_old_health_budget_would_decline(self):
        s = self.corridor()
        for tile in s["map"]["cells"]:
            if tile["cell"] in {24, 25}:
                tile["effects"] = ["A greenish cloud of toxic gas is swirling here."]
        self.assertEqual(25, SurvivalPolicy().choose(s).action["cell"])
        s["hero"]["hp"] = 7
        self.assertEqual(25, SurvivalPolicy().choose(s).action["cell"])

    def test_confusion_gas_waits_without_random_vertigo_movement(self):
        s, p = self.corridor(), SurvivalPolicy()
        s["hero"]["buffs"] = [{"name": "vertigo"}]
        for tile in s["map"]["cells"]:
            if tile["cell"] in {24, 25}:
                tile["effects"] = ["A cloud of confusion gas is swirling here."]
        self.assertEqual("wait", p.choose(s).action["type"])
        for tile in s["map"]["cells"]:
            tile["effects"] = []
        self.assertEqual("wait", p.choose(s).action["type"])
        s["hero"]["buffs"] = []
        p.choose(s)
        self.assertEqual(0, p.temporary_confusion_waits)

    def test_confusion_wait_is_bounded(self):
        s, p = self.corridor(), SurvivalPolicy()
        for tile in s["map"]["cells"]:
            if tile["cell"] in {24, 25}:
                tile["effects"] = ["A cloud of confusion gas is swirling here."]
        for _ in range(40):
            self.assertEqual("wait", p.choose(s).action["type"])
        with self.assertRaises(Finished):
            p.choose(s)

    def test_does_not_treat_toxic_gas_as_safe_freezing_air(self):
        s = self.corridor()
        next(t for t in s["map"]["cells"] if t["cell"] == 25)["effects"] = ["A cloud of toxic gas"]
        d = SurvivalPolicy().choose(s)
        self.assertNotEqual(25, d.action.get("cell"))

    def test_isolated_cold_wait_is_bounded(self):
        s, p = self.corridor(False), SurvivalPolicy()
        for _ in range(16):
            self.assertEqual("wait", p.choose(s).action["type"])
        with self.assertRaises(Finished):
            p.choose(s)

    def test_does_not_wait_under_enemy_pressure(self):
        s = self.corridor(False)
        s["objects"] = [{"cell": 25, "name": "sewer crab"}]
        with self.assertRaises(Finished):
            SurvivalPolicy().choose(s)

    def test_cleared_cold_resets_wait_budget(self):
        s, p = self.corridor(False), SurvivalPolicy()
        p.choose(s)
        for tile in s["map"]["cells"]:
            tile["effects"] = []
        p.update(s)
        p.escape_special_room(s)
        self.assertEqual(0, p.temporary_freeze_waits)
