import copy
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.ordinary_traps import choose, footprint, accepted, burning_footprint
from tools.policy_runtime import Transaction
from tools.policy_decision import Finished
from tools.payload_workflow import PayloadPhase
from tools.test_survival_bot import state


def corridor():
    s = state()
    s["hero"]["cell"] = 31
    s["inventory"].append({"id": "dew", "name": "waterskin", "actions": ["THROW"], "status": "0/20"})
    s["map"] = {"width": 9, "height": 9, "cells": [
        {"cell": c, "terrain": 1 if c % 9 == 4 and 1 <= c // 9 <= 7 else 4,
         "visible": True, "observed": True, "effects": []} for c in range(81)]}
    next(t for t in s["map"]["cells"] if t["cell"] == 49).update(terrain=18, trap="flock trap")
    next(t for t in s["map"]["cells"] if t["cell"] == 67)["terrain"] = 8
    p = MagePolicy(profile="simple-bot")
    p.update(s)
    return s, p


class OrdinaryTrapTests(unittest.TestCase):
    def burning_corridor(self):
        s, p = corridor()
        s["hero"]["cell"] = 22
        next(t for t in s["map"]["cells"] if t["cell"] == 49)["trap"] = "burning trap"
        p.update(s)
        return s, p

    def test_blocking_burning_trap_uses_waterskin_from_outside_fire_radius(self):
        s, p = self.burning_corridor()
        action = choose(p, s, [])
        self.assertEqual({"type": "item", "id": "dew", "action": "THROW"}, action.action)
        self.assertEqual(49, p.target)
        self.assertFalse(p.trap_payload_return.dropped)
        self.assertEqual(18, p.tiles[49]["terrain"])

    def test_remote_fire_checks_collateral_unknown_geometry_fuel_and_other_traps(self):
        for case in ("fuel", "loot", "ally", "unknown", "summoning"):
            s, p = self.burning_corridor()
            if case == "fuel":p.tiles[48]["terrain"] = 27
            elif case == "loot":p.loot[48] = {"name": "scroll of upgrade"}
            elif case == "ally":s["objects"] = [{"name": "sad ghost", "cell": 48}]
            elif case == "unknown":p.tiles[48]["observed"] = False
            else:p.tiles[48].update(terrain=18, trap="summoning trap")
            self.assertIsNone(burning_footprint(p, s, 49), case)

    def test_remote_fire_waits_are_bounded_and_do_not_credit_payload_retrieval(self):
        s, p = self.burning_corridor()
        choose(p, s, [])
        p.trap_payload_return.phase = PayloadPhase.LANDED
        p.trap_payload_return.dropped["waterskin"] = 1
        p.tiles[49].update(terrain=19, effects=["A fire is raging here."])
        for _ in range(16):
            action = choose(p, s, [])
            self.assertEqual({"type": "wait"}, action.action)
            accepted(p, s, action, s)
        with self.assertRaises(Finished):
            choose(p, s, [])
        self.assertTrue(p.trap_payload_return.outstanding)

    def test_observed_blocking_flock_uses_owned_payload_not_direct_entry(self):
        s, p = corridor()
        action = choose(p, s, [])
        self.assertEqual({"type": "item", "id": "dew", "action": "THROW"}, action.action)
        self.assertEqual(49, p.target)
        self.assertEqual(PayloadPhase.PROPOSED, p.trap_payload_return.phase)
        self.assertFalse(p.trap_payload_return.dropped)
        self.assertEqual(18, p.tiles[49]["terrain"])  # Planning did not disarm.
        self.assertIsNotNone(p.physical_ledger.entries.get(p.trap_payload_return.owner))

    def test_unknown_footprint_and_secondary_traps_veto_activation(self):
        for kind in ("unknown", "secondary", "plant", "effect", "actor"):
            s, p = corridor()
            if kind == "unknown":
                p.tiles.pop(57)
            elif kind == "secondary":
                p.tiles[58].update(terrain=18, trap="summoning trap")
            elif kind == "plant":
                p.tiles[58]["plant"] = "firebloom"
            elif kind == "effect":
                p.tiles[58]["effects"] = ["A cloud of toxic gas"]
            else:
                s["objects"] = [{"name": "rat", "cell": 58}]
            self.assertIsNone(footprint(p, s, 49), kind)

    def test_other_trap_types_and_no_reusable_item_do_not_get_a_blanket_exception(self):
        for kind in ("other-trap", "no-payload"):
            s, p = corridor()
            if kind == "other-trap":
                p.tiles[49]["trap"] = "explosive trap"
            else:
                s["inventory"] = [s["inventory"][0]]
            action = choose(p, s, [])
            self.assertTrue(action is None or action.action.get("action") != "THROW")
            self.assertIsNone(p.trap_payload_return)

    def test_sheep_wait_budget_is_accepted_only_and_keeps_custody(self):
        s, p = corridor()
        choose(p, s, [])
        p.trap_payload_return.phase = PayloadPhase.LANDED
        p.trap_payload_return.dropped["waterskin"] = 1
        p.tiles[49].update(terrain=19, trap=None)
        s["objects"] = [{"name": "sheep", "cell": 49}]
        action = choose(p, s, [])
        self.assertEqual({"type": "wait"}, action.action)
        plan = p.simple_floors[(1, 0)]["ordinary_trap"]
        self.assertEqual(0, plan["waits"])
        transaction = Transaction(p)
        accepted(p, s, action, s)
        transaction.rollback()
        self.assertEqual(0, p.simple_floors[(1, 0)]["ordinary_trap"]["waits"])
        for _ in range(12):
            accepted(p, s, action, s)
        with self.assertRaises(Finished):
            choose(p, s, [])
        self.assertTrue(p.trap_payload_return.outstanding)

    def test_active_threats_do_not_start_ordinary_trap_work(self):
        s, p = corridor()
        self.assertIsNone(choose(p, s, [{"name": "rat", "cell": 22}]))
        self.assertIsNone(p.trap_payload_return)
