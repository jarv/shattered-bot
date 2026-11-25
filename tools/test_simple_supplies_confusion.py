import copy
import unittest

from tools.bot_profiles import resolve
from tools.test_bot_profiles import ready
from tools.simple_navigation import choose, before_descent, accepted, observe
from tools.garden_tactics import GARDEN_DESCRIPTION
from tools.policy_decision import Decision, Intent, PlannerStuck
from tools.policy_runtime import Transaction
from tools import test_shattered_vertigo_response as gas_fixture
from tools.vertigo_tactics import choose as vertigo_choice, observe as observe_vertigo, MAX_GAS_WAITS


class SimpleSupplyTests(unittest.TestCase):
    def test_observed_dewcatcher_and_seedpod_preempt_level_gain_descent(self):
        for plant in ("Dewcatcher", "Seed Pod"):
            s, p = ready()
            s["hero"]["level"] += 1
            p.tiles[23].update(plant=plant, observed=True, effects=[GARDEN_DESCRIPTION])
            action = choose(p, s, [])
            self.assertEqual(23, action.action["cell"])
            self.assertIn("harvest", action.reason)
            gate = before_descent(p, s, Decision({"type": "cell", "cell": 25}, "leave", Intent.DESCEND))
            self.assertEqual(23, gate.action["cell"])
            self.assertFalse(p.loot_collection_receipts)

    def test_harvest_has_accepted_only_limits_and_does_not_credit_drops(self):
        s, p = ready()
        p.tiles[23].update(plant="Dewcatcher", observed=True)
        action = choose(p, s, [])
        after = copy.deepcopy(s)
        after["hero"]["cell"] = 23
        transaction = Transaction(p)
        accepted(p, s, action, after)
        transaction.rollback()
        self.assertFalse(observe(p, s).get("harvest_attempts"))
        accepted(p, s, action, after)
        self.assertEqual(1, observe(p, s)["harvest_attempts"][23])
        self.assertFalse(p.loot_collection_receipts)

    def test_armed_traps_other_plants_and_combat_do_not_get_harvest_exception(self):
        from tools.simple_navigation import harvest_supplies
        for case in ("trap", "harmful", "enemy", "budget"):
            s, p = ready()
            p.tiles[23].update(plant="Seed Pod", observed=True)
            if case == "trap":p.tiles[23].update(terrain=18, trap="summoning trap")
            elif case == "harmful":p.tiles[23]["plant"] = "blindweed"
            elif case == "budget":observe(p, s)["harvest_inputs"] = 64
            self.assertIsNone(harvest_supplies(p, s, [{"name": "rat"}] if case == "enemy" else []), case)


class SimpleConfusionWaitTests(unittest.TestCase):
    def blocked_gas(self):
        s, p = gas_fixture.run54()
        p.profile = resolve("simple-bot")
        p.tiles[791].update(terrain=0, effects=[])
        return s, p

    def test_confusion_on_known_ground_with_chasm_neighbor_waits_instead_of_random_move(self):
        s, p = self.blocked_gas()
        for _ in range(MAX_GAS_WAITS):
            action = vertigo_choice(p, s)
            self.assertEqual({"type": "wait"}, action.action)
            self.assertEqual("gas-wait", action.vertigo_kind)
            observe_vertigo(p, s, action, copy.deepcopy(s))
        with self.assertRaises(PlannerStuck):
            vertigo_choice(p, s)

    def test_damaging_mixed_cloud_or_visible_threat_still_prevents_wait(self):
        for case in ("toxic", "enemy", "harm", "low-health"):
            s, p = self.blocked_gas()
            if case == "toxic":p.tiles[790]["effects"].append("A cloud of toxic gas")
            elif case == "enemy":s["objects"] = [{"name": "marsupial rat", "cell": 744}]
            elif case == "harm":p.unseen_damage_turns = 1
            else:s["hero"]["hp"] = 1
            try:
                action = vertigo_choice(p, s)
            except PlannerStuck:
                continue
            self.assertNotEqual("gas-wait", getattr(action, "vertigo_kind", None), case)
