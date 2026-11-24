"""Accepted ownership and interruption contracts, not counterfactual replays."""
import copy
import itertools
import json
import unittest

from tools.workflow_accounting import AcceptedBudget, OwnedAction, RecoveryEpisode, RecoveryPhase
from tools.policy_decision import Decision, Intent, PlannerStuck
from tools.test_shattered_floor_abandonment import fixture


def started():
    s,p,recovery=fixture()
    decision=recovery.start(s,PlannerStuck("optional exhausted",kind="optional-work-exhausted"),{},0)
    return s,p,recovery,decision


class WorkflowAccountingContracts(unittest.TestCase):
    def test_short_sequences_match_independent_budget_model(self):
        for events in itertools.product(("progress","stall","interrupt"),repeat=5):
            budget=AcceptedBudget(best_distance=20)
            accepted=owned=interruptions=stalled=0
            distance=20
            for event in events:
                accepted+=1
                if event=="interrupt":
                    interruptions+=1
                    budget.accept(False)
                elif event=="stall":
                    owned+=1;stalled+=1
                    budget.accept(True)
                else:
                    owned+=1;stalled=0;distance-=1
                    budget.accept(True,distance)
                self.assertEqual((accepted,owned,interruptions,stalled,distance),
                                 (budget.accepted,budget.owned,budget.interruptions,
                                  budget.stalled,budget.best_distance),events)

    def test_first_owned_move_credits_actual_remaining_distance(self):
        s,_,recovery,d=started()
        episode=recovery.active
        initial=episode.budget.best_distance
        episode.budget.stalled=3
        after=copy.deepcopy(s)
        after["hero"]["cell"]=d.action["cell"]
        after["observation_id"]+=1
        recovery.observe(s,d,after)
        self.assertEqual(initial-1,episode.budget.best_distance)
        self.assertEqual((1,1,0,0),(episode.budget.accepted,episode.budget.owned,
                         episode.budget.interruptions,episode.budget.stalled))
        self.assertFalse(episode["collection_credited"])

    def test_replaced_or_stale_decisions_cannot_claim_ownership(self):
        for mode in ("action","intent","controller","origin","floor","branch","no-witness"):
            with self.subTest(mode=mode):
                s,_,recovery,d=started()
                episode=recovery.active
                if mode=="action": d.action=dict(type="wait")
                elif mode=="intent": d.intent=Intent.RETREAT
                elif mode=="controller": d.controller="survival"
                elif mode=="origin": s["hero"]["cell"]+=1
                elif mode=="floor": s["depth"]+=1
                elif mode=="branch": s["branch"]=1
                else: del d.recovery_receipt
                after=copy.deepcopy(s)
                after["observation_id"]+=1
                after["hero"]["cell"]=d.action.get("cell",s["hero"]["cell"])
                recovery.observe(s,d,after)
                self.assertEqual((1,0,1,0),(episode.budget.accepted,episode.budget.owned,
                                 episode.budget.interruptions,episode.budget.stalled))
                self.assertEqual(RecoveryPhase.PAUSED,episode.phase)
                self.assertFalse(episode["collection_credited"])

    def test_duplicate_receipt_never_spends_or_progresses_twice(self):
        s,_,recovery,d=started()
        after=copy.deepcopy(s)
        after["hero"]["cell"]=d.action["cell"]
        after["observation_id"]+=1
        recovery.observe(s,d,after)
        baseline=copy.deepcopy(recovery.active.budget)
        recovery.observe(s,d,after)
        self.assertEqual(baseline,recovery.active.budget)

    def test_pause_resume_keeps_both_budgets_and_owner(self):
        s,_,recovery,d=started()
        episode=recovery.active
        episode.budget.stalled=2
        combat=copy.deepcopy(s)
        combat["objects"]=[dict(name="marsupial rat",cell=61)]
        self.assertIsNone(recovery.next(combat))
        self.assertEqual(RecoveryPhase.PAUSED,episode.phase)
        after=copy.deepcopy(combat)
        after["observation_id"]+=1
        recovery.observe(combat,Decision(dict(type="wait"),"survival"),after)
        self.assertEqual((1,2),(episode.budget.accepted,episode.budget.stalled))
        # Fresh planning resumes the same episode, not a new allowance.
        after["objects"]=[]
        resumed=recovery.next(after)
        self.assertEqual(episode["id"],resumed.recovery_receipt.owner)
        self.assertEqual(RecoveryPhase.ACTIVE,episode.phase)
        self.assertEqual((1,2),(episode.budget.accepted,episode.budget.stalled))

    def test_report_mutation_cannot_reset_runtime_budgets(self):
        s,_,recovery,d=started()
        recovery.active.budget.accepted=64
        recovery.incidents[0]["accepted_actions"]=0
        with self.assertRaises(PlannerStuck): recovery.next(s)
        self.assertEqual(64,recovery.incidents[0]["accepted_actions"])
        self.assertEqual("exhausted",recovery.incidents[0]["status"])
        json.dumps(recovery.incidents)

    def test_replanning_does_not_rewrite_accepted_action_witness(self):
        s,_,recovery,d=started()
        expected=len(d.recovery_receipt.route)-2
        recovery.active["last_distance"]=0  # Stale later diagnostic, not evidence.
        after=copy.deepcopy(s)
        after["hero"]["cell"]=d.action["cell"]
        after["observation_id"]+=1
        recovery.observe(s,d,after)
        self.assertEqual(expected,recovery.active.budget.best_distance)

    def test_terminal_descent_needs_exact_owned_transition(self):
        for owned in (False,True):
            s,_,recovery,_=started()
            target=recovery.active["target"]
            d=Decision(dict(type="cell",cell=target),"descend",Intent.DESCEND)
            d.floor_abandonment=recovery.active["id"]  # Legacy tag alone is not authority.
            if owned:
                d.recovery_receipt=OwnedAction.capture(recovery.active["id"],s,d,
                                                      [s["hero"]["cell"],target])
            after=copy.deepcopy(s)
            after["depth"]+=1
            after["observation_id"]+=1
            recovery.observe(s,d,after)
            self.assertEqual(owned,recovery.active is None)
            self.assertEqual("descended" if owned else "paused",recovery.incidents[0]["status"])
            self.assertFalse(recovery.incidents[0]["collection_credited"])

    def test_imported_counters_do_not_invent_past_ownership(self):
        episode=RecoveryEpisode.from_record(dict(status="active",accepted_actions=4))
        self.assertEqual((4,0,0,4),(episode.budget.accepted,episode.budget.owned,
                         episode.budget.interruptions,episode.budget.unattributed))
        episode.budget.accept(False)
        self.assertEqual(5,episode.budget.accepted)
        self.assertEqual(4,episode.budget.unattributed)

    def test_run_interruption_closes_episode_without_completion_credit(self):
        _,_,recovery,_=started()
        recovery.interrupt()
        self.assertIsNone(recovery.active)
        self.assertEqual("interrupted",recovery.incidents[0]["status"])
        self.assertFalse(recovery.incidents[0]["collection_credited"])


if __name__=="__main__":
    unittest.main()
