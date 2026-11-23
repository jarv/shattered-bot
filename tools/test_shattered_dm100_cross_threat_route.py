"""Reduced run 000174 decision 3754, selection line 10794.

This is public route geometry, not recovered runtime memory or a game replay.
The plan-shaped probe is isolated; no changed-decision future is supplied.
"""
import copy
import unittest

from tools.challenge_combat import exposure
from tools.dm100_escape import choose
from tools.policy_geometry import distance, line_clear
from tools.test_challenge_rules import verified


def corridor():
    terrain = {392: 5, 424: 14, 425: 5, 456: 14, 486: 14, 487: 14,
               517: 14, 549: 14, 581: 14, 613: 14, 646: 14,
               647: 14, 648: 14, 649: 14}
    s = dict(scene="GameScene", status="ready", modal=False, depth=7, branch=0,
             hero=dict(cell=646, hp=65, max_hp=65, strength=12, level=10,
                       buffs=[dict(name="starving"), dict(name="healing")], talents=[]),
             inventory=[], danger_cells=[], ui=dict(texts=[], buttons=[]),
             objects=[dict(name="skeleton", cell=424),
                      dict(name="prison guard", cell=647),
                      dict(name="prison guard", cell=648),
                      dict(name="DM-100", cell=649)],
             map=dict(width=32, height=50, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=True)
                 for c, t in terrain.items()]))
    p = verified()
    p.update(s)
    return s, p


class CrossThreatRouteTests(unittest.TestCase):
    def test_existing_guard_contact_does_not_fund_new_skeleton_contact(self):
        s, p = corridor()
        before = copy.deepcopy(s)
        others = s["objects"][:-1]
        # The old aggregate gate treats these different attackers as equal.
        self.assertEqual(1, exposure(p, s, others, 646, distance, line_clear)["exposure"])
        self.assertEqual(1, exposure(p, s, others, 456, distance, line_clear)["exposure"])
        self.assertIsNone(choose(p, s, s["objects"]),
                          "Do not start a door flight through a different observed attacker")
        self.assertIsNone(p.ranged_plan)
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)

    def test_committed_route_rechecks_each_observed_attacker(self):
        s, p = corridor()
        p.ranged_plan = dict(name="dm-100", mode="door-flight", stage="door",
                            door=425, goal=425, approach=456, steps=1, waits=0,
                            depth=7, branch=0, last_seen=649, hp=65, armed=False)
        self.assertIsNone(choose(p, s, s["objects"]))
        self.assertIsNone(p.ranged_plan)
        self.assertIn(425, p.dm100_failed_doors)

    def test_retreat_from_current_guard_remains_available_without_new_contact(self):
        s, p = corridor()
        # Counterfactual sleeping actor, not a later recorded observation.
        s["objects"][0]["sleeping"] = True
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=613), d.action)
        self.assertEqual(425, p.ranged_plan["door"])
        self.assertEqual("retreat", d.intent.value)

    def test_route_hazards_still_veto_the_positive_control(self):
        s, p = corridor()
        s["objects"][0]["sleeping"] = True
        p.tiles[581]["trap"] = "explosive trap"
        self.assertIsNone(choose(p, s, s["objects"]))
        self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
