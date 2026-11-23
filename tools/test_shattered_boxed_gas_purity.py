"""Reduced run 000213 D766 public inputs (log line 2301), not a replay.

The newly opened gas threshold has a mimic on its only clear exit. Fixture
bookkeeping is fresh selector state, not recovered original runtime memory.
"""
import copy
import unittest
from unittest.mock import patch

from tools.policy_decision import Finished
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.toxic_escape import escape


GAS = "A greenish cloud of toxic gas is swirling here."


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=1024, hp=30, max_hp=30, level=3, strength=11,
                     buffs=[{"name": "hungry"}])
    groups = {
        4: [912,913,914,915,916,917,919,920,922,947,954,982,989,
            1017,1052,1059,1087,1094,1122,1123,1124,1125,1126,1127,1128,1129],
        1: [949,950,952,953,983,985,986,987,1018,1019,1053,1054,1055,
            1088,1089,1090,1091,1092],
        20: [948,951],
        19: [984,1020,1022,1056,1057],
        29: [988,1023,1058,1093],
        25: [1021],
        6: [1024],
        14: [1025,1026,1061,1096],
        0: [990,992,1060,1095],
    }
    s["map"] = dict(width=35, height=51, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True,
             effects=[GAS] if t in {1,19,20,29} or c == 1024 else [],
             **({"trap": "toxic vent"} if t == 19 else {}))
        for t, cells in groups.items() for c in cells])
    for tile in s["map"]["cells"]:
        if tile["cell"] in {919,920,954,1094,1128,1129}:
            tile["visible"] = False
            tile.pop("effects")
    s["objects"] = [
        dict(cell=986, name="Chest"), dict(cell=1020, name="Chest"),
        dict(cell=1054, name="Skeletal remains"),
        dict(cell=1025, name="mimic", health_bar=[15,21], status_icons=[]),
        dict(cell=1096, name="gnoll scout", status_icons=[])]
    s["inventory"] = [
        dict(id="item-9", name="potion of purity", identified=True, quantity=1,
             actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-10", name="crimson potion", identified=False, quantity=1,
             actions=["DROP", "THROW", "DRINK"])]
    p = verified()
    p.update(s)
    return s, p


class BoxedGasPurityTests(unittest.TestCase):
    def test_boxed_cloud_selects_known_clearance_not_terminal_stop(self):
        for full in (False, True):
            s, p = fixture()
            before = copy.deepcopy(s)
            try:
                d = p.choose(s) if full else escape(p, s)
            except Finished:
                d = None
            self.assertIsNotNone(d, "Known purity self-splash must precede gas exhaustion")
            self.assertEqual(dict(type="item", id="item-9", action="THROW"), d.action)
            self.assertEqual(1024, p.target)
            self.assertEqual("emergency", d.potion_purpose)
            if full:
                self.assertEqual("toxic-gas-escape", d.controller)
            self.assertEqual(before, s)
            self.assertIsNone(p.room_supply_permit)
            self.assertIsNone(p.room_journey)
            self.assertFalse(p.room_supply_spent_elsewhere)
            self.assertFalse(p.loot_collection_receipts)
            self.assertFalse(p.cleared_floors)
            self.assertIn(986, p.loot)

    def test_unknown_unthrowable_or_empty_dose_does_not_authorize_rescue(self):
        for change in ({"name": "golden potion", "identified": False},
                       {"identified": False}, {"actions": ["DRINK"]},
                       {"quantity": 0}):
            s, p = fixture()
            s["inventory"][0].update(change)
            with self.subTest(change=change), self.assertRaises(Finished):
                escape(p, s)

    def test_unshatterable_or_unsafe_origin_preserves_stop(self):
        for terrain in (0,24,18):
            s, p = fixture()
            p.tiles[1024]["terrain"] = terrain
            with self.subTest(terrain=terrain), self.assertRaises(Finished):
                escape(p, s)

    def test_observation_hazards_and_action_veto_still_apply(self):
        for change in ("unseen", "unobserved", "plant", "trap", "warning",
                       "paralysis", "vertigo", "veto"):
            s, p = fixture()
            tile = p.tiles[1024]
            if change == "unseen":
                tile["visible"] = False
            elif change == "unobserved":
                tile["observed"] = False
            elif change == "plant":
                tile["plant"] = "firebloom"
            elif change == "trap":
                tile["trap"] = "burning trap"
            elif change == "warning":
                s["danger_cells"] = [1024]
            elif change in {"paralysis", "vertigo"}:
                s["hero"]["buffs"].append({"name": change})
            with patch.object(p, "item_action_allowed", return_value=change != "veto"):
                with self.subTest(change=change), self.assertRaises(Finished):
                    escape(p, s)
            self.assertIsNone(p.room_supply_permit)

    def test_observed_clear_step_preserves_purity(self):
        s, p = fixture()
        s["objects"] = [o for o in s["objects"] if o["cell"] != 1025]
        p.room_blocked.discard(1025)
        self.assertEqual(dict(type="cell", cell=1025), escape(p, s).action)
        self.assertIsNone(p.room_supply_permit)


if __name__ == "__main__":
    unittest.main()
