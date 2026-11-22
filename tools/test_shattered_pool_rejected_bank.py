"""Reduced public pool geometry, run 000115 decisions 602 and 611–612.

Independent selector fixtures, not a reconstruction of recorded runtime memory.
The dry bank has one ordinary retreat square and a closed entrance; it fails
the existing drink-bank gate even with its entire neighborhood visible.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance, neighbors
from tools.piranha_tactics import observe, pending, staging_bank
from tools.puzzle_supplies import Demand, safe_test_bank, stage_known_pool


def approach(pos=1268):
    s = state()
    s["depth"] = 2
    s["hero"].update(cell=pos, hp=28, max_hp=30, strength=11, buffs=[])
    groups = {
        4: [1194,1195,1222,1223,1225,1226,1227,1228,1229,1230,1231,
            1259,1296,1303,1304,1305,1306,1307,1333,1370,1407,1482,1483],
        1: [1196,1233,1267,1268,1269,1270], 12: [1224], 20: [1232],
        29: [1260,1261,1262,1263,1264,1297,1298,1299,1300,1301,
             1334,1335,1336,1337,1338,1372,1373,1374,1375,
             1408,1409,1410,1411,1445,1446,1447],
        14: [1265,1302,1339], 5: [1266], 11: [1371],
    }
    visible = {1229,1230,1231,1232,1233,1266,1267,1268,1269,1270,
               1303,1304,1305,1306,1307}
    s["map"] = dict(width=37, height=42, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c in visible, effects=[])
        for t, cells in groups.items() for c in cells])
    s["objects"] = []
    potion = dict(id="invis", name="potion of invisibility", identified=True,
                  quantity=1, actions=["DROP", "THROW", "DRINK"])
    s["inventory"].append(potion)
    p = verified()
    p.update(s)
    p.piranha_rooms[1371] = dict(water=set(groups[29]), collected=False)
    p.loot[1371] = dict(cell=1371, name="Chest")
    observe(p, s)
    return s, p, potion


class RejectedPoolBankTests(unittest.TestCase):
    def select(self, s, p, potion):
        return stage_known_pool(p, s, Demand("pool", "potion of invisibility", 1371),
                                potion, distance, neighbors)

    def test_fully_seen_rejected_arrival_cannot_attract_neighbor(self):
        s, p, potion = approach()
        before = copy.deepcopy(s)
        self.assertTrue(staging_bank(p, s, 1267))
        self.assertFalse(safe_test_bank(p, s, 1267, distance, neighbors,
                                       allow_dry=True, pool_bank=True))
        self.assertIsNone(self.select(s, p, potion),
                          "Do not return to a fully seen bank that cannot activate preparation")
        self.assertEqual(0, p.puzzle_revisit_steps["pool"])
        self.assertEqual(before, s)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        self.assertIn(1371, pending(p))
        self.assertFalse(p.loot_collection_receipts)

    def test_arrival_still_declines_without_weakening_drink_safety(self):
        s, p, potion = approach(1267)
        self.assertIsNone(self.select(s, p, potion))
        self.assertIsNone(p.room_journey)
        self.assertIn(1371, pending(p))

    def test_incomplete_visibility_can_still_request_a_recheck(self):
        s, p, potion = approach()
        # Isolated alternative, not a continuation after a changed decision.
        p.tiles[1229]["visible"] = False
        d = self.select(s, p, potion)
        self.assertEqual({"type": "cell", "cell": 1267}, d.action)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)
        self.assertIn(1371, pending(p))


if __name__ == "__main__":
    unittest.main()
