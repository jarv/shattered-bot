"""Run-wide ownership, receipt reconciliation and transactional contracts."""
import copy
import json
import unittest

from tools.objective_episodes import Scope
from tools.physical_obligations import PhysicalLedger, Resource, ResourceKind
from tools.stash_workflow import StashWorkflow
from tools.policy_runtime import Transaction
from tools.objective_planning import resolve, Result, Status
from tools.potion_stash import observe_accepted, can_protect_potions
from tools.policy_geometry import distance, neighbors, line_clear
from tools.policy_decision import TacticalBlocked
from tools.tactical_recovery import recover
from tools.test_stash_workflow import drop_fixture, pickup_fixture


class PhysicalLedgerContracts(unittest.TestCase):
    def test_plan_claims_are_not_physical_debts(self):
        ledger=PhysicalLedger()
        plan=StashWorkflow(depth=1,bank=24,cell=21)
        self.assertTrue(ledger.register(plan,["candidate","other"]))
        self.assertFalse(plan.unresolved)
        self.assertFalse(ledger.deferred_records())
        self.assertEqual("planned",ledger.records()[0]["status"])
        ledger.defer(plan,"planning declined")
        self.assertFalse(ledger.claims)
        self.assertFalse(ledger.deferred_records())
        self.assertEqual("cancelled",ledger.records()[0]["status"])

    def test_claim_acquisition_is_atomic_and_owner_scoped(self):
        ledger=PhysicalLedger()
        first=StashWorkflow(depth=1,bank=24,cell=21)
        second=StashWorkflow(depth=1,bank=24,cell=22)
        self.assertTrue(ledger.register(first,["candidate"]))
        before=copy.deepcopy(ledger.claims)
        self.assertFalse(ledger.register(second,["free-item","candidate"]))
        self.assertEqual(before,ledger.claims)
        self.assertFalse(second.owner)
        self.assertEqual(1,len(ledger.entries))
        self.assertTrue(ledger.register(first,["candidate"]))
        self.assertTrue(ledger.inventory_available(Scope(1),["candidate"],first.owner))
        self.assertFalse(ledger.inventory_available(Scope(1),["candidate"]))
        self.assertTrue(ledger.register(StashWorkflow(depth=1,branch=1,bank=24,cell=21),
                                        ["candidate"]))

    def test_deactivation_releases_inventory_but_not_owned_ground(self):
        p,s,_,_=pickup_fixture()
        plan=p.potion_stash
        ledger=p.physical_ledger
        ledger.defer(plan,"blocked return")
        self.assertTrue(ledger.inventory_available(plan.scope,["candidate","other"]))
        self.assertFalse(ledger.site_available(plan.scope,plan.cell))
        self.assertFalse(ledger.register(StashWorkflow(depth=plan.depth,bank=24,cell=21)))
        self.assertEqual({"potion of strength":2},
                         ledger.deferred_records()[0]["obligation"]["outstanding"])
        with self.assertRaises(ValueError): ledger.finish(plan)
        self.assertEqual("outstanding",ledger.records()[0]["status"])

    def test_orphan_pickup_settles_debt_without_recreating_workflow(self):
        p,s,d,after=pickup_fixture()
        plan=p.potion_stash
        recover(p,s,[],TacticalBlocked("obligation:potion-stash","blocked return"),
                distance,neighbors,line_clear)
        self.assertIsNone(p.potion_stash)
        self.assertTrue(p.deferred_obligations)
        self.assertFalse(p.legacy_deferred_obligations)
        receipt=observe_accepted(p,s,d,after)
        self.assertEqual("pickup",receipt["kind"])
        self.assertFalse(p.deferred_obligations)
        self.assertIsNone(p.potion_stash)
        self.assertTrue(p.physical_ledger.site_available(plan.scope,plan.cell))
        self.assertEqual("settled",p.physical_ledger.records()[0]["status"])
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":2},plan.retrieved)

    def test_new_attempt_does_not_own_or_erase_old_debt(self):
        p,s,d,after=pickup_fixture()
        old=p.potion_stash
        p.physical_ledger.defer(old,"old blocked return")
        p.potion_stash=None
        new=StashWorkflow(depth=old.depth,bank=24,cell=22,candidate="ivory potion")
        self.assertTrue(p.physical_ledger.register(new,["new-supply"]))
        p.potion_stash=new
        self.assertNotEqual(old.owner,new.owner)
        self.assertTrue(p.deferred_obligations)
        observe_accepted(p,s,d,after)  # Physical old-stash receipt, not new attempt progress.
        self.assertIs(new,p.potion_stash)
        self.assertFalse(old.outstanding)
        self.assertFalse(new.dropped)
        self.assertFalse(new.retrieved)
        self.assertEqual(new.owner,p.physical_ledger.claims[
            Resource(new.scope,ResourceKind.INVENTORY,"new-supply")])

    def test_report_views_cannot_modify_canonical_quantities(self):
        p,_,_,_=pickup_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"blocked")
        view=p.deferred_obligations
        view[0]["obligation"]["outstanding"].clear()
        view[0]["obligation"]["confirmed_drops"].clear()
        view.clear()
        self.assertEqual({"potion of strength":2},plan.outstanding)
        self.assertTrue(p.deferred_obligations)
        json.dumps(p.physical_ledger.records())
        json.dumps(p.physical_ledger.claim_records())

    def test_uncertain_drop_is_distinct_from_confirmed_owned_quantities(self):
        p,_,_,_,_=drop_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"execution unresolved",plan.pending)
        self.assertFalse(plan.dropped)
        self.assertFalse(plan.outstanding)
        self.assertTrue(plan.unresolved)
        self.assertEqual("unverified",p.physical_ledger.records()[0]["status"])
        self.assertFalse(p.physical_ledger.site_available(plan.scope,plan.cell))
        self.assertEqual(2,p.deferred_obligations[0]["obligation"]["unverified_drop"]["quantity"])

    def test_foreign_owner_and_duplicate_tokens_cannot_resolve_debt(self):
        p,_,_,_=pickup_fixture()
        plan=p.potion_stash
        forged=copy.deepcopy(plan)
        ledger=p.physical_ledger
        self.assertFalse(ledger.pickup(forged,"potion of strength",2,20))
        self.assertFalse(ledger.register(forged))
        with self.assertRaises(ValueError): ledger.finish(forged)
        self.assertTrue(ledger.pickup(plan,"potion of strength",1,20))
        self.assertFalse(ledger.pickup(plan,"potion of strength",1,20))
        self.assertFalse(ledger.pickup(plan,"potion of strength",2,21))
        self.assertEqual({"potion of strength":1},plan.outstanding)

    def test_transaction_preserves_single_object_identity_and_claims(self):
        p,s,d,after,_=drop_fixture()
        plan=p.potion_stash
        pending=plan.pending
        tx=Transaction(p)
        observe_accepted(p,s,d,after)
        p.physical_ledger.defer(p.potion_stash,"interrupted")
        tx.rollback()
        restored=p.potion_stash
        self.assertIs(restored,p.physical_ledger.entries[restored.owner])
        self.assertFalse(restored.dropped)
        self.assertTrue(restored.active)
        self.assertTrue(p.physical_ledger.claims)
        self.assertEqual(pending,restored.pending)
        self.assertFalse(p.physical_ledger.receipts)

    def test_declined_provider_does_not_leak_claims_or_obligations(self):
        p,_,_,_,_=drop_fixture()
        p.physical_ledger.finish(p.potion_stash)
        p.potion_stash=None
        baseline=copy.deepcopy(p.physical_ledger)
        def declined():
            plan=StashWorkflow(depth=1,bank=24,cell=22)
            self.assertTrue(p.physical_ledger.register(plan,["new-item"]))
            return Result(Status.BLOCKED,"domain route declined")
        self.assertIsNone(resolve(p,"prepare",[("claim",declined)]))
        self.assertEqual(baseline,p.physical_ledger)

    def test_reserved_candidate_fails_read_only_preflight(self):
        p,s,_,_,candidate=drop_fixture()
        old=p.potion_stash
        p.potion_stash=None  # Another consumer may not use the active owner's item.
        before=copy.deepcopy(p.physical_ledger)
        self.assertFalse(can_protect_potions(
            p,s,candidate,distance,neighbors,lambda *a,**k:True))
        self.assertEqual(before,p.physical_ledger)
        self.assertTrue(old.active)

    def test_orphan_pickup_after_floor_reset_uses_original_scope(self):
        p,s,d,after=pickup_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"left floor")
        new_floor=copy.deepcopy(s)
        new_floor["depth"]+=1
        p.update(new_floor)
        self.assertIsNone(p.potion_stash)
        self.assertIs(plan,p.physical_ledger.entries[plan.owner])
        self.assertTrue(p.deferred_obligations)
        self.assertFalse(p.physical_ledger.site_available(plan.scope,plan.cell))
        # Public return/pickup observation on the original scope.
        self.assertIsNotNone(observe_accepted(p,s,d,after))
        self.assertFalse(p.deferred_obligations)
        self.assertFalse(p.potion_stash)

    def test_orphan_partial_and_unrelated_pickups_do_not_overcredit(self):
        p,s,d,after=pickup_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"blocked")
        p.potion_stash=None
        wrong=copy.deepcopy(after)
        wrong["hero"]["cell"]=22
        self.assertIsNone(observe_accepted(p,s,d,wrong))
        self.assertEqual({"potion of strength":2},plan.outstanding)
        after["inventory"][-1]=dict(after["inventory"][-1],quantity=1)
        self.assertIsNotNone(observe_accepted(p,s,d,after))
        self.assertIsNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":1},plan.outstanding)
        self.assertTrue(p.deferred_obligations)
        self.assertFalse(p.physical_ledger.site_available(plan.scope,plan.cell))

    def test_hidden_or_absent_heap_does_not_free_stash_location(self):
        from tools.potion_stash import stash_cells
        p,s,_,_=pickup_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"heap no longer visible")
        p.potion_stash=None
        s["objects"]=[]
        p.loot.clear()
        self.assertFalse(stash_cells(p,s,distance,neighbors,lambda *a,**k:True))
        self.assertTrue(p.deferred_obligations)

    def test_deferred_debt_still_blocks_abandonment_and_clear_credit(self):
        from tools.floor_abandonment import FloorAbandonment
        from tools.loot_completion import pending_collections
        p,s,d,after=pickup_fixture()
        plan=p.potion_stash
        p.physical_ledger.defer(plan,"blocked")
        p.potion_stash=None
        p.stop_on_incomplete_loot=False
        gate=FloorAbandonment(p)
        self.assertEqual("owned item debt or unverified transfer remains",gate.hard_gate(s))
        self.assertTrue(pending_collections(p))
        self.assertFalse(p.descent_counts_as_clear())
        observe_accepted(p,s,d,after)
        self.assertFalse(p.physical_ledger.has_unresolved())
        self.assertNotEqual("owned item debt or unverified transfer remains",gate.hard_gate(after))
        self.assertFalse(p.loot_collection_receipts)


if __name__=="__main__":
    unittest.main()
