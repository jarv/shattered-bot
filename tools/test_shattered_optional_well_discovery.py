"""Run 160 D208: optional well preparation must not own unknown colors.

Reduced deterministic public contract, not reconstructed runtime memory:
one unknown crimson dose, no known fall protection, and a distant well.
The ordinary test-bank geometry is synthetic; it does not certify the
recorded terminal position's bank or a successful drop/discovery.
"""
import unittest

from tools.descent_potions import begin
from tools.policy_decision import PlannerStuck
from tools.room_completion import obligations
from tools.room_supplies import allowed, discovery_requirements, requirements
from tools.test_shattered_strength_before_descent import ready


def fixture():
    s, p = ready(bag=False)
    s["inventory"][-1].update(id="crimson", name="crimson potion")
    s["map"]["cells"][12].update(terrain=0, name="Distant well")
    p.update(s)
    return s, p


class OptionalWellDiscoveryTests(unittest.TestCase):
    def test_missing_optional_drop_supply_does_not_block_admitted_discovery(self):
        s, p = fixture()
        self.assertEqual(["fall"], [d.kind for d in requirements(p, s)])
        try:
            decision = begin(p, s)
        except PlannerStuck as error:
            self.fail("Optional well held mandatory discovery hostage: " + error.blocker)
        self.assertEqual({"type": "item", "id": "crimson", "action": "DRINK"},
                         decision.action)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(p.drop_plan)
        self.assertEqual(0, p.tiles[12]["terrain"])
        self.assertNotIn(12, p.paths(s))
        self.assertIn({"kind": "uncompleted distant-well drop", "cell": 12},
                      obligations(p, s))
        self.assertTrue(p.deferred_obligations)
        self.assertFalse(p.descent_counts_as_clear())

    def test_known_fall_protection_remains_reserved(self):
        for name in ("elixir of feather fall", "potion of cleansing"):
            s, p = fixture()
            item = dict(id="protection", name=name, quantity=1, identified=True,
                        actions=["DRINK", "THROW", "DROP"])
            s["inventory"].append(item)
            p.update(s)
            discovery_requirements(p, s)
            self.assertEqual([name], [d.potion for d in requirements(p, s)
                                     if d.kind == "fall"])
            self.assertFalse(allowed(p, item, "DRINK"))
            self.assertFalse(allowed(p, item, "THROW"))

    def test_actual_flight_reward_keeps_its_unknown_supply(self):
        s, p = fixture()
        s["map"]["cells"][14].update(terrain=18, trap="disintegration trap")
        p.update(s)
        p.loot[14] = dict(cell=14, name="scroll of upgrade",
                         top_item=dict(name="scroll of upgrade", identified=True))
        self.assertIn("flight", [d.kind for d in discovery_requirements(p, s)])
        self.assertNotIn(14, p.paths(s))
        self.assertIn(14, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_no_bank_is_not_permission_to_drink_or_descend(self):
        s, p = fixture()
        s["map"]["cells"][60]["terrain"] = 1
        p.update(s)
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.puzzle_probe)

    def test_health_and_owned_drop_retrieval_still_block_testing(self):
        for condition in ("health", "drop"):
            s, p = fixture()
            if condition == "health":
                s["hero"]["hp"] = 5
            else:
                p.drop_plan = dict(depth=1, cell=12, stage="confirm")
            with self.assertRaises(PlannerStuck):
                begin(p, s)
            self.assertIsNone(p.puzzle_probe)
            self.assertFalse(p.strength_identified)

    def test_strict_unfinished_loot_does_not_admit_discovery(self):
        s, p = fixture()
        p.stop_on_incomplete_loot = True
        p.loot[14] = dict(cell=14, name="scroll of upgrade")
        self.assertIsNone(begin(p, s))
        self.assertIsNone(p.descent_potion_plan)
        self.assertIn(14, p.loot)


if __name__ == "__main__":
    unittest.main()
