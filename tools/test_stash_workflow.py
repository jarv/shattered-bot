"""Accepted-transfer contracts and synthetic workflows, not recording replays."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.policy_decision import Decision, TacticalBlocked
from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.potion_stash import (
    advance_stash, can_protect_potions, protect_potions, observe_accepted,
)
from tools.stash_workflow import StashWorkflow, StashPhase


def drop_fixture():
    from tools import test_potion_stash as fixtures
    s,p,candidate,other,safe=fixtures.PotionStashTests().setup_stash()
    protect_potions(p,s,candidate,distance,neighbors,safe)
    s["hero"]["cell"]=21
    action=advance_stash(p,s,[],distance)
    after=copy.deepcopy(s)
    after["observation_id"]=s["observation_id"]+1
    after["inventory"].remove(other)
    after["objects"]=[dict(cell=21,name=other["name"],top_item=other)]
    return p,s,action,after,candidate


def pickup_fixture():
    p,s,d,after,_=drop_fixture()
    observe_accepted(p,s,d,after)
    p.potion_stash.retrieve()
    before=copy.deepcopy(after)
    before["hero"]["cell"]=24
    after=copy.deepcopy(before)
    after["observation_id"]+=1
    after["hero"]["cell"]=21
    after["inventory"].append(after["objects"][0]["top_item"])
    after["objects"]=[]
    return p,before,Decision(dict(type="cell",cell=21),"retrieve"),after


class StashReceiptContracts(unittest.TestCase):
    def test_drop_is_whole_stack_and_needs_accepted_matching_transfer(self):
        p,s,d,after,_=drop_fixture()
        self.assertIsInstance(p.potion_stash,StashWorkflow)
        self.assertFalse(p.potion_stash.dropped)
        receipt=observe_accepted(p,s,d,after)
        self.assertEqual(("drop",2),(receipt["kind"],receipt["quantity"]))
        self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)
        self.assertIsNone(p.potion_stash.pending)
        self.assertIsNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":2},p.potion_stash.dropped)
        json.dumps(receipt)

    def test_invalid_drop_receipts_retain_pending_obligation(self):
        for mode in ("no-proposal","replaced","no-removal","partial","no-ground",
                     "wrong-ground","small-ground","sale","wrong-origin",
                     "displaced","cross-floor","cross-branch","missing-inventory",
                     "missing-depth","missing-hero"):
            with self.subTest(mode=mode):
                p,s,d,after,candidate=drop_fixture()
                if mode=="no-proposal": d=Decision(d.action,"unowned drop")
                elif mode=="replaced": d.action=dict(type="wait")
                elif mode=="no-removal": after["inventory"]=copy.deepcopy(s["inventory"])
                elif mode=="partial":
                    after["inventory"].append(dict(s["inventory"][-1],quantity=1))
                elif mode=="no-ground": after["objects"]=[]
                elif mode=="wrong-ground": after["objects"][0]["top_item"]=dict(candidate)
                elif mode=="small-ground": after["objects"][0]["top_item"]=dict(
                    after["objects"][0]["top_item"],quantity=1)
                elif mode=="sale": after["objects"][0]["for_sale"]=True
                elif mode=="wrong-origin": s["hero"]["cell"]=22
                elif mode=="displaced": after["hero"]["cell"]=22
                elif mode=="cross-floor": after["depth"]+=1
                elif mode=="cross-branch": after["branch"]=1
                elif mode=="missing-inventory": del after["inventory"]
                elif mode=="missing-depth": del after["depth"]
                else: del after["hero"]
                self.assertIsNone(observe_accepted(p,s,d,after))
                self.assertFalse(p.potion_stash.dropped)
                self.assertIsNotNone(p.potion_stash.pending)

    def test_plausible_later_inventory_and_heap_are_not_drop_receipts(self):
        p,s,_,after,candidate=drop_fixture()
        p.loot[21]=after["objects"][0]
        with self.assertRaises(TacticalBlocked):
            advance_stash(p,after,[],distance)
        self.assertFalse(can_protect_potions(
            p,after,candidate,distance,neighbors,lambda *a,**k:True))
        with self.assertRaises(TacticalBlocked):
            protect_potions(p,after,candidate,distance,neighbors,lambda *a,**k:True)
        self.assertFalse(p.potion_stash.dropped)

    def test_interruption_does_not_discard_accepted_drop(self):
        p,s,d,after,_=drop_fixture()
        advance_stash(p,s,[dict(name="mimic",cell=25)],distance)
        self.assertEqual(StashPhase.RETRIEVE,p.potion_stash.phase)
        self.assertIsNotNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)

    def test_existing_matching_heap_needs_observed_quantity_change(self):
        p,s,d,after,_=drop_fixture()
        s["objects"]=copy.deepcopy(after["objects"])
        self.assertIsNone(observe_accepted(p,s,d,after))
        after["objects"][0]["top_item"]=dict(after["objects"][0]["top_item"],quantity=4)
        self.assertIsNotNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)

    def test_pickup_receipt_and_explicit_completion(self):
        p,s,d,after=pickup_fixture()
        receipt=observe_accepted(p,s,d,after)
        self.assertEqual(("pickup",2),(receipt["kind"],receipt["quantity"]))
        self.assertFalse(p.potion_stash.outstanding)
        self.assertIsNotNone(p.potion_stash)
        self.assertIsNone(observe_accepted(p,s,d,after))
        plan=p.potion_stash
        self.assertIsNone(advance_stash(p,after,[],distance))
        self.assertEqual(StashPhase.COMPLETE,plan.phase)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.loot_collection_receipts)

    def test_unrelated_matching_inventory_cannot_complete_retrieval(self):
        p,s,_,after=pickup_fixture()
        # Even ten carried doses do not prove this stash was retrieved.
        s["inventory"].append(dict(after["inventory"][-1],quantity=10))
        self.assertIsNotNone(advance_stash(p,s,[],distance))
        self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)

    def test_invalid_pickup_receipts_do_not_resolve_owned_items(self):
        for mode in ("no-gain","elsewhere","no-ground","sale","wrong-name","unchanged-heap",
                     "wrong-action","excess-gain","cross-floor","cross-branch"):
            with self.subTest(mode=mode):
                p,s,d,after=pickup_fixture()
                if mode=="no-gain": after["inventory"]=copy.deepcopy(s["inventory"])
                elif mode=="elsewhere":
                    d.action["cell"]=22
                    after["hero"]["cell"]=22
                elif mode=="no-ground": s["objects"]=[]
                elif mode=="sale": s["objects"][0]["for_sale"]=True
                elif mode=="unchanged-heap": after["objects"]=copy.deepcopy(s["objects"])
                elif mode=="wrong-name":
                    s["objects"][0]["top_item"]=dict(name="ivory potion",quantity=2)
                elif mode=="wrong-action": d.action=dict(type="wait")
                elif mode=="excess-gain": after["inventory"][-1]["quantity"]=3
                elif mode=="cross-floor": after["depth"]+=1
                else: after["branch"]=1
                self.assertIsNone(observe_accepted(p,s,d,after))
                self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)

    def test_partial_pickup_duplicates_and_multi_stack_counts(self):
        p,s,d,after=pickup_fixture()
        after["inventory"][-1]=dict(after["inventory"][-1],quantity=1)
        observe_accepted(p,s,d,after)
        self.assertEqual({"potion of strength":1},p.potion_stash.outstanding)
        self.assertIsNone(observe_accepted(p,s,d,after))
        self.assertEqual({"potion of strength":1},p.potion_stash.outstanding)
        # A second accepted pickup adds a separate stack with the same name.
        before=copy.deepcopy(after)
        before["objects"]=[dict(cell=21,top_item=dict(
            name="potion of strength",quantity=1))]
        after=copy.deepcopy(before)
        after["observation_id"]+=1
        after["inventory"].append(dict(name="potion of strength",quantity=1,id="second"))
        after["objects"]=[]
        self.assertIsNotNone(observe_accepted(p,before,d,after))
        self.assertFalse(p.potion_stash.outstanding)

    def test_multiple_whole_color_stacks_are_independently_reconciled(self):
        p,s,d,after,_=drop_fixture()
        third=dict(id="azure",name="azure potion",quantity=3,actions=["DROP","DRINK"])
        s["inventory"].append(third)
        after["inventory"].append(copy.deepcopy(third))
        observe_accepted(p,s,d,after)  # Whole strength stack, quantity two.
        p.loot[21]=after["objects"][0]
        d=advance_stash(p,after,[],distance)
        self.assertEqual("azure",d.action["id"])
        before=after
        after=copy.deepcopy(before)
        after["observation_id"]+=1
        after["inventory"]=[i for i in after["inventory"] if i["id"]!="azure"]
        strength_heap=copy.deepcopy(after["objects"][0])
        after["objects"]=[dict(cell=21,top_item=third)]
        observe_accepted(p,before,d,after)
        self.assertEqual({"potion of strength":2,"azure potion":3},
                         p.potion_stash.outstanding)
        self.assertEqual("reposition",advance_stash(p,after,[],distance).intent)
        self.assertEqual(StashPhase.READY,p.potion_stash.phase)
        # Cancel testing and retrieve both colors, one publicly visible heap
        # top at a time. No potion identity/effect or room completion is claimed.
        p.potion_stash.retrieve()
        after["hero"]["cell"]=24
        pickup=Decision(dict(type="cell",cell=21),"retrieve")
        for item,next_heap in ((third,[strength_heap]),(strength_heap["top_item"],[])):
            before=after
            after=copy.deepcopy(before)
            after["observation_id"]+=1
            after["hero"]["cell"]=21
            after["inventory"].append(copy.deepcopy(item))
            after["objects"]=next_heap
            self.assertIsNotNone(observe_accepted(p,before,pickup,after))
        self.assertFalse(p.potion_stash.outstanding)
        self.assertIsNone(advance_stash(p,after,[],distance))
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.loot_collection_receipts)

    def test_phase_guards_and_rollback(self):
        plan=StashWorkflow(depth=1,bank=24,cell=21,dropped={"ivory potion":1})
        plan.ready()
        with self.assertRaises(ValueError): plan.complete()
        plan.retrieve()
        with self.assertRaises(ValueError): plan.complete()
        plan.retrieved["ivory potion"]=1
        plan.complete()
        self.assertEqual(StashPhase.COMPLETE,plan.phase)
        p,s,_,_,_=drop_fixture()
        p.potion_stash.pending=None
        tx=Transaction(p)
        advance_stash(p,s,[],distance)
        self.assertIsNotNone(p.potion_stash.pending)
        tx.rollback()
        self.assertIsNone(p.potion_stash.pending)
        self.assertFalse(p.potion_stash.dropped)

    def test_forced_scope_change_keeps_old_floor_physical_obligations(self):
        for branch_change in (False,True):
            p,s,_,_=pickup_fixture()
            after=copy.deepcopy(s)
            after["observation_id"]+=1
            if branch_change: after["branch"]=1
            else: after["depth"]+=1
            self.assertIsNone(observe_accepted(p,s,Decision(dict(type="wait"),"transition"),after))
            record=p.deferred_obligations[0]
            self.assertEqual(s["depth"],record["depth"])
            self.assertEqual(s.get("branch",0),record["obligation"]["branch"])
            self.assertEqual({"potion of strength":2},record["obligation"]["outstanding"])
            p.update(after)
            self.assertTrue(p.deferred_obligations)
            self.assertFalse(p.loot_collection_receipts)

    def test_different_branches_do_not_collapse_owned_obligations(self):
        p,s,_,_=pickup_fixture()
        first=p.potion_stash
        second=StashWorkflow(depth=first.depth,branch=1,bank=24,cell=first.cell,
                             dropped=dict(first.dropped))
        self.assertTrue(p.physical_ledger.register(second))
        for _ in range(2):
            p.physical_ledger.defer(first,"scope change")
            p.physical_ledger.defer(second,"scope change")
        self.assertEqual([0,1],[r["branch"] for r in p.deferred_obligations])
        self.assertFalse(p.legacy_deferred_obligations)
        self.assertTrue(all(r["obligation"]["outstanding"]=={"potion of strength":2}
                            for r in p.deferred_obligations))

    def test_runner_reconciles_only_after_acceptance_and_logs_typed_state(self):
        from tools.player_api import PlayerAPIError
        from tools.policy_runner import run
        p,s,_,after,_=drop_fixture()
        p.potion_stash.pending=None

        class API:
            observation=s
            calls=0
            def state(self): return s
            def step(self,action):
                self.calls+=1
                if self.calls==1:
                    raise PlayerAPIError(409,"stale input")
                return after

        api=API()
        def check_reconciled(*args):
            self.assertIsNone(p.potion_stash.pending)
            self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            path=Path(directory)/"run.jsonl"
            with patch.object(p,"choose",side_effect=lambda state:advance_stash(p,state,[],distance)), \
                    patch("tools.descent_potions.observe",side_effect=check_reconciled) as consumer:
                result=run(api,p,2,0,path,bounded=True)
            rows=[json.loads(row) for row in path.read_text().splitlines()]
        self.assertEqual((2,1),(result["attempts"],result["actions"]))
        self.assertEqual({"potion of strength":2},p.potion_stash.outstanding)
        self.assertEqual(3,p.potion_stash.steps)  # Fixture's two selections + accepted one.
        self.assertEqual(1,sum("observed_potion_stash" in row for row in rows))
        self.assertTrue(any("rejected" in row for row in rows))
        self.assertEqual({"potion of strength":2},result["stash_workflow"]["outstanding"])
        self.assertTrue(any(row.get("stash_workflow",{}).get("pending") for row in rows))
        self.assertEqual(1,consumer.call_count)

    def test_ambiguous_execution_is_not_retried_or_credited(self):
        from tools.player_api import PlayerAPIError
        from tools.policy_runner import run
        p,s,_,_,_=drop_fixture()
        p.potion_stash.pending=None

        class API:
            observation=s
            calls=0
            def step(self,action):
                self.calls+=1
                raise PlayerAPIError(504,"execution status unknown")

        api=API()
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            with patch.object(p,"choose",side_effect=lambda state:advance_stash(p,state,[],distance)):
                with self.assertRaises(PlayerAPIError):
                    run(api,p,2,0,Path(directory)/"run.jsonl",bounded=True)
        self.assertEqual(1,api.calls)
        self.assertIsNotNone(p.potion_stash.pending)
        self.assertFalse(p.potion_stash.dropped)


if __name__=="__main__":
    unittest.main()
