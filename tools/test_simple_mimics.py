import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision
from tools.policy_runtime import Transaction
from tools.test_bot_profiles import ready
from tools import test_environment_quest as fixtures
from tools.room_tactics import investigate_suspect_container
from tools.policy_geometry import distance


class SimpleMimicTests(unittest.TestCase):
    def test_profile_retains_mimics_without_enabling_quests_or_room_objectives(self):
        _, p = ready()
        self.assertTrue(p.profile.mimic_investigation)
        self.assertFalse(p.profile.quests)
        self.assertFalse(p.profile.special_rooms)
        self.assertFalse(p.profile.full_exploration)
        self.assertFalse(p.profile.secret_hunting)

    def test_shared_preparation_calls_investigation_charge_and_active_hunt(self):
        for selected in ("hunt_missing_mimic", "charge_suspect_container", "investigate_suspect_container"):
            s, p = ready()
            action = Decision({"type": "wait"}, "shared mimic test")
            with patch("tools.mage_policy.hunt_missing_mimic",
                       return_value=action if selected == "hunt_missing_mimic" else None) as hunt, \
                    patch("tools.mage_policy.charge_suspect_container",
                          return_value=action if selected == "charge_suspect_container" else None) as charge, \
                    patch("tools.mage_policy.investigate_suspect_container",
                          return_value=action if selected == "investigate_suspect_container" else None) as inspect:
                self.assertIs(action, p.preparation(s, []), selected)
                {"hunt_missing_mimic": hunt, "charge_suspect_container": charge,
                 "investigate_suspect_container": inspect}[selected].assert_called_once()

    def encounter(self):
        s, _ = fixtures.EnvironmentTests().setup_arena()
        p = MagePolicy(profile="simple-bot")
        p.challenges_verified = True
        p.update(s)
        p.tiles[39]["terrain"] = 6
        p.loot[43] = {"name": "Locked chest", "cell": 43,
                      "description": "Something about this chest feels off... Trying to open it might be a bad idea."}
        return s, p

    def test_suspicious_golden_chest_gets_ranged_probe_not_key_open_or_collection_credit(self):
        s, p = self.encounter()
        action = investigate_suspect_container(p, s, [], distance)
        self.assertIsNotNone(action)
        self.assertEqual("ZAP", action.action["action"])
        self.assertEqual(43, p.target)
        self.assertTrue(p.mimic_obligations)
        self.assertFalse(p.loot_collection_receipts)
        self.assertEqual(0, p.keys.get("golden", 0))

    def test_low_health_combat_and_rejected_probe_keep_shared_safety(self):
        for case in ("health", "enemy", "rollback"):
            s, p = self.encounter()
            if case == "health":s["hero"]["hp"] = 10
            transaction = Transaction(p)
            action = investigate_suspect_container(p, s, [{"name": "rat", "cell": 41}] if case == "enemy" else [], distance)
            if case == "rollback":
                self.assertIsNotNone(action)
                transaction.rollback()
                self.assertFalse(p.mimic_obligations)
                self.assertFalse(p.room_attempts)
            else:
                self.assertIsNone(action, case)

    def test_mimic_hunt_observer_runs_in_simple_update(self):
        s, p = ready()
        with patch("tools.mage_policy.observe_hunts") as observer:
            p.update(s)
        observer.assert_called_once()
