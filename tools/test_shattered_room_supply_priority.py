"""Runs 23/24: room priority, accepted off-purpose use, and honest descent."""
import copy
import unittest
from unittest.mock import patch

from tools.test_challenge_rules import verified
from tools.test_pool_and_mirror_passage import pool_room
from tools.test_regular_feedback import arena
from tools.test_consumable_tactics import potion
from tools.puzzle_supplies import Demand, demands
from tools.room_supplies import POTIONS, allowed, use, observe, depleted, deferred_loot, requirements
from tools.loot_completion import required_loot, pending_collections
from tools.policy_decision import Decision, Intent, GameplayBlocked, Finished
from tools.policy_runtime import Transaction
from tools.survival_policy import SurvivalPolicy
from tools.policy_geometry import distance
from tools.priority_resources import targets
from tools.pickup_priority import replacements


def acquired(p, state, item):
    after = copy.deepcopy(state)
    if not any(i.get("id") == item["id"] for i in after["inventory"]):
        after["inventory"].append(copy.deepcopy(item))
    before = copy.deepcopy(after)
    before["inventory"] = [i for i in before["inventory"] if i.get("id") != item["id"]]
    before["objects"] = [dict(cell=before["hero"]["cell"], name=item["name"], top_item=copy.deepcopy(item))]
    observe(p,before,Decision(dict(type="cell",cell=before["hero"]["cell"]),"pickup"),after)
    return after


def spent(p, state, item, purpose=None):
    after = copy.deepcopy(state)
    after["inventory"] = [i for i in after["inventory"] if i.get("id") != item["id"]]
    d = Decision(dict(type="item",id=item["id"],action="DRINK"),"accepted use")
    if purpose:d.potion_purpose=purpose
    observe(p,state,d,after)
    return after


class SupplyReceiptTests(unittest.TestCase):
    def test_each_recognized_potion_is_reserved_but_intended_use_is_allowed(self):
        for kind,name in POTIONS.items():
            with self.subTest(kind=kind):
                s,_=arena();item=potion(name);s["inventory"].append(item)
                p=verified();p.update(s)
                with patch("tools.room_supplies.requirements",return_value=[Demand(kind,name,25)]):
                    self.assertFalse(allowed(p,item,"DRINK"))
                    self.assertFalse(allowed(p,item,"THROW"))
                    self.assertTrue(allowed(p,item,"DROP"))  # Disposal policy has its own reservation.
                    d=use(p,item,"DRINK","planned room use",kind=kind)
                    self.assertEqual(kind,d.potion_purpose)
                    self.assertIsNone(p.room_supply_permit)
                    s=acquired(p,s,item)
                    after=spent(p,s,item,kind)
                    self.assertFalse(depleted(p,after))
                    self.assertFalse(p.room_supply_spent_elsewhere)

    def test_each_confirmed_floor_supply_spent_elsewhere_can_defer_its_room(self):
        for kind,name in POTIONS.items():
            with self.subTest(kind=kind):
                s,p=arena();p=verified();p.update(s)
                item=potion(name);s=acquired(p,s,item)
                with patch("tools.room_supplies.requirements",return_value=[Demand(kind,name,25)]):
                    after=spent(p,s,item,"emergency")
                    self.assertEqual({kind},depleted(p,after))
                    replacement=copy.deepcopy(after);replacement["inventory"].append(item)
                    self.assertFalse(depleted(p,replacement))
                    p.loot[25]=dict(cell=25,name=name,top_item=item)
                    self.assertFalse(depleted(p,after))  # Ground replacement is not lost supply.

    def test_extra_copies_are_available_but_carried_previous_floor_supply_is_not_a_floor_receipt(self):
        s,_=arena();item=potion("potion of invisibility",2);s["inventory"].append(item)
        p=verified();p.update(s)
        with patch("tools.room_supplies.requirements",return_value=[Demand("pool",item["name"],25)]):
            self.assertTrue(allowed(p,item,"DRINK"))
            after=spent(p,s,item)
            self.assertFalse(depleted(p,after))

    def test_shared_levitation_needs_reserve_two_doses_from_disposal_and_combat(self):
        s,_=arena();item=potion("potion of levitation",2);s["inventory"].append(item)
        p=verified();p.update(s)
        wanted=[Demand("flight",item["name"],25),Demand("fall",item["name"],26)]
        with patch("tools.room_supplies.requirements",return_value=wanted):
            self.assertFalse(allowed(p,item,"DRINK"))
            self.assertFalse(any(i["id"]==item["id"] for i in replacements(p,s,dict(name="ration of food"))))

    def test_unknown_floor_pickup_can_be_publicly_identified_then_spent(self):
        s,_=arena();p=verified();p.update(s)
        unknown=potion("azure potion");s=acquired(p,s,unknown)
        known=potion("potion of invisibility");after=copy.deepcopy(s)
        after["inventory"]=[known if i["id"]==unknown["id"] else i for i in after["inventory"]]
        observe(p,s,Decision(dict(type="button",id="confirm"),"intuition"),after)
        self.assertEqual(1,p.room_supply_pickups[known["name"]])
        final=spent(p,after,known)
        self.assertIn(known["name"],p.room_supply_spent_elsewhere)
        self.assertNotIn(known["name"],[i["name"] for i in final["inventory"]])

    def test_unknown_singleton_requires_observed_protection_not_a_color_guess(self):
        s,_=arena();p=verified();p.update(s);item=potion("azure potion")
        s=acquired(p,s,item);after=copy.deepcopy(s);after["inventory"]=[i for i in after["inventory"] if i["id"]!=item["id"]]
        after["hero"]["buffs"]=[dict(name="invisible",description="Turns of invisibility remaining: 20.")]
        observe(p,s,Decision(dict(type="item",id=item["id"],action="DRINK"),"drink"),after)
        self.assertIn("potion of invisibility",p.room_supply_spent_elsewhere)
        self.assertEqual("azure potion",item["name"])

    def test_proposal_drop_cancel_and_different_floor_do_not_prove_consumption(self):
        for mode in ("unchanged","drop","cancel","floor"):
            with self.subTest(mode=mode):
                s,_=arena();p=verified();p.update(s);item=potion("potion of invisibility")
                s=acquired(p,s,item);after=copy.deepcopy(s)
                d=Decision(dict(type="item",id=item["id"],action="DRINK"),"proposal")
                observe(p,s,d,after)
                if mode=="drop":
                    after["inventory"]=[i for i in after["inventory"] if i["id"]!=item["id"]]
                    observe(p,s,Decision(dict(type="item",id=item["id"],action="DROP"),"drop"),after)
                elif mode=="cancel":observe(p,s,Decision(dict(type="back"),"cancel"),after)
                elif mode=="floor":
                    after["depth"]+=1
                    observe(p,s,d,after)
                self.assertFalse(p.room_supply_spent_elsewhere)

    def test_throw_consumption_is_recorded_only_on_accepted_target_confirmation(self):
        s,_=arena();p=verified();p.update(s);item=potion("potion of frost")
        s=acquired(p,s,item);opening=Decision(dict(type="item",id=item["id"],action="THROW"),"throw")
        observe(p,s,opening,copy.deepcopy(s));self.assertFalse(p.room_supply_spent_elsewhere)
        after=copy.deepcopy(s);after["inventory"]=[i for i in after["inventory"] if i["id"]!=item["id"]]
        observe(p,s,Decision(dict(type="cell",cell=25),"target"),after)
        self.assertIn(item["name"],p.room_supply_spent_elsewhere)

    def test_intended_room_throw_keeps_its_purpose_through_targeting(self):
        s,_=arena();p=verified();p.update(s);item=potion("potion of frost")
        s=acquired(p,s,item)
        opening=use(p,item,"THROW","room: extinguish barrier",kind="frost",target=25)
        observe(p,s,opening,copy.deepcopy(s))
        after=copy.deepcopy(s);after["inventory"]=[i for i in after["inventory"] if i["id"]!=item["id"]]
        observe(p,s,Decision(dict(type="cell",cell=25),"target"),after)
        self.assertFalse(p.room_supply_spent_elsewhere)

    def test_distant_well_reserves_finished_protection_before_a_crafting_ingredient(self):
        s,_=arena()
        next(t for t in s["map"]["cells"] if t["cell"]==41).update(terrain=0,name="Distant well")
        feather=potion("elixir of feather fall");levitation=potion("potion of levitation")
        s["inventory"] += [feather,levitation]
        p=verified();p.update(s)
        self.assertEqual(["elixir of feather fall"],[d.potion for d in requirements(p,s) if d.kind=="fall"])
        self.assertFalse(allowed(p,feather,"DRINK"))
        self.assertTrue(allowed(p,levitation,"DRINK"))

    def test_receipts_reset_on_floor_change_and_roll_back_with_rejected_selection(self):
        s,_=arena();p=verified();p.update(s);item=potion("potion of invisibility")
        transaction=Transaction(p);s=acquired(p,s,item);spent(p,s,item)
        self.assertTrue(p.room_supply_spent_elsewhere)
        transaction.rollback();self.assertFalse(p.room_supply_spent_elsewhere)
        s=acquired(p,s,item);spent(p,s,item);p.memory.reset_floor(25)
        self.assertFalse(p.room_supply_spent_elsewhere);self.assertFalse(p.room_supply_pickups)


class PoolDescentTests(unittest.TestCase):
    def fixture(self):
        s,p=pool_room(True)
        item=next(i for i in s["inventory"] if i["name"]=="potion of invisibility")
        s=acquired(p,s,item);after=spent(p,s,item)
        p.update(after)
        return after,p,item

    def test_run23_unused_room_supply_is_not_offered_for_a_snake(self):
        s,p=pool_room(True)
        item=next(i for i in s["inventory"] if i["name"]=="potion of invisibility")
        self.assertFalse(p.item_action_allowed(item,"DRINK"))
        with self.assertRaises(Finished):p.use(item,"DRINK","snake surprise")
        self.assertIn(41,p.piranha_rooms)
        self.assertFalse(p.room_supply_spent_elsewhere)

    def test_run24_unresolved_preparation_alone_is_not_a_spent_supply_receipt(self):
        s,p=pool_room(False)
        p.puzzle_revisit_steps["pool"]=48
        self.assertFalse(depleted(p,s))
        with patch.object(SurvivalPolicy,"choose",return_value=Decision(dict(type="cell",cell=23),"stairs",intent=Intent.DESCEND)):
            with self.assertRaisesRegex(GameplayBlocked,"Piranha-room chest"):p.choose(s)

    def test_spent_supply_releases_only_that_chest_without_collection_or_clear_credit(self):
        s,p,_=self.fixture()
        self.assertEqual({"pool"},depleted(p,s))
        self.assertIn(41,deferred_loot(p,s))
        self.assertIn(41,required_loot(p))
        self.assertFalse(pending_collections(p))
        p.stop_on_incomplete_loot=True
        with patch.object(SurvivalPolicy,"choose",return_value=Decision(dict(type="cell",cell=23),"stairs",intent=Intent.DESCEND)):
            d=p.choose(s)
        self.assertEqual(Intent.DESCEND,d.intent)
        self.assertFalse(p.piranha_rooms[41]["collected"])
        self.assertFalse(p.descent_counts_as_clear())
        p.loot[35]=dict(cell=35,name="chest")  # Ordinary unrelated loot still matters.
        self.assertTrue(pending_collections(p))
        with patch.object(SurvivalPolicy,"choose",return_value=Decision(dict(type="cell",cell=23),"stairs",intent=Intent.DESCEND)):
            self.assertNotEqual(Intent.DESCEND,p.choose(s).intent)

    def test_replacement_restores_room_priority_and_descent_guard(self):
        s,p,item=self.fixture();s["inventory"].append(item);p.update(s)
        self.assertFalse(depleted(p,s))
        self.assertFalse(p.item_action_allowed(item,"DRINK"))
        with patch.object(SurvivalPolicy,"choose",return_value=Decision(dict(type="cell",cell=23),"stairs",intent=Intent.DESCEND)):
            with self.assertRaisesRegex(GameplayBlocked,"Piranha-room chest"):p.choose(s)


class BarrierDeferralTests(unittest.TestCase):
    def fixture(self,kind):
        s,_=arena()
        s["hero"]["cell"]=47
        s["map"]=dict(width=11,height=9,cells=[
            dict(cell=c,terrain=1 if 45<=c<=53 else 4,visible=True,observed=True) for c in range(99)])
        next(t for t in s["map"]["cells"] if t["cell"]==46)["terrain"]=8
        barrier=next(t for t in s["map"]["cells"] if t["cell"]==49)
        if kind=="frost":barrier["effects"]=["Magical fire"]
        elif kind=="gas":barrier["effects"]=["A cloud of toxic gas is swirling here."]
        elif kind=="flame":barrier["terrain"]=13
        else:barrier["terrain"]=0
        s["objects"]=[dict(cell=51,name="potion of strength",
                           top_item=dict(name="potion of strength",identified=True,quantity=1))]
        p=verified();p.update(s)
        item=potion(POTIONS[kind]);s=acquired(p,s,item);s=spent(p,s,item);p.update(s)
        return s,p

    def test_each_exhausted_barrier_can_defer_only_its_inaccessible_progression_loot(self):
        for kind in ("frost","flame","flight","gas"):
            with self.subTest(kind=kind):
                s,p=self.fixture(kind)
                self.assertIn(kind,depleted(p,s))
                self.assertIn(51,deferred_loot(p,s))
                self.assertIn(51,required_loot(p))
                self.assertNotIn(51,targets(p))
                p.stop_on_incomplete_loot=True
                with patch.object(SurvivalPolicy,"choose",return_value=Decision(dict(type="cell",cell=46),"stairs",intent=Intent.DESCEND)):
                    self.assertEqual(Intent.DESCEND,p.choose(s).intent)
                self.assertFalse(p.descent_counts_as_clear())

    def test_exhausted_frost_does_not_waive_an_additional_toxic_barrier(self):
        s,p=self.fixture("frost")
        p.tiles[50]["effects"]=["A cloud of toxic gas is swirling here."]
        p.room_blocked.add(50)
        self.assertNotIn(51,deferred_loot(p,s))
        self.assertIn(51,targets(p))


if __name__=="__main__":unittest.main()
