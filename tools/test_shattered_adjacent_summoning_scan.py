"""Run 58 decision 747: inspect a revealed summoning trap's immediate approach.

Reduced public geometry, not reconstructed runtime memory or a game replay.
Searching is preparation only: no hidden trap or successful retrieval is assumed.
"""
import copy
import unittest

from tools import trap_field_tactics as traps
from tools.policy_decision import Decision, Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def approach():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=980, hp=30, max_hp=30, buffs=[{"name": "hungry"}])
    terrain = {945: 29, 979: 4, 980: 6, 981: 4, 1012: 4, 1013: 18,
               1014: 1, 1015: 1, 1016: 1, 1046: 4, 1047: 1, 1048: 1,
               1049: 1, 1050: 1, 1051: 1}
    s["map"] = {"width": 34, "height": 38, "cells": [
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()]}
    next(t for t in s["map"]["cells"] if t["cell"] == 1013)["trap"] = "summoning trap"
    s["objects"] = [{"cell": 1049, "name": "Skeletal remains"}]
    p = verified()
    p.update(s)
    move = Decision({"type": "cell", "cell": 1014}, "loot: collect/open", Intent.LOOT)
    return s, p, move


class AdjacentSummoningScanTests(unittest.TestCase):
    def test_full_selector_defers_unprepared_summoning_field(self):
        s, p, _ = approach()
        scan = p.choose(s)
        self.assertEqual({"type": "cell", "cell": 945}, scan.action)
        self.assertNotIn(1014,p.paths(s))
        self.assertIn(1049,p.loot)

    def test_single_revealed_summoning_trap_merits_search_before_adjacent_loot_step(self):
        s, p, move = approach()
        self.assertIsNone(p.tiles[1014].get("trap"))  # No pre-action hidden identity.
        scan = traps.before_move(p, s, move, [])
        self.assertIsNotNone(scan, "Do not require three traps beside a revealed summoning trap")
        self.assertEqual({"type": "search"}, scan.action)
        self.assertFalse(p.walkable(1013))
        self.assertFalse(p.trap_scan_cells)  # Proposing is not accepting.

    def test_receipts_and_existing_search_budgets_still_apply(self):
        s, p, move = approach()
        for n in (1, 2):
            scan = traps.before_move(p, s, move, [])
            self.assertIsNotNone(scan)
            receipt = traps.observe_accepted(p, s, scan, copy.deepcopy(s))
            self.assertEqual(n, receipt["accepted_searches"])
        self.assertIsNone(traps.before_move(p, s, move, []))
        self.assertIn(1049, p.loot)  # No search receipt grants loot completion.

    def test_rejected_proposal_does_not_spend_search_budget(self):
        s, p, move = approach()
        tx = Transaction(p, p.planner)
        self.assertIsNotNone(traps.before_move(p, s, move, []))
        tx.rollback()
        self.assertFalse(p.trap_scan_cells)
        self.assertIsNone(p.trap_scan_pending)

    def test_not_a_general_sparse_trap_search_rule(self):
        for change in ("ordinary", "inactive", "unseen", "distant-step"):
            s, p, move = approach()
            tile = p.tiles[1013]
            if change == "ordinary":
                tile["trap"] = "burning trap"
            elif change == "inactive":
                tile["terrain"] = 19
            elif change == "unseen":
                tile["visible"] = False
            else:
                move.action["cell"] = 945
            self.assertIsNone(traps.before_move(p, s, move, []), change)

    def test_does_not_preempt_emergencies_or_search_from_hazard(self):
        for change in ("retreat", "enemy", "recent", "starving", "hp", "gas", "warning", "mapped"):
            s, p, move = approach()
            enemies = []
            if change == "retreat":
                move.intent = Intent.RETREAT
            elif change == "enemy":
                enemies = [{"name": "marsupial rat", "cell": 1015}]
            elif change == "recent":
                p.recent_threats[1015] = {"name": "marsupial rat", "cell": 1015}
            elif change == "starving":
                s["hero"]["buffs"] = [{"name": "starving"}]
            elif change == "hp":
                s["hero"]["hp"] = 1
            elif change == "gas":
                p.tiles[980]["effects"] = ["A greenish cloud of toxic gas is swirling here."]
            elif change == "warning":
                s["danger_cells"] = [980]
            else:
                p.mapped_floors.add((2, 0))
            self.assertIsNone(traps.before_move(p, s, move, enemies), change)


if __name__ == "__main__":
    unittest.main()
