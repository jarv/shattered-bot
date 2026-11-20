"""Reduced public-input fixture for run 000003 decision 1135.

This probes arbitration only; no hit, kill, or safe retreat is assumed.
"""
from collections import Counter
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.policy_nodes import critical_withdrawal
from tools.policy_runtime import Context
from tools.policy_decision import Decision, Intent


class CausticFinisherTests(unittest.TestCase):
    def fixture(self):
        # Public decision 1135: empty staff, 18/40 HP, adjacent caustic
        # slime with a rendered 1/19 health bar. No ooze remains.
        s = {
            "depth": 4, "map": {"width": 55},
            "hero": {"cell": 1074, "hp": 18, "max_hp": 40,
                     "buffs": [{"name": "starving"}, {"name": "barrier"}]},
            "inventory": [],
        }
        foe = {"name": "caustic slime", "cell": 1130,
               "health_bar": [1, 19]}
        p = SimpleNamespace(
            depth=4, snake_melee_attempts=Counter(), critical_retreats=0,
            charged_magic=Mock(return_value=[]),
            retreat=Mock(side_effect=lambda *a: Decision(
                {"type": "cell", "cell": 1020}, "combat: retreat",
                intent=Intent.RETREAT)),
        )
        return Context(p, s, enemies=[foe], active=[foe])

    def test_nearly_dead_caustic_slime_reaches_existing_combat_arbitration(self):
        c = self.fixture()
        self.assertIsNone(critical_withdrawal(c))
        c.policy.retreat.assert_not_called()
        self.assertEqual(1, sum(c.policy.snake_melee_attempts.values()))

    def test_two_attempt_limit_still_withdraws_on_third_probe(self):
        c = self.fixture()
        self.assertIsNone(critical_withdrawal(c))
        self.assertIsNone(critical_withdrawal(c))
        self.assertEqual(Intent.RETREAT, critical_withdrawal(c).intent)
        self.assertEqual(2, sum(c.policy.snake_melee_attempts.values()))

    def test_health_bar_health_and_crowding_gates_remain(self):
        for mode in ("critical", "healthy_foe", "missing_bar", "crowded"):
            with self.subTest(mode=mode):
                c = self.fixture()
                if mode == "critical":
                    c.state["hero"]["hp"] = 9
                elif mode == "healthy_foe":
                    c.active[0]["health_bar"] = [4, 19]
                elif mode == "missing_bar":
                    del c.active[0]["health_bar"]
                else:
                    c.active.append({"name": "slime", "cell": 1073})
                self.assertEqual(Intent.RETREAT, critical_withdrawal(c).intent)
                self.assertFalse(c.policy.snake_melee_attempts)

    def test_no_extension_to_special_enemies(self):
        c = self.fixture()
        c.active[0]["name"] = "great crab"
        self.assertEqual(Intent.RETREAT, critical_withdrawal(c).intent)


if __name__ == "__main__":
    unittest.main()
