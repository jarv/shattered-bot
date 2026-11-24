"""Public knowledge distinctions and causal retirement, not gameplay replays."""
import copy
import json
import unittest

from tools.public_evidence import (
    TileEvidence, Mechanism, ThreatRef, RetirementRule, bind_threat,
)
from tools.combat_observation import observe_accepted_attack, retirement_proof
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_shattered_arcane_missile_same_level import fixture


def prepared():
    before,targeting,after=fixture()
    before["observation_id"]=1
    targeting["observation_id"]=2
    after["observation_id"]=3
    p=verified()
    p.update(before)
    p.ranged_plan=dict(name="dm-100",mode="cover",goal=1144)
    bind_threat(p,before,p.ranged_plan,1140)
    d=p.use(before["inventory"][0],"ZAP","cast",target=1140)
    observe_accepted_attack(p,before,d,targeting)
    return p,targeting,after


class PublicFactContracts(unittest.TestCase):
    def test_mapping_never_implies_observed_geometry(self):
        fact=TileEvidence.of(dict(terrain=1,mapped=True,observed=False,visible=False))
        self.assertTrue(fact.mapped)
        self.assertFalse(fact.observed)
        self.assertEqual(Mechanism.UNKNOWN,fact.mechanism)
        # Missing old-schema observed flags retain the prior visible fallback.
        self.assertTrue(TileEvidence.of(dict(terrain=1,visible=True)).observed)
        self.assertFalse(TileEvidence.of(dict(terrain=1,visible=True,observed=False)).observed)

    def test_mechanism_identity_status_and_effects_are_independent(self):
        for terrain,expected in ((18,Mechanism.ACTIVE),(19,Mechanism.INACTIVE),
                                 (1,Mechanism.UNKNOWN)):
            fact=TileEvidence.of(dict(terrain=terrain,visible=True,trap="toxic vent",
                                      effects=["cloud of toxic gas"],plant="firebloom"))
            self.assertEqual(expected,fact.mechanism)
            self.assertEqual("toxic vent",fact.trap_identity)
            self.assertEqual(("cloud of toxic gas",),fact.effects)
            self.assertEqual("firebloom",fact.plant)
            self.assertFalse(hasattr(fact,"safe"))
            json.dumps(fact.record())

    def test_unseen_mapping_does_not_prove_trap_inactivity(self):
        fact=TileEvidence.of(dict(terrain=19,mapped=True,visible=False,observed=False,
                                  trap="burning trap"))
        self.assertEqual(Mechanism.UNKNOWN,fact.mechanism)
        self.assertEqual("burning trap",fact.trap_identity)
        self.assertEqual(Mechanism.UNKNOWN,TileEvidence.of({}).mechanism)


class CausalRetirementContracts(unittest.TestCase):
    def test_matching_accepted_receipt_releases_only_actor_derived_state(self):
        p,before,after=prepared()
        p.escape_commitment=dict(edges=[(1140,1144)],hp=12,charges=2,age=0)
        feedback=observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        event=feedback["threat_retirement"]
        self.assertEqual(RetirementRule.ARCANE_MISSILE_XP.value,event["rule"])
        self.assertEqual({"dm100-lightning-lane","dm100-ranged-plan","recent-threat"},
                         set(event["invalidated"]))
        self.assertIsNone(p.dm100_threat)
        self.assertIsNone(p.ranged_plan)
        self.assertNotIn(1140,p.recent_threats)
        # Generic pursuit edges need their own stricter last-foe receipt.
        self.assertEqual([(1140,1144)],p.escape_commitment["edges"])
        self.assertEqual({"threat_retirement"},set(feedback))
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)
        json.dumps(event)

    def test_different_explicit_plan_source_is_not_retired(self):
        p,before,after=prepared()
        p.ranged_plan["threat_ref"]=ThreatRef.observed(before,1100).record()
        old=copy.deepcopy(p.ranged_plan)
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        self.assertIsNone(p.dm100_threat)
        self.assertEqual(old,p.ranged_plan)

    def test_explicit_legacy_last_seen_also_keeps_unrelated_plan(self):
        p,before,after=prepared()
        p.ranged_plan=dict(name="dm-100",last_seen=1100,mode="door-flight")
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        self.assertIsNotNone(p.ranged_plan)
        self.assertIsNone(p.dm100_threat)

    def test_late_receipt_cannot_clear_newer_facts_at_the_same_site(self):
        p,before,after=prepared()
        proof=retirement_proof(before,after,p.damage_pending,set(before["ui"]["texts"]))
        newer=copy.deepcopy(before)
        newer["status"]="ready"
        newer["observation_id"]=4
        newer["evaluation_stats"]["elapsed_turns"]=3181
        p.update(newer)
        bind_threat(p,newer,p.ranged_plan,1140)
        old_lane=copy.deepcopy(p.dm100_threat)
        old_plan=copy.deepcopy(p.ranged_plan)
        event=p.evidence_reducer.retire(p,proof)
        self.assertFalse(event["invalidated"])
        self.assertEqual(old_lane,p.dm100_threat)
        self.assertEqual(old_plan,p.ranged_plan)
        self.assertIn(1140,p.recent_threats)

    def test_duplicate_receipts_do_not_invalidate_later_sightings(self):
        p,before,after=prepared()
        proof=retirement_proof(before,after,p.damage_pending,set(before["ui"]["texts"]))
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        newer=copy.deepcopy(before)
        newer.update(status="ready",observation_id=4)
        newer["evaluation_stats"]["elapsed_turns"]=3181
        p.update(newer)
        self.assertIsNotNone(p.dm100_threat)
        self.assertIsNone(p.evidence_reducer.retire(p,proof))
        self.assertIsNotNone(p.dm100_threat)
        self.assertEqual(1,len(p.evidence_reducer.retirements))

    def test_disappearance_or_retained_text_is_not_a_kill_receipt(self):
        for retained in (False,True):
            p,before,after=prepared()
            after["evaluation_stats"]["experience"]=before["evaluation_stats"]["experience"]
            if retained:
                before["ui"]["texts"].append("You defeated DM-100.")
                after["ui"]["texts"].append("You defeated DM-100.")
            observe_accepted_attack(p,before,p.cell(1140,"target"),after)
            self.assertIsNotNone(p.dm100_threat)
            self.assertIsNotNone(p.ranged_plan)
            self.assertFalse(p.evidence_reducer.retirements)

    def test_targeting_selection_cancellation_has_no_retirement(self):
        p,before,after=prepared()
        observe_accepted_attack(p,before,p.decision(dict(type="back"),"cancel"),after)
        self.assertFalse(p.evidence_reducer.retirements)
        self.assertIsNotNone(p.dm100_threat)

    def test_scope_invalidation_is_not_reported_as_defeat(self):
        from tools.dm100_escape import exposed_memory
        p,before,_=prepared()
        other=copy.deepcopy(before)
        other.update(status="ready",branch=1,observation_id=4,objects=[])
        self.assertFalse(exposed_memory(p,other))  # Even before the next update.
        self.assertIsNotNone(p.dm100_threat)
        p.update(other)
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.evidence_reducer.retirements)

    def test_unseen_plan_binding_reuses_evidence_without_new_sighting(self):
        p,before,_=prepared()
        remembered=copy.deepcopy(p.dm100_threat["threat_ref"])
        hidden=copy.deepcopy(before)
        hidden.update(status="ready",observation_id=9,objects=[])
        slot=dict(name="dm-100")
        bind_threat(p,hidden,slot,1140)
        self.assertEqual(remembered,slot["threat_ref"])
        unbound=dict(name="dm-100")
        bind_threat(p,hidden,unbound,1100)
        self.assertNotIn("threat_ref",unbound)

    def test_transaction_restores_evidence_and_vetoes_together(self):
        p,before,after=prepared()
        snapshot=copy.deepcopy(p.dm100_threat)
        tx=Transaction(p)
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        self.assertTrue(p.evidence_reducer.retirements)
        tx.rollback()
        self.assertEqual(snapshot,p.dm100_threat)
        self.assertFalse(p.evidence_reducer.retirements)
        self.assertFalse(p.evidence_reducer.seen)

    def test_pending_capture_scope_and_causal_order_are_required(self):
        for mode in ("capture-floor","capture-branch","backward-observation"):
            p,before,after=prepared()
            if mode=="capture-floor":
                context=p.damage_pending["context"]
                p.damage_pending["context"]=(context[0]-1,*context[1:])
            elif mode=="capture-branch": p.damage_pending["branch"]=1
            else: after["observation_id"]=0
            observe_accepted_attack(p,before,p.cell(1140,"target"),after)
            self.assertIsNotNone(p.dm100_threat)
            self.assertFalse(p.evidence_reducer.retirements)

    def test_retirement_audit_survives_floor_reset_without_becoming_a_tombstone(self):
        p,before,after=prepared()
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        following=copy.deepcopy(after)
        following["depth"]+=1
        following["observation_id"]+=1
        p.update(following)
        self.assertEqual(1,len(p.evidence_reducer.retirements))
        self.assertIsNone(p.dm100_threat)
        following["objects"]=copy.deepcopy(before["objects"])
        following["observation_id"]+=1
        p.update(following)
        self.assertIsNotNone(p.dm100_threat)
        self.assertEqual(following["depth"],p.dm100_threat["threat_ref"]["depth"])

    def test_same_name_defeat_message_with_multiple_casters_is_ambiguous(self):
        p,before,after=prepared()
        before["objects"].append(dict(name="DM-100",cell=1100))
        after["ui"]["texts"].append("You defeated DM-100.")
        observe_accepted_attack(p,before,p.cell(1140,"target"),after)
        self.assertIsNotNone(p.dm100_threat)
        self.assertFalse(p.evidence_reducer.retirements)
        self.assertFalse(p.damage_samples)


if __name__=="__main__":
    unittest.main()
