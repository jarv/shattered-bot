"""Gas scouting is observation work, never a test-bank or reward receipt."""
import copy
import unittest

from tools.policy_decision import Intent
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Transaction
from tools.puzzle_supplies import demands,revisit_flight_room,safe_test_bank,stage_known_gas,prepare_supplies
from tools.loot_completion import observe_collected
from tools.test_cross_door_storage import fixture as storage_fixture


def fixture():
    s,p=storage_fixture()
    s["hero"]["cell"]=31
    for t in s["map"]["cells"]:
        if t["cell"]==31:t["terrain"]=6
        if t["cell"]==85:t.update(terrain=14,effects=["cloud of toxic gas"])
    s["objects"][0]["cell"]=85
    stone=dict(id="stone",name="stone of intuition",quantity=1,actions=["USE"])
    s["objects"].append(dict(cell=22,name=stone["name"],top_item=stone))
    p.update(s)
    return s,p,next(d for d in demands(p,s,distance) if d.kind=="gas")


def accepted(p,s,action,cell=None):
    after=copy.deepcopy(s)
    after["observation_id"]=s.get("observation_id",0)+1
    if cell is not None:after["hero"]["cell"]=cell
    p.last_decision=action
    p.update(after)
    return after


class GasApproachReceiptTests(unittest.TestCase):
    def test_completed_scout_yields_to_stone_pickup_instead_of_reversing_loot(self):
        s,p,demand=fixture()
        scout=revisit_flight_room(p,s,demand,distance)
        self.assertEqual(dict(type="cell",cell=40),scout.action)
        s=accepted(p,s,scout,40)
        p.visits.update({c:1 for c in p.paths(s)})
        ordinary=p.explore(s,[])
        self.assertEqual(dict(type="cell",cell=31),ordinary.action)
        s=accepted(p,s,ordinary,31)
        # Original policy returns toward 40 here and repeats until exhaustion.
        self.assertIsNone(revisit_flight_room(p,s,demand,distance))
        self.assertIn((1,0,67,40),p.gas_approach_receipts)
        ordinary=p.explore(s,[])
        self.assertEqual(dict(type="cell",cell=22),ordinary.action)
        after=copy.deepcopy(s)
        after["hero"]["cell"]=22
        stone=next(o for o in after["objects"] if o["cell"]==22)
        after["inventory"].append(stone["top_item"])
        after["objects"].remove(stone)
        observe_collected(p,s,ordinary,after)
        p.last_decision=ordinary
        p.update(after)
        self.assertTrue(any(i["name"]=="stone of intuition" for i in after["inventory"]))
        self.assertIn(85,p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.physical_ledger.has_unresolved())
        self.assertTrue(safe_test_bank(p,after,40,distance,neighbors,allow_dry=True))
        information=prepare_supplies(p,after,[],distance,neighbors)
        self.assertEqual(dict(type="item",id="stone",action="USE"),information.action)
        self.assertEqual("potion of purity",p.intuition_plan["guess"])
        self.assertFalse(any(i.get("identified") for i in after["inventory"] if "potion" in i["name"]))

    def test_intermediate_input_preserves_pending_but_is_not_arrival(self):
        s,p,demand=fixture()
        p.puzzle_gas_bank=49
        action=revisit_flight_room(p,s,demand,distance)
        self.assertEqual((1,0,67,49),p.gas_approach_pending)
        self.assertEqual(40,action.action["cell"])
        s=accepted(p,s,action,40)
        self.assertEqual((1,0,67,49),p.gas_approach_pending)
        self.assertFalse(p.gas_approach_receipts)
        action=revisit_flight_room(p,s,demand,distance)
        s=accepted(p,s,action,49)
        self.assertIn((1,0,67,49),p.gas_approach_receipts)
        self.assertIsNone(p.gas_approach_pending)

    def test_rejection_failure_wrong_intent_and_scope_do_not_receipt_arrival(self):
        for case in ("rejected","stationary","other-controller","branch","unseen"):
            with self.subTest(case=case):
                s,p,demand=fixture()
                tx=Transaction(p)
                action=revisit_flight_room(p,s,demand,distance)
                if case=="rejected":
                    tx.rollback()
                    self.assertIsNone(p.gas_approach_pending)
                else:
                    after=copy.deepcopy(s)
                    after["hero"]["cell"]=31 if case=="stationary" else 40
                    if case=="other-controller":action=p.cell(40,"unowned",intent=Intent.EXPLORE)
                    if case=="branch":after["branch"]=1
                    if case=="unseen":
                        next(t for t in after["map"]["cells"] if t["cell"]==40)["visible"]=False
                    p.last_decision=action
                    p.update(after)
                self.assertFalse(p.gas_approach_receipts)
                self.assertFalse(p.completed_room_rewards)

    def test_receipt_preserves_existing_bounds_and_does_not_forget_new_room(self):
        s,p,demand=fixture()
        action=revisit_flight_room(p,s,demand,distance)
        s=accepted(p,s,action,40)
        self.assertEqual(1,p.puzzle_revisit_steps["gas"])
        for _ in range(3):self.assertIsNone(revisit_flight_room(p,s,demand,distance))
        self.assertEqual(1,p.puzzle_revisit_steps["gas"])
        from tools.puzzle_supplies import Demand
        p.puzzle_revisit_steps["gas"]=48
        self.assertIsNone(revisit_flight_room(p,s,Demand("gas","potion of purity",76),distance))
        self.assertEqual(48,p.puzzle_revisit_steps["gas"])
        p.memory.reset_floor(31)
        self.assertFalse(p.gas_approach_receipts)
        self.assertIsNone(p.gas_approach_pending)
        self.assertIsNone(p.puzzle_gas_bank)

    def test_known_purity_still_requires_actual_buff_then_receipted_reward_and_return(self):
        s,p,demand=fixture()
        action=revisit_flight_room(p,s,demand,distance)
        s=accepted(p,s,action,40)
        # Independent public identification fixture, not an inferred result of
        # the recorded run or a successful guess. No unknown potion is drunk.
        s["inventory"][0].update(name="potion of purity",identified=True)
        p.update(s)
        drank=False
        for _ in range(40):
            if p.room_journey:
                action=p.room_journey.advance(p,s,[],neighbors)
            else:
                action=None if drank else stage_known_gas(p,s,s["inventory"][0],neighbors)
            if action is None:
                break
            after=copy.deepcopy(s)
            after["observation_id"]+=1
            if action.action["type"]=="cell":
                cell=action.action["cell"]
                if p.tiles[cell].get("effects"):
                    self.assertTrue(drank)
                    self.assertTrue(after["hero"]["buffs"])
                after["hero"]["cell"]=cell
                if cell==85:
                    after["objects"]=[o for o in after["objects"] if o["cell"]!=85]
                    after["hero"]["gold"]=10
            else:
                self.assertEqual(dict(type="item",id="jade",action="DRINK"),action.action)
                drank=True
                after["inventory"]=after["inventory"][1:]
                after["hero"]["buffs"]=[dict(name="purification barrier",
                    description="Turns remaining: 20.")]
            observe_collected(p,s,action,after)
            p.last_decision=action
            p.update(after)
            s=after
        else:self.fail("Known-protection trip failed its existing finite bound")
        self.assertTrue(drank)
        self.assertIsNone(p.room_journey)
        self.assertNotIn(85,p.loot)
        self.assertIn((1,"gas",85),p.completed_room_rewards)
        self.assertFalse(p.physical_ledger.has_unresolved())


if __name__=="__main__":
    unittest.main()
