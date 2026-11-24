"""Reduced public geometry from recording 000210, decision 1290.

Search counts reconstruct the four accepted scan receipts, not runtime memory.
This is an isolated preparation probe; no discovery or later input is invented.
"""
import copy
import unittest

from tools import trap_field_tactics as traps
from tools.policy_decision import Decision, Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=1552, hp=40, max_hp=40,
                     buffs=[{"name": "hungry"}])
    # Rows 25-31, columns 10-16 of the observed 53-column floor.
    rows = [
        [1, 19, 18, 1, 9, 19, 4],
        [1, 1, 9, 19, 1, 1, 4],
        [1, 1, 1, 18, 1, 18, 4],
        [19, 18, 9, 9, 19, 18, 5],
        [9, 9, 18, 1, 18, 19, 4],
        [18, 19, 9, 1, 1, 18, 4],
        [19, 18, 9, 19, 18, 1, 4],
    ]
    s["map"] = dict(width=53, height=39, cells=[
        dict(cell=(25+y)*53+10+x, terrain=t, visible=True,
             observed=True, effects=[],
             **({"trap": "burning trap"} if t in {18, 19} else {}))
        for y, row in enumerate(rows) for x, t in enumerate(row)])
    s["objects"] = [dict(cell=1390, name="scroll of SOWILO",
                         top_item=dict(name="scroll of SOWILO"))]
    s["danger_cells"] = []
    p = verified()
    p.update(s)
    p.trap_scan_cells.update({1501: 2, 1500: 2})
    move = Decision(dict(type="cell", cell=1498),
                    "loot: finish shortest observed-room collection tour",
                    Intent.LOOT)
    return s, p, move


class InactiveTrapScanTests(unittest.TestCase):
    def test_inactive_plate_does_not_exclude_remaining_preparation(self):
        s, p, move = fixture()
        before = copy.deepcopy(s)
        scan = traps.before_move(p, s, move, [])
        self.assertIsNotNone(scan, "A clear triggered plate is not an active trap")
        self.assertEqual(dict(type="search"), scan.action)
        self.assertEqual(4, sum(p.trap_scan_cells.values()))
        self.assertEqual(before, s)
        self.assertNotIn("trap", p.tiles[1445])  # Still unknown before searching.
        self.assertIn(1390, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_same_search_limits_and_honest_receipts(self):
        s, p, move = fixture()
        for count in (1, 2):
            scan = traps.before_move(p, s, move, [])
            self.assertIsNotNone(scan)
            receipt = traps.observe_accepted(p, s, scan, copy.deepcopy(s))
            self.assertEqual(count, receipt["accepted_searches"])
        self.assertEqual(6, sum(p.trap_scan_cells.values()))
        self.assertIsNone(traps.before_move(p, s, move, []))
        self.assertIn(1390, p.loot)
        self.assertNotIn("trap", p.tiles[1445])

    def test_rejected_preparation_rolls_back(self):
        s, p, move = fixture()
        tx = Transaction(p, p.planner)
        self.assertIsNotNone(traps.before_move(p, s, move, []))
        tx.rollback()
        self.assertEqual(4, sum(p.trap_scan_cells.values()))
        self.assertIsNone(p.trap_scan_pending)

    def test_active_or_ambiguous_trap_and_hazards_remain_excluded(self):
        for mode in ("active", "active-unnamed", "ambiguous", "unobserved", "fire", "plant", "room",
                     "danger", "enemy", "retreat", "total-budget"):
            with self.subTest(mode=mode):
                s, p, move = fixture()
                tile = p.tiles[1552]
                enemies = []
                if mode == "active": tile["terrain"] = 18
                elif mode == "active-unnamed":
                    tile["terrain"]=18
                    tile.pop("trap",None)
                elif mode == "ambiguous": tile["terrain"] = 1
                elif mode == "unobserved": tile.update(visible=False, observed=False)
                elif mode == "fire": tile["effects"] = ["A fire is raging here."]
                elif mode == "plant": tile["plant"] = "firebloom"
                elif mode == "room": p.room_blocked.add(1552)
                elif mode == "danger": s["danger_cells"] = [1552]
                elif mode == "enemy": enemies = [dict(name="slime", cell=1498)]
                elif mode == "retreat": move.intent = Intent.RETREAT
                else: p.trap_scan_cells[1501] = 4
                self.assertIsNone(traps.before_move(p, s, move, enemies))


if __name__ == "__main__":
    unittest.main()
