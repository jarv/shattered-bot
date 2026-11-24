import unittest
import copy

from tools.test_challenge_systems import ready, item
from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.policy_decision import Finished, Decision
from tools.potion_stash import protect_potions, advance_stash, observe_accepted


class PotionStashTests(unittest.TestCase):
    def setup_stash(self):
        s,p=ready()
        candidate=dict(item("crimson potion","DRINK"),id="candidate")
        other=dict(item("potion of strength","DRINK"),id="other",actions=["DRINK","DROP"],quantity=2)
        s["inventory"] += [candidate,other]
        for c in (21,22,23,24):p.tiles[c]["terrain"]=1
        p.paths=lambda state,occupied=():{24:None,23:24,22:23,21:22}
        safe=lambda *args,**kwargs:args[2]==21
        return s,p,candidate,other,safe

    def start(self):
        s,p,candidate,other,safe=self.setup_stash()
        action=protect_potions(p,s,candidate,distance,neighbors,safe)
        self.assertEqual(23,action.action.get("cell"))
        self.assertEqual("reposition",action.intent)
        s["hero"]["cell"]=21
        action=advance_stash(p,s,[],distance)
        self.assertEqual("DROP",action.action.get("action"))
        self.assertEqual("other",action.action.get("id"))
        self.drop_action=action
        return s,p,candidate,other

    def test_drop_confirm_separate_drink_and_retrieve_after_chill(self):
        s,p,candidate,other=self.start()
        before=copy.deepcopy(s)
        s["observation_id"]+=1
        s["inventory"].remove(other)
        s["objects"]=[dict(cell=21,name=other["name"],top_item=other)]
        p.loot[21]={"name":"potion of strength","top_item":other}
        self.assertIsNotNone(observe_accepted(p,before,self.drop_action,s))
        action=advance_stash(p,s,[],distance)
        self.assertEqual("reposition",action.intent)
        self.assertEqual({"potion of strength":2},p.potion_stash["dropped"])
        s["hero"]["cell"]=24
        self.assertIsNone(advance_stash(p,s,[],distance))
        p.potion_stash["phase"]="retrieve"
        s["hero"]["buffs"]=[{"name":"chilled"}]
        self.assertIsNone(advance_stash(p,s,[],distance))
        self.assertIsNotNone(p.potion_stash)
        s["hero"]["buffs"]=[]
        self.assertEqual("loot",advance_stash(p,s,[],distance).intent)
        before=copy.deepcopy(s)
        s["observation_id"]+=1
        s["hero"]["cell"]=21
        s["inventory"].append(other)
        s["objects"]=[]
        self.assertIsNotNone(observe_accepted(p,before,Decision(dict(type="cell",cell=21),"pickup"),s))
        self.assertIsNone(advance_stash(p,s,[],distance))
        self.assertIsNone(p.potion_stash)

    def test_failed_drop_is_not_treated_as_protected_inventory(self):
        s,p,candidate,other=self.start()
        with self.assertRaises(Finished):advance_stash(p,s,[],distance)

    def test_interrupt_keeps_retrieval_obligation(self):
        s,p,candidate,other=self.start()
        before=copy.deepcopy(s)
        s["observation_id"]+=1
        s["inventory"].remove(other)
        s["objects"]=[dict(cell=21,name=other["name"],top_item=other)]
        p.loot[21]={"name":"potion of strength","top_item":other}
        observe_accepted(p,before,self.drop_action,s)
        self.assertIsNone(advance_stash(p,s,[{"name":"mimic","cell":25}],distance))
        self.assertEqual("retrieve",p.potion_stash["phase"])
        self.assertIsNone(p.potion_stash["pending"])
        self.assertEqual({"potion of strength":2},p.potion_stash["dropped"])

    def test_candidate_stack_and_missing_safe_stash_refuse_drink(self):
        s,p,candidate,other,safe=self.setup_stash()
        candidate["quantity"]=2
        with self.assertRaises(Finished):protect_potions(p,s,candidate,distance,neighbors,safe)
        candidate["quantity"]=1
        for c in (21,22,23):p.tiles[c]["effects"]=["fire"]
        with self.assertRaises(Finished):protect_potions(p,s,candidate,distance,neighbors,lambda *a,**k:False)

    def test_rejected_drop_rolls_back_owned_plan(self):
        s,p,candidate,other=self.start()
        p.potion_stash["pending"]=None
        before=Transaction(p)
        advance_stash(p,s,[],distance)
        before.rollback()
        self.assertIsNone(p.potion_stash["pending"])
