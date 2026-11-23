"""Run 207 D659: reduced public geometry, not a changed-action continuation."""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=946, hp=30, max_hp=30)
    # Public water bank, closed door and observed alternative hiding bank.
    # Unrelated terrain is omitted; no enemy arrival route is asserted.
    terrain = {946: 29, 978: 29, 979: 5, 724: 29}
    s["map"] = {"width": 32, "height": 50, "cells": [
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()]}
    s["objects"] = [dict(cell=724, name="gnoll scout",
                         status_icons=["chilled"])]
    p = MagePolicy()
    p.update(s)
    return p, s


class DoorwayApproachBankTests(unittest.TestCase):
    def test_fresh_lure_does_not_choose_its_own_reverse_approach_bank(self):
        p, s = fixture()
        d = p.door_ambush(s, s["objects"], s["objects"], kind="doorway")
        self.assertEqual({"type": "cell", "cell": 979}, d.action)
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual(978, p.ambush_plan["hide"],
                         "The approach bank would require a protected reverse edge")
        self.assertEqual(0, p.ambush_plan["waits"])
        self.assertEqual(10, p.ambush_plan["arrival_budget"])
        self.assertIsNone(p.escape_commitment)  # A proposal is not an accepted move.
        self.assertIsNone(p.doorway_hold)
        self.assertFalse(p.loot_collection_receipts)

    def test_no_alternative_means_decline_not_unexecutable_lure(self):
        p, s = fixture()
        p.tiles[978]["terrain"] = 4
        self.assertIsNone(p.door_ambush(s, s["objects"], s["objects"], kind="doorway"))
        self.assertIsNone(p.ambush_plan)

    def test_hazardous_alternative_is_not_admitted(self):
        for effect in ("cloud of toxic gas", "A fire is raging here."):
            with self.subTest(effect=effect):
                p, s = fixture()
                p.tiles[978]["effects"] = [effect]
                self.assertIsNone(p.door_ambush(s, s["objects"], s["objects"], kind="doorway"))
                self.assertIsNone(p.ambush_plan)

    def test_owned_plan_is_not_rewritten(self):
        p, s = fixture()
        p.ambush_plan = dict(door=979, hide=946, waits=0, kind="doorway")
        d = p.door_ambush(s, s["objects"], s["objects"], kind="doorway")
        self.assertEqual({"type": "wait"}, d.action)
        self.assertEqual(946, p.ambush_plan["hide"])


if __name__ == "__main__":
    unittest.main()
