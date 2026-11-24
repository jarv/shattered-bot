"""Synthetic split-endpoint contracts, not run-206/208 counterfactual replays."""
import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from tools.test_survival_bot import state
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import Decision, TacticalBlocked
from tools.room_tactics import plan_journey
from tools.protected_rewards import (
    asymmetric_pool_plan, bind_test_storage, observe, travel_cost,
)
from tools.puzzle_supplies import safe_test_bank, entrance_actionable
from tools.puzzle_supplies import prepare_supplies, Demand
from tools.potion_stash import advance_stash, observe_accepted
from tools.stash_workflow import StashWorkflow
from tools.loot_completion import observe_collected as observe_collection


def fixture(other=False):
    s=state()
    s["hero"].update(cell=16,hp=30,max_hp=30,strength=10,buffs=[])
    terrains={**{c:1 for c in range(16,24)},24:6,25:29,26:11,31:1,46:1,61:1}
    s["map"]=dict(width=15,height=6,cells=[
        dict(cell=c,terrain=terrains.get(c,4),visible=True,observed=True,effects=[])
        for c in range(90)])
    s["objects"]=[dict(cell=26,name="Chest")]
    candidate=dict(id="ivory",name="ivory potion",quantity=1,identified=False,
                   actions=["DRINK","DROP"])
    s["inventory"].append(candidate)
    if other:
        s["inventory"].append(dict(id="azure",name="azure potion",quantity=2,
                                  identified=False,actions=["DRINK","DROP"]))
    p=verified()
    p.update(s)
    # Explicit bookkeeping premise for this synthetic geometry.
    p.piranha_rooms[26]=dict(water={25},collected=False)
    p.room_blocked.update({25,26})
    return p,s,candidate


def run_trip(p,s,trip):
    opened=False
    for tick in range(30):
        action=trip.advance(p,s,[],neighbors)
        if action is None:
            return s
        after=copy.deepcopy(s)
        after["observation_id"]+=1
        cell=action.action["cell"]
        if cell==26 and not opened:
            opened=True
            reward=dict(id="loot",name="scroll of upgrade",quantity=1)
            after["objects"]=[o for o in after["objects"] if o["cell"]!=26]+[
                dict(cell=26,name=reward["name"],top_item=reward)]
        elif cell==26:
            after["hero"]["cell"]=26
            obj=next(o for o in after["objects"] if o["cell"]==26)
            after["inventory"].append(obj["top_item"])
            after["objects"].remove(obj)
        else:
            after["hero"]["cell"]=cell
        after["hero"]["buffs"]=[dict(name="invisible",description=f"Remaining: {19-tick}")]
        observe_collection(p,s,action,after)
        observe(p)
        p.loot={o["cell"]:o for o in after["objects"]}
        s=after
    raise AssertionError("Split-endpoint trip did not finish")


class PreparationItineraryContracts(unittest.TestCase):
    def test_long_symmetric_trip_gets_distinct_return_without_door_testing(self):
        p,s,_=fixture()
        trip=plan_journey(p,s,[],neighbors,probe_kind="pool",plan_only=True)
        self.assertIsNotNone(trip)
        contract=trip.itinerary
        self.assertEqual((16,24,26,24,16),(contract.test_bank,contract.work_origin,
                         contract.work_target,contract.success_return,contract.failure_bank))
        self.assertLessEqual(contract.quoted_cost,20)
        symmetric=2*travel_cost(p,contract.outbound,reserve_doors=True)+2+3
        self.assertGreater(symmetric,20)
        self.assertTrue(safe_test_bank(p,s,16,distance,neighbors,allow_dry=True,pool_bank=True))
        self.assertFalse(safe_test_bank(p,s,24,distance,neighbors,allow_dry=True,pool_bank=True))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.physical_ledger.entries)
        json.dumps(contract.record())

    def test_stash_requires_ordinary_handoff_and_preserves_read_only_preflight(self):
        p,s,candidate=fixture(other=True)
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        before=copy.deepcopy(p.physical_ledger)
        self.assertTrue(bind_test_storage(p,s,trip,candidate,distance,neighbors,safe_test_bank))
        contract=trip.itinerary
        self.assertTrue(contract.unknown_test_admitted)
        self.assertEqual(61,contract.storage_cell)
        self.assertEqual((24,61),(contract.handoff_route[0],contract.handoff_route[-1]))
        self.assertEqual(before,p.physical_ledger)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)

    def test_unreachable_or_hazardous_stash_handoff_declines(self):
        for mode in ("hazard","constraint"):
            p,s,candidate=fixture(other=True)
            trip=asymmetric_pool_plan(p,s,p.paths(s))
            if mode=="hazard":
                p.tiles[22]["effects"]=["A fire is raging here."]
            else:
                p.escape_commitment=dict(edges=[(23,24)],hp=30,charges=0,age=0)
            self.assertFalse(bind_test_storage(p,s,trip,candidate,distance,neighbors,safe_test_bank))
            self.assertFalse(p.physical_ledger.entries)
            self.assertFalse(p.completed_room_rewards)

    def test_unsafe_or_unobserved_exit_does_not_become_return_bank(self):
        for mode in ("effect","unobserved","trap","danger"):
            p,s,_=fixture()
            if mode=="effect": p.tiles[24]["effects"]=["toxic gas"]
            elif mode=="unobserved": p.tiles[24]["observed"]=False
            elif mode=="trap": p.tiles[24]["trap"]="dart trap"
            else: s["danger_cells"]=[24]
            self.assertIsNone(asymmetric_pool_plan(p,s,p.paths(s)))

    def test_closed_return_door_keeps_scouting_prerequisite(self):
        p,s,_=fixture()
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        p.tiles[24]["terrain"]=5
        self.assertFalse(entrance_actionable(p,s,trip))
        p.pool_entrance_receipts.add((s["depth"],s.get("branch",0),24))
        self.assertTrue(entrance_actionable(p,s,trip))
        self.assertEqual(1,travel_cost(p,[23,24],reserve_doors=True)-1)

    def test_failed_hypothesis_cancels_without_reward_or_physical_debt(self):
        for cell in (16,24):
            p,s,_=fixture()
            trip=asymmetric_pool_plan(p,s,p.paths(s))
            p.room_journey=trip
            s["hero"]["cell"]=cell
            self.assertIsNone(trip.advance(p,s,[],neighbors))
            self.assertIsNone(p.room_journey)
            self.assertFalse(p.physical_ledger.has_unresolved())
            self.assertFalse(p.completed_room_rewards)

    def test_real_effect_and_fresh_return_budget_are_required(self):
        p,s,_=fixture()
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        p.room_journey=trip
        s["hero"]["buffs"]=[dict(name="invisible",description="Remaining: 2")]
        with self.assertRaises(TacticalBlocked):
            trip.advance(p,s,[],neighbors)
        self.assertFalse(p.completed_room_rewards)

    def test_split_trip_completes_only_after_actual_pickup_and_safe_return(self):
        p,s,_=fixture()
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        p.room_journey=trip
        s["hero"]["buffs"]=[dict(name="invisible",description="Remaining: 20")]
        s=run_trip(p,s,trip)
        self.assertIsNone(p.room_journey)
        self.assertEqual(24,s["hero"]["cell"])
        self.assertIn(26,trip.collected)
        self.assertIn((1,"pool",26),p.completed_room_rewards)
        self.assertNotEqual(trip.itinerary.test_bank,s["hero"]["cell"])

    def test_arrival_at_safe_endpoint_does_not_need_imaginary_extra_protection(self):
        p,s,_=fixture()
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        trip.stage="return"
        p.room_journey=trip
        s["hero"]["cell"]=24
        self.assertIsNone(trip.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)  # Arrival is not a pickup.

    def test_unknown_test_cannot_burn_an_older_deferred_owned_stash(self):
        p,s,candidate=fixture()
        old=StashWorkflow(depth=1,bank=20,cell=17,dropped={"azure potion":2})
        self.assertTrue(p.physical_ledger.register(old))
        p.physical_ledger.defer(old,"old blocked return")
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        self.assertFalse(bind_test_storage(p,s,trip,candidate,distance,neighbors,safe_test_bank))
        self.assertTrue(p.physical_ledger.has_unresolved())
        self.assertFalse(p.puzzle_drinks)

    def test_bulk_and_wrong_role_routes_are_not_certified(self):
        p,s,_=fixture()
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        with self.assertRaises(ValueError):
            replace(trip.itinerary,success_return=31)
        s["inventory"].append(dict(name="cloth armor of bulk",equipped=True))
        self.assertIsNone(asymmetric_pool_plan(p,s,p.paths(s)))

    def test_real_preparation_then_trip_and_independent_owned_item_handoff(self):
        p,s,_=fixture(other=True)
        with patch("tools.puzzle_supplies.demands",
                   return_value=[Demand("pool","potion of invisibility",26)]):
            for _ in range(24):
                action=advance_stash(p,s,[],distance) if p.potion_stash else None
                action=action or prepare_supplies(p,s,[],distance,neighbors)
                self.assertIsNotNone(action)
                after=copy.deepcopy(s)
                after["observation_id"]+=1
                if action.action.get("action")=="DRINK":
                    self.assertEqual("ivory",action.action["id"])
                    after["inventory"]=[i for i in after["inventory"] if i["id"]!="ivory"]
                    # Explicit synthetic successful observation, not identity inferred
                    # from the planner's hypothesis. No harmful effect in this case.
                    after["hero"]["buffs"]=[dict(name="invisible",description="Remaining: 20")]
                    s=after
                    p.puzzle_probe=None
                    break
                if action.action.get("action")=="DROP":
                    item=next(i for i in after["inventory"] if i["id"]==action.action["id"])
                    self.assertEqual(("azure",2),(item["id"],item["quantity"]))
                    after["inventory"].remove(item)
                    after["objects"].append(dict(cell=61,name=item["name"],top_item=item))
                else:
                    after["hero"]["cell"]=action.action["cell"]
                observe_accepted(p,s,action,after)
                p.loot={o["cell"]:o for o in after["objects"]}
                s=after
            else:
                self.fail("Preparation failed to reach its admitted test")
        trip=p.room_journey
        self.assertEqual(61,p.potion_stash.cell)
        self.assertEqual(61,trip.itinerary.storage_cell)
        s=run_trip(p,s,trip)
        self.assertEqual(24,s["hero"]["cell"])
        self.assertTrue(p.physical_ledger.has_unresolved())
        s["hero"]["buffs"]=[]  # Storage handoff cannot depend on protection.
        for _ in range(20):
            action=advance_stash(p,s,[],distance)
            if action is None:
                break
            after=copy.deepcopy(s)
            after["observation_id"]+=1
            after["hero"]["cell"]=action.action["cell"]
            obj=next((o for o in after["objects"] if o["cell"]==after["hero"]["cell"]
                      and o.get("top_item")),None)
            if obj:
                after["inventory"].append(obj["top_item"])
                after["objects"].remove(obj)
            observe_accepted(p,s,action,after)
            p.loot={o["cell"]:o for o in after["objects"]}
            s=after
        else:
            self.fail("Ordinary storage handoff failed to finish")
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.physical_ledger.has_unresolved())
        self.assertFalse(p.physical_ledger.claims)
        self.assertEqual(2,next(i["quantity"] for i in s["inventory"] if i["id"]=="azure"))
        self.assertIn((1,"pool",26),p.completed_room_rewards)
        self.assertFalse(p.strength_identified)

    def test_storage_on_protected_route_is_not_an_unbudgeted_transit_pickup(self):
        p,s,candidate=fixture(other=True)
        p.tiles[46]["terrain"]=4
        p.tiles[61]["terrain"]=4
        trip=asymmetric_pool_plan(p,s,p.paths(s))
        self.assertFalse(bind_test_storage(p,s,trip,candidate,distance,neighbors,safe_test_bank))
        self.assertFalse(p.physical_ledger.entries)


if __name__=="__main__":
    unittest.main()
