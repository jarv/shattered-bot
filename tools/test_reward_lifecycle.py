import copy
import unittest

from tools.reward_lifecycle import RewardLifecycle, ReturnPhase, lifecycle
from tools.room_tactics import Journey
from tools.loot_completion import observe_collected
from tools.policy_decision import Decision, Intent
from tools.test_protected_reward_tours import gas_room


class RewardLifecycleTests(unittest.TestCase):
    def test_hypothesis_is_not_protection_or_owned_stock(self):
        work = RewardLifecycle(2, 0, "gas", 10, {11})
        state = {"depth": 2, "hero": {"cell": 10}}
        work.observe(state, 0)
        self.assertEqual(ReturnPhase.HYPOTHESIS, work.phase)
        self.assertFalse(work.record()["owned_item_debt"])
        work.cancel()
        self.assertEqual(ReturnPhase.CANCELLED, work.phase)
        self.assertEqual([11], work.record()["uncollected"])

    def test_return_does_not_certify_collection(self):
        work = RewardLifecycle(2, 0, "gas", 10, {11})
        state = {"depth": 2, "hero": {"cell": 10}}
        work.observe(state, 20)
        state["hero"]["cell"] = 11
        work.observe(state, 19)
        work.cancel()
        self.assertEqual(ReturnPhase.EXPOSED, work.phase)
        with self.assertRaises(ValueError):
            work.returned(state)
        state["hero"]["cell"] = 10
        work.returned(state)
        self.assertEqual(ReturnPhase.RETURNED, work.phase)
        self.assertEqual([11], work.record()["uncollected"])

    def test_scope_change_never_returns_or_collects(self):
        work = RewardLifecycle(2, 0, "gas", 10, {11})
        work.observe({"depth": 2, "branch": 1, "hero": {"cell": 10}}, 20)
        self.assertEqual(ReturnPhase.INTERRUPTED, work.phase)
        self.assertFalse(work.receipts)

    def test_controller_and_history_share_one_transactional_object(self):
        state, p = gas_room()
        trip = p.room_journey = Journey("gas", [38, 39, 40], state["depth"])
        work = lifecycle(p, trip)
        self.assertIs(work, lifecycle(p, trip))
        self.assertIs(work, p.reward_lifecycles[0])
        saved = copy.deepcopy((p.memory, trip))
        self.assertIs(saved[0].run.reward_lifecycles[0], saved[1].lifecycle)
        p.memory.reset_floor(38)
        self.assertIs(work, p.reward_lifecycles[0])

    def test_old_goals_accept_only_scoped_inventory_backed_pickup(self):
        state, p = gas_room()
        p.room_journey = Journey("gas", [38, 39, 40], state["depth"])
        work = lifecycle(p, p.room_journey)
        p.room_journey = None
        before = copy.deepcopy(state)
        before["objects"] = [{"cell": 40, "name": "gold", "top_item": {"name": "gold", "quantity": 10}}]
        after = copy.deepcopy(before)
        after["objects"] = []
        action = Decision({"type": "cell", "cell": 40}, "collect", Intent.LOOT)
        observe_collected(p, before, action, after)
        self.assertFalse(work.receipts)
        after["hero"]["gold"] = before["hero"].get("gold", 0) + 10
        after["branch"] = 1
        observe_collected(p, before, action, after)
        self.assertFalse(work.receipts)
        after["branch"] = 0
        observe_collected(p, before, action, after)
        self.assertEqual({40}, work.receipts)


if __name__ == "__main__":
    unittest.main()
