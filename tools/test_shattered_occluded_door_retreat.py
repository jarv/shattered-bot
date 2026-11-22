"""Reduced public corridor from decisions 1464-1465 of recording 000108."""
import copy
import unittest

from tools import multi_enemy_tactics as multi
from tools import pursuit_budget
from tools.escape_commitment import reverses
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.test_unit_strategies import enemy


def corridor():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=914, hp=38, max_hp=40,
                     buffs=[{"name": "hungry"}])
    # x=26..36, y=18..24. Omitted cells remain unknown.
    rows = (
        "5 1 1 1 0 0 4 ? ? ? ?",
        "4 0 0 1 0 0 4 ? ? ? ?",
        "4 0 0 1 0 0 4 4 12 12 4",
        "4 0 0 1 29 29 6 29 29 29 1",
        "4 4 4 4 4 4 4 33 33 1 1",
        "4 ? ? ? ? ? ? 33 33 1 1",
        "4 4 4 4 4 4 4 ? 1 1 1",
    )
    s["map"] = dict(width=42, height=38, cells=[
        dict(cell=y*42+x, terrain=int(t), observed=True, visible=True)
        for y, row in enumerate(rows, 18)
        for x, t in enumerate(row.split(), 26) if t != "?"])
    s["objects"] = [enemy("slime", 916, sleeping=True),
                     enemy("gnoll scout", 917),
                     enemy("swarm of flies", 959),
                     enemy("sewer crab", 1042)]
    s["inventory"][0].update(name="staff of magic missile +3", status="2/7",
                              identified=True, curse_known=True, known_cursed=False)
    p = verified()
    p.update(s)
    return p, s


def occluded():
    p, before = corridor()
    d = multi.choose(p, before, before["objects"])
    assert d.action == {"type": "cell", "cell": 913}
    assert p.multi_door_plan["door"] == 782
    d.controller = "multi-threat-retreat"
    after = copy.deepcopy(before)
    after["hero"]["cell"] = 913
    after["objects"] = []
    for t in after["map"]["cells"]:
        if t["cell"] == 914:
            t["terrain"] = 5  # The observed door shuts behind the retreat.
        if t["cell"] % 42 >= 33:
            t["visible"] = False
    multi.observe_accepted(p, before, d, after)
    pursuit_budget.observe_accepted(p, before, d, after)
    p.update(after)
    return p, after


class OccludedDoorRetreatTests(unittest.TestCase):
    def test_occlusion_continues_accepted_observed_route_not_frontier_reentry(self):
        p, s = occluded()
        self.assertTrue(reverses(p, s, 914))
        d = p.choose(s)
        self.assertEqual("multi-threat-retreat", d.controller)
        self.assertEqual({"type": "cell", "cell": 912}, d.action)
        self.assertEqual(Intent.RETREAT, d.intent)
        self.assertEqual(1, p.multi_door_plan["steps"])
        self.assertIsNone(p.doorway_hold)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.cleared_floors)

    def test_only_accepted_recent_safe_continuations_are_admitted(self):
        for case in ("unaccepted", "forgotten", "hazard", "plant", "loot",
                     "unknown", "invisible-step", "low-hp", "budget", "branch",
                     "effects", "danger", "root", "contact", "at-door"):
            with self.subTest(case=case):
                p, s = occluded()
                if case == "unaccepted": p.multi_door_plan["steps"] = 0
                elif case == "forgotten": p.recent_threats.clear()
                elif case == "hazard": p.tiles[912]["trap"] = "burning trap"
                elif case == "plant": p.tiles[912]["plant"] = "firebloom"
                elif case == "loot": p.loot[912] = dict(cell=912, name="scroll of upgrade")
                elif case == "unknown": p.tiles.pop(912)
                elif case == "invisible-step": p.tiles[912]["visible"] = False
                elif case == "low-hp": s["hero"]["hp"] = 10
                elif case == "budget": p.multi_door_plan["steps"] = 12
                elif case == "branch": p.multi_door_plan["branch"] = 1
                elif case == "effects": p.tiles[912]["effects"] = ["fire is raging"]
                elif case == "danger": s["danger_cells"] = [912]
                elif case == "root": s["hero"]["buffs"] = [dict(name="rooted")]
                elif case == "contact":
                    p.recent_threats[911] = enemy("sewer crab", 911)
                elif case == "at-door": s["hero"]["cell"] = 782
                self.assertIsNone(multi.choose(p, s, []))

    def test_proposal_does_not_spend_accepted_budget_and_can_roll_back(self):
        p, s = occluded()
        tx = Transaction(p)
        d = multi.choose(p, s, [])
        self.assertIsNotNone(d)
        self.assertEqual(1, p.multi_door_plan["steps"])
        tx.rollback()
        self.assertIsNone(p.multi_retreat_pending)
        self.assertEqual(1, p.multi_door_plan["steps"])


if __name__ == "__main__":
    unittest.main()
