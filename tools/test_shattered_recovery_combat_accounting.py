"""Reduced public run 203 D3001-D3008 inputs; not recovered policy memory."""
import copy
import unittest

from tools.floor_abandonment import FloorAbandonment
from tools.policy_decision import Decision, Intent, PlannerStuck


def fixture():
    # Only bookkeeping is under test; no navigation or game actions execute.
    recovery = FloorAbandonment(None)
    recovery.active = dict(id=1, depth=7, branch=0, target=511,
                           accepted_actions=4, stalled_actions=0,
                           best_distance=21, last_distance=21, status="active",
                           collection_credited=False)
    state = dict(status="ready", modal=False, depth=7, branch=0,
                 hero=dict(cell=496, hp=65, max_hp=65, buffs=[]),
                 objects=[dict(name="crazy thief", cell=539)],
                 danger_cells=[])
    return recovery, state


class RecoveryCombatAccountingTests(unittest.TestCase):
    def test_combat_and_target_selection_are_not_failed_descent_steps(self):
        recovery, state = fixture()
        before = copy.deepcopy(state)
        actions = [
            dict(type="item", id="item-0", action="ZAP"),
            dict(type="cell", cell=583),
            dict(type="item", id="item-10", action="THROW"),
            dict(type="cell", cell=539),
            dict(type="item", id="item-10", action="THROW"),
            dict(type="cell", cell=539),
            dict(type="item", id="item-9", action="THROW"),
            dict(type="cell", cell=539),
        ]
        for action in actions:
            recovery.observe(state, Decision(action, "combat or target"), state)
        self.assertEqual(12, recovery.active["accepted_actions"])
        self.assertEqual(0, recovery.active["stalled_actions"],
                         "Survival arbitration did not attempt a descent step")
        self.assertIsNone(recovery.next(state))  # Combat still preempts transit.
        self.assertEqual(before, state)
        self.assertFalse(recovery.active["collection_credited"])

    def test_failed_recovery_steps_still_exhaust_eight_input_limit(self):
        recovery, state = fixture()
        decision = Decision(dict(type="cell", cell=539), "recovery",
                            intent=Intent.DESCEND)
        decision.floor_abandonment = 1
        for _ in range(8):
            recovery.observe(state, decision, state)
        self.assertEqual(8, recovery.active["stalled_actions"])
        with self.assertRaises(PlannerStuck):
            recovery.next(state)

    def test_interruptions_still_exhaust_total_input_limit(self):
        recovery, state = fixture()
        for _ in range(60):
            recovery.observe(state, Decision(dict(type="cell", cell=539), "target"), state)
        with self.assertRaises(PlannerStuck):
            recovery.next(state)

    def test_nonrecovery_movement_cannot_claim_descent_progress(self):
        recovery, state = fixture()
        recovery.active["stalled_actions"] = 3
        after = copy.deepcopy(state)
        after["hero"]["cell"] = 539
        recovery.observe(state, Decision(dict(type="cell", cell=539), "combat",
                                         intent=Intent.RETREAT), after)
        self.assertEqual(3, recovery.active["stalled_actions"])
        self.assertEqual(21, recovery.active["best_distance"])

    def test_unowned_transition_cannot_claim_recovery_success(self):
        recovery, state = fixture()
        after = copy.deepcopy(state)
        after["depth"] = 8
        recovery.observe(state, Decision(dict(type="cell", cell=511), "other"), after)
        self.assertIsNotNone(recovery.active)
        self.assertEqual("active", recovery.active["status"])
        self.assertFalse(recovery.active["collection_credited"])

    def test_death_during_interruption_still_ends_recovery(self):
        recovery, state = fixture()
        incident = recovery.active
        after = copy.deepcopy(state)
        after["hero"]["hp"] = 0
        recovery.observe(state, Decision(dict(type="cell", cell=539), "combat"), after)
        self.assertIsNone(recovery.active)
        self.assertEqual("died", incident["status"])


if __name__ == "__main__":
    unittest.main()
