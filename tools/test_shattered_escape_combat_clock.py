"""Run 100: paid melee turns must age the bounded escape commitment."""
import copy
import unittest
from types import SimpleNamespace

from tools.escape_commitment import observe, reverses
from tools.policy_decision import Decision


def fixture(age=10):
    # Minimal derivative of decisions 2735–2738 public inputs, not run memory.
    state = {
        "hero": {"cell": 1546, "hp": 42, "max_hp": 60},
        "evaluation_stats": {"elapsed_turns": 2652},
        "inventory": [{"name": "staff of magic missile +3", "status": "0/5"}],
        "objects": [{"name": "skeleton", "cell": 1497}],
    }
    policy = SimpleNamespace(escape_commitment={
        "edges": [(1497, 1546)], "hp": 44, "charges": 0, "age": age})
    return policy, state


class EscapeCombatClockTests(unittest.TestCase):
    def test_paid_melee_ages_and_expires_even_without_damage_or_charge_change(self):
        p, before = fixture()
        attack = Decision({"type": "cell", "cell": 1497}, "combat: melee")
        self.assertTrue(reverses(p, before, 1497))
        after = copy.deepcopy(before)
        after["evaluation_stats"]["elapsed_turns"] += 1
        observe(p, before, attack, after, True)
        self.assertEqual(11, p.escape_commitment["age"])
        later = copy.deepcopy(after)
        later["evaluation_stats"]["elapsed_turns"] += 1
        observe(p, after, attack, later, True)
        self.assertIsNone(p.escape_commitment)
        self.assertFalse(reverses(p, later, 1497))

    def test_free_targeting_or_inspection_does_not_spend_commitment(self):
        p, before = fixture(age=11)
        decision = Decision({"type": "cell", "cell": 1497}, "target selection")
        observe(p, before, decision, copy.deepcopy(before), True)
        self.assertEqual(11, p.escape_commitment["age"])
        self.assertTrue(reverses(p, before, 1497))

    def test_clock_is_optional_and_no_elapsed_time_is_invented(self):
        for value in (None, {}, {"elapsed_turns": None}):
            with self.subTest(value=value):
                p, before = fixture(age=11)
                before["evaluation_stats"] = value
                observe(p, before, Decision({"type": "cell", "cell": 1497}, "melee"),
                        copy.deepcopy(before), True)
                self.assertEqual(11, p.escape_commitment["age"])

    def test_existing_movement_and_wait_receipts_still_count_once(self):
        for action in ({"type": "wait"}, {"type": "cell", "cell": 1595}):
            with self.subTest(action=action):
                p, before = fixture(age=9)
                after = copy.deepcopy(before)
                after["evaluation_stats"]["elapsed_turns"] += 1
                if action["type"] == "cell":
                    after["hero"]["cell"] = 1595
                observe(p, before, Decision(action, "accepted"), after, True)
                self.assertEqual(10, p.escape_commitment["age"])


if __name__ == "__main__":
    unittest.main()
