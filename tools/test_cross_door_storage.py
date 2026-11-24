"""Synthetic gas preparation across an ordinary door, not a run-255 replay."""
import copy
import unittest

from tools.policy_geometry import distance, neighbors
from tools.policy_decision import Finished
from tools.potion_stash import (
    can_protect_potions,protect_potions,advance_stash,observe_accepted,
    quote_storage,stash_cells,fire_reaches_stash)
from tools.puzzle_supplies import safe_test_bank,prepare_supplies,recover_probe
from tools.loot_completion import observe_collected
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s=state()
    s["hero"].update(cell=49,hp=25,max_hp=25,strength=10,buffs=[])
    terrain={22:1,31:5,40:1,48:1,49:1,50:1,58:1,67:1,76:14}
    s["map"]=dict(width=9,height=10,cells=[
        dict(cell=c,terrain=terrain.get(c,4),observed=True,visible=True,
             effects=["cloud of toxic gas"] if c==67 else [])
        for c in range(90)])
    s["objects"]=[dict(cell=76,name="gold",top_item=dict(name="gold",quantity=10))]
    s["inventory"]=[
        dict(id="jade",name="jade potion",quantity=1,identified=False,actions=["DROP","DRINK"]),
        dict(id="other",name="turquoise potion x2",quantity=2,identified=False,actions=["DROP","DRINK"])]
    p=verified()
    p.update(s)
    return s,p


class CrossDoorStorageTests(unittest.TestCase):
    def test_opt_in_quotes_whole_transaction_not_door_storage(self):
        s,p=fixture()
        candidate=s["inventory"][0]
        self.assertFalse(can_protect_potions(p,s,candidate,distance,neighbors,safe_test_bank))
        self.assertTrue(can_protect_potions(p,s,candidate,distance,neighbors,safe_test_bank,through_doors=True))
        quote=quote_storage(p,s,22,candidate,distance,neighbors,safe_test_bank)
        self.assertEqual((49,40,31,22),quote.route)
        self.assertEqual((31,),quote.doors)
        self.assertEqual(13,quote.quoted_inputs)
        self.assertNotIn(31,stash_cells(p,s,distance,neighbors,safe_test_bank,through_doors=True))
        self.assertFalse(p.physical_ledger.entries)
        self.assertFalse(p.completed_room_rewards)

    def sequence(self,success):
        s,p=fixture()
        opened=0
        reclosed=False
        tested=False
        ordinary_retrieval=False
        contract=None
        for _ in range(60):
            action=recover_probe(p,s,[],distance,neighbors)
            if action is None and p.room_journey:
                action=p.room_journey.advance(p,s,[],neighbors)
            if action is None and p.potion_stash:
                action=advance_stash(p,s,[],distance)
            if action is None and not tested:
                action=prepare_supplies(p,s,[],distance,neighbors)
            if action is None:
                break
            if p.potion_stash:
                contract=p.potion_stash.storage_itinerary
                self.assertIsNotNone(contract)
                self.assertLessEqual(p.potion_stash.steps,48)
            after=copy.deepcopy(s)
            after["observation_id"]=s.get("observation_id",0)+1
            a=action.action
            if a["type"]=="cell":
                cell=a["cell"]
                tile=next(t for t in after["map"]["cells"] if t["cell"]==cell)
                if tile["terrain"]==5:
                    tile["terrain"]=6
                    opened+=1  # A door input did not move the hero.
                else:
                    old=after["hero"]["cell"]
                    after["hero"]["cell"]=cell
                    if old==31 and cell==40 and not reclosed:
                        next(t for t in after["map"]["cells"] if t["cell"]==31)["terrain"]=5
                        reclosed=True
                    obj=next((o for o in after["objects"] if o["cell"]==cell),None)
                    if obj:
                        if cell==22:
                            self.assertEqual("turquoise potion x2",obj["name"])
                            after["inventory"].append(obj["top_item"])
                        else:
                            after["hero"]["gold"]=s["hero"].get("gold",0)+10
                        after["objects"].remove(obj)
            elif a.get("action")=="DROP":
                item=next(i for i in after["inventory"] if i["id"]==a["id"])
                self.assertEqual(("other",2),(item["id"],item["quantity"]))
                after["inventory"].remove(item)
                after["objects"].append(dict(cell=22,name=item["name"],top_item=item))
            else:
                self.assertEqual(dict(type="item",id="jade",action="DRINK"),a)
                self.assertEqual(49,s["hero"]["cell"])
                self.assertEqual(["jade"],[i["id"] for i in s["inventory"]])
                after["inventory"]=[]
                tested=True
                after["hero"]["buffs"]=[dict(name="purification barrier",
                    description="Turns remaining: 20.")] if success else []
            observe_accepted(p,s,action,after)
            observe_collected(p,s,action,after)
            p.last_decision=action
            p.update(after)
            s=after
            if tested and not p.room_journey:
                s["hero"]["buffs"]=[]
                ordinary_retrieval=True
        else:
            self.fail("Bounded storage/test/return/retrieval sequence failed")
        self.assertTrue(tested)
        self.assertTrue(reclosed)
        self.assertEqual(2,opened)
        self.assertTrue(ordinary_retrieval)
        self.assertIsNotNone(contract)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.physical_ledger.has_unresolved())
        self.assertFalse(p.physical_ledger.claims)
        self.assertEqual(2,s["inventory"][0]["quantity"])
        self.assertFalse(p.strength_identified)
        self.assertEqual(success,(1,"gas",76) in p.completed_room_rewards)
        return s,p

    def test_real_provider_drop_observed_protection_reward_return_and_retrieval(self):
        self.sequence(True)

    def test_failed_effect_returns_all_owned_potions_without_reward_credit(self):
        s,p=self.sequence(False)
        self.assertIn(76,p.loot)
        self.assertFalse(p.completed_room_rewards)

    def test_unknown_hazardous_locked_or_bulk_door_does_not_get_a_quote(self):
        for case in ("unknown","trap","plant","effect","lock","bulk","unseen-site"):
            with self.subTest(case=case):
                s,p=fixture()
                if case=="unknown":p.tiles[31]["observed"]=False
                elif case=="trap":p.tiles[31]["trap"]="summoning trap"
                elif case=="plant":p.tiles[31]["plant"]="firebloom"
                elif case=="effect":p.tiles[31]["effects"]=["fire"]
                elif case=="lock":p.tiles[31]["terrain"]=10
                elif case=="bulk":s["inventory"].append(dict(name="cloth armor of bulk",equipped=True))
                else:p.tiles[22]["visible"]=False
                self.assertIsNone(quote_storage(p,s,22,s["inventory"][0],distance,neighbors,safe_test_bank))
                self.assertFalse(p.physical_ledger.entries)

    def test_flammable_door_is_not_a_collateral_firebreak(self):
        s,p=fixture()
        p.tiles[40]["terrain"]=2
        p.tiles[22]["terrain"]=2
        self.assertTrue(fire_reaches_stash(p,s,49,22))
        self.assertIsNone(quote_storage(p,s,22,s["inventory"][0],distance,neighbors,safe_test_bank))

    def test_arrival_scope_and_input_budget_remain_hard_guards(self):
        s,p=fixture()
        protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank,through_doors=True)
        s["hero"]["cell"]=22
        p.tiles[22]["effects"]=["fire"]
        with self.assertRaises(Finished):
            advance_stash(p,s,[],distance)
        s,p=fixture()
        protect_potions(p,s,s["inventory"][0],distance,neighbors,safe_test_bank,through_doors=True)
        s["branch"]=1
        with self.assertRaises(Finished):
            advance_stash(p,s,[],distance)
        s,p=fixture()
        s["inventory"].extend(dict(id=f"extra-{i}",name=f"extra-{i} potion",quantity=1,
                                   actions=["DROP"]) for i in range(40))
        self.assertIsNone(quote_storage(p,s,22,s["inventory"][0],distance,neighbors,safe_test_bank))

    def test_owned_storage_cannot_be_rebound_and_bank_loss_requests_retrieval(self):
        from tools.stash_workflow import StashWorkflow,StashPhase
        s,p=fixture()
        quote=quote_storage(p,s,22,s["inventory"][0],distance,neighbors,safe_test_bank)
        plan=StashWorkflow(depth=1,bank=49,cell=22,candidate="jade potion",
                           phase=StashPhase.READY,dropped={"turquoise potion":2},
                           storage_itinerary=quote)
        self.assertTrue(p.physical_ledger.register(plan))
        p.potion_stash=plan
        other=s["inventory"].pop()
        s["objects"].append(dict(cell=22,name=other["name"],top_item=other))
        p.update(s)
        moved=dict(s,hero=dict(s["hero"],cell=48))
        self.assertFalse(can_protect_potions(p,moved,s["inventory"][0],distance,neighbors,
                                           safe_test_bank,through_doors=True))
        with self.assertRaises(Finished):
            protect_potions(p,moved,s["inventory"][0],distance,neighbors,
                            safe_test_bank,through_doors=True)
        p.tiles[50]["plant"]="firebloom"
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual(StashPhase.RETRIEVE,plan.phase)
        self.assertEqual(dict(type="cell",cell=40),action.action)
        self.assertTrue(plan.outstanding)
        self.assertFalse(p.completed_room_rewards)


if __name__=="__main__":
    unittest.main()
