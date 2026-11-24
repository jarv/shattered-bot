"""Conservative composition checks; no enemy timing or hazard permission."""
import copy
import unittest

from tools.escape_commitment import preflight, observe
from tools.policy_decision import Decision, Intent
from tools.test_shattered_doorway_approach_bank import fixture


class CommitmentPreflightContracts(unittest.TestCase):
    def test_proposed_reverse_edge_is_rejected_without_live_commitment(self):
        p,s=fixture()
        before=copy.deepcopy(p.escape_commitment)
        result=preflight(p,s,[946,979],946)
        self.assertFalse(result.allowed)
        self.assertEqual((979,946),result.edge)
        self.assertEqual(before,p.escape_commitment)

    def test_existing_constraint_on_an_earlier_approach_edge_is_checked(self):
        p,s=fixture()
        p.escape_commitment=dict(edges=[(979,946)],hp=30,charges=0,age=0)
        before=copy.deepcopy(p.escape_commitment)
        result=preflight(p,s,[946,979],978)
        self.assertFalse(result.allowed)
        self.assertEqual((946,979),result.edge)
        self.assertEqual(before,p.escape_commitment)

    def test_safe_projection_matches_accepted_edge_reducer(self):
        p,s=fixture()
        result=preflight(p,s,[946,979],978)
        self.assertTrue(result.allowed)
        self.assertIsNone(p.escape_commitment)
        for cell in (979,978):
            after=copy.deepcopy(s)
            after["hero"]["cell"]=cell
            observe(p,s,Decision(dict(type="cell",cell=cell),"retreat",Intent.RETREAT),after,True)
            s=after
        self.assertEqual(result.projected_edges,tuple(p.escape_commitment["edges"]))

    def test_origin_mismatch_or_no_move_does_not_certify_itinerary(self):
        p,s=fixture()
        self.assertFalse(preflight(p,s,[],978).allowed)
        self.assertFalse(preflight(p,s,[979],978).allowed)
        self.assertFalse(preflight(p,s,[946,946,979],978).allowed)

    def test_age_expiry_is_not_assumed_during_planning(self):
        p,s=fixture()
        p.escape_commitment=dict(edges=[(979,946)],hp=30,charges=0,age=11)
        self.assertFalse(preflight(p,s,[946,979],978).allowed)
        self.assertEqual(11,p.escape_commitment["age"])

    def test_fresh_doorway_plan_reports_witness_and_decline(self):
        p,s=fixture()
        d=p.door_ambush(s,s["objects"],s["objects"],kind="doorway")
        self.assertEqual(979,d.action["cell"])
        self.assertTrue(p.ambush_plan["preflight"]["allowed"])
        declines=p.planner.report["commitment_declines"]
        self.assertTrue(any(r["hide"]==946 and not r["allowed"] for r in declines))
        self.assertIsNone(p.escape_commitment)
        self.assertFalse(p.completed_room_rewards)


if __name__=="__main__":
    unittest.main()
