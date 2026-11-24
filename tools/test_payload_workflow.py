"""Synthetic custody sequences; no trap-activation or game-completion claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.payload_workflow import throw, observe_landing, PayloadPhase
from tools.owned_transfers import observe_pickup
from tools.environment_tactics import recover_trap_payload
from tools.policy_decision import Decision, TacticalBlocked
from tools.policy_geometry import distance, neighbors, line_clear
from tools.policy_runtime import Transaction
from tools.tactical_recovery import recover
from tools.stash_workflow import StashWorkflow
from tools.floor_abandonment import FloorAbandonment


def proposed(quantity=1,spare=False,disarm_required=True):
    from tools import test_environment_quest as fixtures
    s,p=fixtures.EnvironmentTests().setup_arena()
    skin=dict(id="skin",name="waterskin",quantity=quantity,status="20/20",
              actions=["THROW","DRINK"])
    s["inventory"]=[skin]
    if spare:
        s["inventory"].append(dict(skin,id="spare",quantity=1))
    tile=next(t for t in s["map"]["cells"] if t["cell"]==43)
    tile.update(terrain=18,trap="chilling trap")
    p.update(s)
    action=throw(p,s,skin,43,"synthetic remote activation",disarm_required=disarm_required)
    return p,s,action


def landed(quantity=1,spare=False,disarm_required=True):
    p,b,d=proposed(quantity,spare,disarm_required)
    targeting=copy.deepcopy(b)
    targeting.update(status="targeting",observation_id=b["observation_id"]+1)
    observe_landing(p,b,d,targeting)
    after=copy.deepcopy(targeting)
    after.update(status="ready",observation_id=targeting["observation_id"]+1)
    item=after["inventory"][0]
    ground=dict(item,quantity=1)
    if quantity==1: after["inventory"].pop(0)
    else: item["quantity"]-=1
    after["objects"]=[dict(cell=43,name=ground["name"],top_item=ground)]
    receipt=observe_landing(p,targeting,Decision(dict(type="cell",cell=43),"aim"),after)
    assert receipt["kind"]=="payload-landed"
    p.update(after)
    return p,after,p.trap_payload_return


def disarmed(p,s,effects=()):
    after=copy.deepcopy(s)
    after["observation_id"]+=1
    next(t for t in after["map"]["cells"] if t["cell"]==43).update(
        terrain=19,effects=list(effects))
    p.update(after)
    return after


def picked(p,s,quantity=1):
    before=copy.deepcopy(s)
    before["hero"]["cell"]=42
    obj=next(o for o in before["objects"] if o["cell"]==43)
    obj["top_item"]=dict(obj["top_item"],quantity=quantity)
    after=copy.deepcopy(before)
    after["hero"]["cell"]=43
    after["observation_id"]+=1
    after["inventory"].append(dict(obj["top_item"],id="recovered"))
    after["objects"]=[]
    d=Decision(dict(type="cell",cell=43),"accepted pickup")
    return before,d,after


class PayloadCustodyContracts(unittest.TestCase):
    def test_proposal_and_targeting_are_not_landing_or_disarm(self):
        p,b,d=proposed()
        plan=p.trap_payload_return
        self.assertFalse(plan.dropped)
        self.assertFalse(p.physical_ledger.has_unresolved())
        t=copy.deepcopy(b)
        t.update(status="targeting",observation_id=2)
        self.assertIsNone(observe_landing(p,b,d,t))
        self.assertEqual(PayloadPhase.AIMING,plan.phase)
        self.assertFalse(plan.dropped)
        self.assertEqual(18,p.tiles[43]["terrain"])
        self.assertFalse(p.completed_room_rewards)

    def test_landing_preserves_full_container_and_does_not_authorize_active_plate(self):
        p,s,plan=landed()
        self.assertEqual({"waterskin":1},plan.outstanding)
        self.assertEqual("20/20",s["objects"][0]["top_item"]["status"])
        self.assertEqual(18,p.tiles[43]["terrain"])
        self.assertIsNone(recover_trap_payload(p,s,[]))
        self.assertIs(plan,p.physical_ledger.entries[plan.owner])
        self.assertTrue(p.physical_ledger.has_unresolved())

    def test_matching_spare_or_remaining_stack_does_not_resolve_owned_unit(self):
        for qty,spare in ((1,True),(3,False)):
            p,s,plan=landed(qty,spare)
            self.assertTrue(s["inventory"])
            s=disarmed(p,s)
            self.assertIsNotNone(recover_trap_payload(p,s,[]))
            self.assertEqual({"waterskin":1},plan.outstanding)
            self.assertIsNotNone(p.trap_payload_return)

    def test_only_matching_pickup_completes_then_releases_claims(self):
        p,s,plan=landed(spare=True)
        s=disarmed(p,s)
        before,d,after=picked(p,s)
        self.assertEqual(1,observe_pickup(p,before,d,after)["quantity"])
        self.assertIsNone(observe_pickup(p,before,d,after))
        self.assertIsNotNone(p.trap_payload_return)
        p.update(after)
        self.assertIsNone(recover_trap_payload(p,after,[]))
        self.assertIsNone(p.trap_payload_return)
        self.assertEqual(PayloadPhase.COMPLETE,plan.phase)
        self.assertFalse(p.physical_ledger.claims)
        self.assertFalse(p.physical_ledger.has_unresolved())
        self.assertFalse(p.completed_room_rewards)

    def test_residual_cloud_and_current_threat_still_block_retrieval(self):
        p,s,_=landed()
        s=disarmed(p,s,["A freezing cloud is swirling here."])
        self.assertIsNone(recover_trap_payload(p,s,[]))
        s=disarmed(p,s)
        self.assertIsNone(recover_trap_payload(p,s,[dict(name="rat",cell=42)]))
        self.assertTrue(p.physical_ledger.has_unresolved())

    def test_missing_landing_or_wrong_target_preserves_uncertainty_not_confirmation(self):
        for mode in ("no-ground","sale","wrong-name","missing-inventory","retarget","no-owner",
                     "retained-inventory"):
            p,b,d=proposed()
            t=copy.deepcopy(b)
            t.update(status="targeting",observation_id=2)
            if mode=="no-owner": del d.payload_owner
            observe_landing(p,b,d,t)
            a=copy.deepcopy(t)
            a.update(status="ready",observation_id=3,inventory=[])
            item=dict(b["inventory"][0])
            a["objects"]=[dict(cell=43,top_item=item)]
            target=44 if mode=="retarget" else 43
            if mode=="no-ground": a["objects"]=[]
            elif mode=="sale": a["objects"][0]["for_sale"]=True
            elif mode=="wrong-name": a["objects"][0]["top_item"]=dict(name="dagger")
            elif mode=="missing-inventory": del a["inventory"]
            elif mode=="retained-inventory": a["inventory"]=copy.deepcopy(b["inventory"])
            event=observe_landing(p,t,Decision(dict(type="cell",cell=target),"aim"),a)
            self.assertEqual("payload-landing-unverified",event["kind"],mode)
            self.assertFalse(p.trap_payload_return.dropped)
            self.assertTrue(p.physical_ledger.has_unresolved())
            self.assertFalse(event["trap_activation_verified"])

    def test_cancel_and_preempt_release_only_unexecuted_claims(self):
        for aim in (False,True):
            p,b,d=proposed()
            before=b
            if aim:
                before=copy.deepcopy(b)
                before.update(status="targeting",observation_id=2)
                observe_landing(p,b,d,before)
            after=copy.deepcopy(before)
            after.update(status="ready",observation_id=before["observation_id"]+1)
            action=dict(type="back") if aim else dict(type="wait")
            observe_landing(p,before,Decision(action,"cancel/preempt"),after)
            self.assertIsNone(p.trap_payload_return)
            self.assertFalse(p.physical_ledger.has_unresolved())
            self.assertFalse(p.physical_ledger.claims)
            self.assertFalse(p.deferred_obligations)

    def test_unchanged_inventory_after_confirmed_landing_cannot_cancel_debt(self):
        p,s,plan=landed(spare=True)
        after=copy.deepcopy(s)
        after["observation_id"]+=1
        observe_landing(p,s,Decision(dict(type="wait"),"other work"),after)
        self.assertEqual(PayloadPhase.LANDED,plan.phase)
        self.assertEqual({"waterskin":1},plan.outstanding)

    def test_unverified_landing_is_not_paid_by_an_unrelated_matching_container(self):
        p,b,d=proposed()
        after=copy.deepcopy(b)
        after.update(observation_id=b["observation_id"]+1,inventory=[],objects=[])
        observe_landing(p,b,d,after)
        self.assertEqual(PayloadPhase.UNVERIFIED,p.trap_payload_return.phase)
        another=copy.deepcopy(after)
        another["observation_id"]+=1
        another["inventory"]=[dict(b["inventory"][0],id="unrelated")]
        observe_landing(p,after,Decision(dict(type="wait"),"other acquisition"),another)
        self.assertTrue(p.physical_ledger.has_unresolved())
        self.assertIsNotNone(p.trap_payload_return.unverified_drop)
        self.assertFalse(p.trap_payload_return.dropped)

    def test_later_recycled_inventory_id_does_not_create_another_payload_uncertainty(self):
        from tools.owned_transfers import unknown_execution
        p,s,plan=landed()
        decision=Decision(dict(type="item",id=plan.item_id,action="THROW"),"another item")
        self.assertFalse(unknown_execution(p,s,decision,"unrelated API failure"))
        self.assertEqual(PayloadPhase.LANDED,plan.phase)
        self.assertIsNone(plan.unverified_drop)
        self.assertEqual({"waterskin":1},plan.outstanding)

    def test_budget_exhaustion_defers_single_account_and_orphan_pickup_can_settle_it(self):
        p,s,plan=landed()
        s=disarmed(p,s)
        plan.steps=16
        with self.assertRaises(TacticalBlocked) as caught:
            recover_trap_payload(p,s,[])
        recover(p,s,[],caught.exception,distance,neighbors,line_clear)
        self.assertIsNone(p.trap_payload_return)
        self.assertFalse(p.legacy_deferred_obligations)
        self.assertEqual(1,len(p.deferred_obligations))
        p.stop_on_incomplete_loot=False
        self.assertIn("owned item debt",FloorAbandonment(p).hard_gate(s))
        before,d,after=picked(p,s)
        self.assertIsNotNone(observe_pickup(p,before,d,after))
        self.assertFalse(p.deferred_obligations)
        self.assertIsNone(p.trap_payload_return)
        self.assertEqual("settled",plan.physical_record()["status"])

    def test_floor_branch_transition_does_not_erase_payload(self):
        for branch in (False,True):
            p,s,plan=landed()
            after=copy.deepcopy(s)
            after["observation_id"]+=1
            if branch: after["branch"]=s.get("branch",0)+1
            else: after["depth"]+=1
            observe_landing(p,s,Decision(dict(type="wait"),"displaced"),after)
            p.update(after)
            self.assertEqual({"waterskin":1},plan.outstanding)
            self.assertTrue(p.deferred_obligations)
            self.assertEqual(1,len(p.physical_ledger.entries))

    def test_seed_controller_still_requires_clear_effects_but_not_fake_disarm(self):
        p,s,_=landed(disarm_required=False)
        # A plant is not an active trap; the producer supplies that distinction.
        for tile in s["map"]["cells"]:
            if tile["cell"]==43: tile.update(terrain=1,trap=None,effects=["cold cloud"])
        p.update(s)
        self.assertIsNone(recover_trap_payload(p,s,[]))
        for tile in s["map"]["cells"]:
            if tile["cell"]==43: tile["effects"]=[]
        p.update(s)
        self.assertIsNotNone(recover_trap_payload(p,s,[]))

    def test_shared_pickup_credits_owned_units_not_entire_mixed_heap(self):
        p,s,plan=landed()
        s=disarmed(p,s)
        before,d,after=picked(p,s,quantity=4)
        receipt=observe_pickup(p,before,d,after)
        self.assertEqual((1,4),(receipt["quantity"],receipt["inventory_gain"]))
        self.assertEqual({"waterskin":1},plan.retrieved)
        self.assertFalse(plan.outstanding)

    def test_paid_owner_does_not_block_combat_priority_reuse_before_cleanup_leaf(self):
        p,s,old=landed()
        s=disarmed(p,s)
        before,d,after=picked(p,s)
        observe_pickup(p,before,d,after)
        self.assertIs(old,p.trap_payload_return)  # Cleanup leaf has not run.
        item=next(i for i in after["inventory"] if i["id"]=="recovered")
        action=throw(p,after,item,49,"new admitted remote transaction")
        self.assertIsNotNone(action)
        self.assertEqual(PayloadPhase.COMPLETE,old.phase)
        self.assertNotEqual(old.owner,p.trap_payload_return.owner)
        self.assertFalse(old.outstanding)
        self.assertEqual("settled",old.physical_record()["status"])
        self.assertFalse(p.trap_payload_return.dropped)

    def test_resource_conflicts_do_not_replace_existing_owner(self):
        p,s,d=proposed()
        old=p.trap_payload_return
        self.assertIsNone(throw(p,s,s["inventory"][0],44,"second throw"))
        self.assertIs(old,p.trap_payload_return)
        self.assertEqual(1,len(p.physical_ledger.entries))
        p.physical_ledger.finish(old)
        p.trap_payload_return=None
        stash=StashWorkflow(depth=s["depth"],bank=40,cell=43,dropped={"ivory potion":1})
        self.assertTrue(p.physical_ledger.register(stash))
        self.assertIsNone(throw(p,s,s["inventory"][0],43,"cannot take owned site"))
        self.assertEqual({"ivory potion":1},stash.outstanding)

    def test_transaction_restores_one_canonical_payload_account(self):
        p,b,d=proposed()
        owner=p.trap_payload_return.owner
        tx=Transaction(p)
        targeting=copy.deepcopy(b)
        targeting.update(status="targeting",observation_id=2)
        observe_landing(p,b,d,targeting)
        after=copy.deepcopy(targeting)
        after.update(status="ready",observation_id=3,inventory=[],
                     objects=[dict(cell=43,top_item=b["inventory"][0])])
        observe_landing(p,targeting,Decision(dict(type="cell",cell=43),"aim"),after)
        self.assertTrue(p.trap_payload_return.outstanding)
        tx.rollback()
        self.assertIs(p.trap_payload_return,p.physical_ledger.entries[owner])
        self.assertEqual(PayloadPhase.PROPOSED,p.trap_payload_return.phase)
        self.assertFalse(p.trap_payload_return.dropped)
        self.assertFalse(p.physical_ledger.receipts)
        self.assertTrue(p.physical_ledger.claims)

    def test_runner_rejection_targeting_landing_order_and_json(self):
        from tools.player_api import PlayerAPIError
        from tools.policy_runner import run
        p,s,_=proposed()
        p.physical_ledger.finish(p.trap_payload_return)
        p.trap_payload_return=None
        class API:
            observation=s
            calls=0
            def state(self): return self.observation
            def step(self,action):
                self.calls+=1
                if self.calls==1: raise PlayerAPIError(409,"stale input")
                after=copy.deepcopy(self.observation)
                after["observation_id"]+=1
                if action["type"]=="item": after["status"]="targeting"
                else:
                    after["status"]="ready"
                    item=after["inventory"].pop()
                    after["objects"]=[dict(cell=43,name=item["name"],top_item=item)]
                self.observation=after
                return after
        def choose(state):
            p.update(state)
            if state["status"]=="targeting":
                return p.cell(43,"target payload")
            return throw(p,state,state["inventory"][0],43,"remote throw")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            path=Path(directory)/"run.jsonl"
            with patch.object(p,"choose",side_effect=choose):
                result=run(API(),p,3,0,path,bounded=True)
            rows=[json.loads(row) for row in path.read_text().splitlines()]
        self.assertEqual((3,2),(result["attempts"],result["actions"]))
        self.assertEqual({"waterskin":1},p.trap_payload_return.outstanding)
        self.assertEqual(1,sum("observed_payload_landing" in row for row in rows))
        self.assertTrue(any(row.get("payload_workflow",{}).get("phase")=="aiming" for row in rows))

    def test_ambiguous_execution_is_not_retried_and_is_not_a_landing(self):
        from tools.player_api import PlayerAPIError
        from tools.policy_runner import run
        p,s,_=proposed()
        p.physical_ledger.finish(p.trap_payload_return)
        p.trap_payload_return=None
        class API:
            observation=s
            calls=0
            def step(self,action):
                self.calls+=1
                raise PlayerAPIError(504,"execution status unknown")
        api=API()
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            path=Path(directory)/"run.jsonl"
            with patch.object(p,"choose",side_effect=lambda state:
                              throw(p,state,state["inventory"][0],43,"remote throw")):
                with self.assertRaises(PlayerAPIError):
                    run(api,p,3,0,path,bounded=True)
            rows=[json.loads(row) for row in path.read_text().splitlines()]
        self.assertEqual(1,api.calls)
        self.assertFalse(p.trap_payload_return.dropped)
        self.assertEqual(PayloadPhase.UNVERIFIED,p.trap_payload_return.phase)
        self.assertTrue(p.physical_ledger.has_unresolved())
        self.assertTrue(any("ambiguous_owned_transfer" in row for row in rows))


if __name__=="__main__":
    unittest.main()
