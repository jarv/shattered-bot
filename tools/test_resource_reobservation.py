"""Fresh observation of a cached cloud is not expiry, protection or collection."""
import copy
import unittest
from unittest.mock import patch

from tools.resource_reobservation import choose,ResourceView
from tools.priority_resources import choose as priority,targets
from tools.objective_planning import observe
from tools.objective_episodes import Scope
from tools.loot_completion import observe_collected
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s=state()
    s.update(depth=4,branch=0)
    s["hero"].update(cell=10,hp=30,max_hp=30,buffs=[])
    floor=set(range(10,17))
    s["map"]=dict(width=9,height=7,cells=[
        dict(cell=c,terrain=1 if c in floor else 10 if c==40 else 4,
             observed=True,visible=True,
             effects=["A cloud of confusion gas is swirling here."] if c in {15,16} else [])
        for c in range(63)])
    s["objects"]=[dict(cell=16,name="iron key",top_item=dict(name="iron key",quantity=1))]
    s["inventory"]=[]
    p=verified()
    p.update(s)
    s["objects"]=[]
    for t in s["map"]["cells"]:
        if t["cell"] in {15,16}:t["visible"]=False
    p.update(s)
    return s,p


class ResourceReobservationTests(unittest.TestCase):
    def test_priority_handoff_observed_clearance_then_real_key_receipt(self):
        s,p=fixture()
        self.assertNotIn(16,p.paths(s))
        for count in range(2):
            action=choose(p,s,targets(p),[],start=True) if count==0 else priority(p,s,[])
            self.assertEqual(dict(type="cell",cell=11+count),action.action)
            self.assertFalse(p.planner.report["resource_reobservation"]["hazard_retired"])
            after=copy.deepcopy(s)
            after["observation_id"]=s.get("observation_id",0)+1
            after["hero"]["cell"]=action.action["cell"]
            if count==1:
                for t in after["map"]["cells"]:
                    if t["cell"] in {15,16}:t.update(visible=True,effects=[])
                after["objects"]=[dict(cell=16,name="iron key",top_item=dict(name="iron key",quantity=1))]
            observe(p,s,action,after)
            p.last_decision=action
            p.update(after)
            s=after
            self.assertFalse(p.loot_collection_receipts)
        self.assertIn(16,targets(p))
        for _ in range(5):
            action=priority(p,s,[])
            if action is None:break
            self.assertIsNone(p.resource_view_plan)
            after=copy.deepcopy(s)
            after["observation_id"]+=1
            after["hero"]["cell"]=action.action["cell"]
            if action.action["cell"]==16:
                after["objects"]=[]
                after["keys"]=[dict(name="iron key",depth=4,quantity=1)]
            observe_collected(p,s,action,after)
            p.last_decision=action
            p.update(after)
            s=after
        self.assertEqual(16,s["hero"]["cell"])
        self.assertNotIn(16,targets(p))
        self.assertFalse(p.completed_room_rewards)
        self.assertEqual(2,p.objective_progress["resource-observation:4:0:16"]["accepted"])

    def test_arrival_with_fog_or_persistent_cloud_never_clears_it(self):
        s,p=fixture()
        p.resource_view_plan=ResourceView(Scope.of(s),16,10)
        action=choose(p,s,targets(p),[],start=True)
        self.assertEqual("search",action.action["type"])
        self.assertIsNone(choose(p,s,targets(p),[]))
        self.assertTrue(p.tiles[16]["effects"])
        self.assertNotIn(16,p.paths(s))
        p.tiles[16]["visible"]=True
        self.assertIsNone(choose(p,s,targets(p),[]))
        self.assertTrue(p.tiles[16]["effects"])
        self.assertIn(16,targets(p))
        self.assertFalse(p.loot_collection_receipts)

    def test_pause_and_rejection_preserve_vantage_and_owned_budget(self):
        s,p=fixture()
        action=choose(p,s,targets(p),[],start=True)
        self.assertEqual(12,p.resource_view_plan.vantage)
        p.recent_threats[11]=dict(cell=11,name="rat")
        self.assertIsNone(choose(p,s,targets(p),[]))
        self.assertEqual(12,p.resource_view_plan.vantage)
        self.assertFalse(p.objective_progress)
        p.recent_threats.clear()
        tx=Transaction(p)
        p.resource_view_plan.searched=True
        tx.rollback()
        self.assertFalse(p.resource_view_plan.searched)
        self.assertEqual(action.action,choose(p,s,targets(p),[]).action)

    def test_safety_effect_type_budget_and_known_route_guards(self):
        for case in ("enemy","recent","damage","warning","burning","owned","unknown",
                     "toxic","fire","visible","wall","navigation","hunger","budget","standing-cloud"):
            with self.subTest(case=case):
                s,p=fixture()
                enemies=[]
                if case=="enemy":enemies=[dict(cell=11,name="rat")]
                elif case=="recent":p.recent_threats[11]=dict(cell=11,name="rat")
                elif case=="damage":p.unseen_damage_turns=1
                elif case=="warning":s["danger_cells"]=[11]
                elif case=="burning":s["hero"]["buffs"]=[dict(name="burning")]
                elif case=="owned":p.room_journey=object()
                elif case=="unknown":p.tiles[16]["observed"]=False
                elif case=="toxic":p.tiles[16]["effects"]=["cloud of toxic gas"]
                elif case=="fire":p.tiles[16]["effects"]=["magical fire"]
                elif case=="visible":p.tiles[16]["visible"]=True
                elif case=="standing-cloud":p.tiles[10]["effects"]=["cloud of toxic gas"]
                elif case=="wall":p.tiles[11]["terrain"]=4
                elif case=="navigation":p.blocked.add(11)
                elif case=="budget":p.objective_progress["resource-observation:4:0:16"]={"accepted":48}
                budget={"optional_turns":0} if case=="hunger" else None
                with patch("tools.resource_reobservation.forecast",return_value=budget):
                    self.assertIsNone(choose(p,s,targets(p),enemies,start=True))
                self.assertTrue(p.tiles[16]["effects"])
                self.assertFalse(p.loot_collection_receipts)

    def test_floor_branch_and_transaction_lifetimes_do_not_retire_facts(self):
        s,p=fixture()
        tx=Transaction(p)
        self.assertIsNotNone(choose(p,s,targets(p),[],start=True))
        tx.rollback()
        self.assertIsNone(p.resource_view_plan)
        self.assertTrue(p.tiles[16]["effects"])
        self.assertIsNotNone(choose(p,s,targets(p),[],start=True))
        s["branch"]=1
        from tools.resource_reobservation import refresh
        refresh(p,s,targets(p))
        self.assertIsNone(p.resource_view_plan)
        self.assertTrue(p.tiles[16]["effects"])
        self.assertFalse(p.loot_collection_receipts)

    def test_only_a_declined_descent_starts_the_information_trip(self):
        from tools.survival_policy import SurvivalPolicy
        from tools.policy_decision import Intent
        s,p=fixture()
        self.assertIsNone(priority(p,s,[]))
        ordinary=p.cell(11,"explore",intent=Intent.EXPLORE)
        with patch.object(SurvivalPolicy,"choose",return_value=ordinary):
            self.assertEqual(ordinary.action,p.choose(s).action)
        self.assertIsNone(p.resource_view_plan)
        descent=p.cell(10,"descend",intent=Intent.DESCEND)
        with patch.object(SurvivalPolicy,"choose",return_value=descent):
            action=p.choose(s)
        self.assertEqual(dict(type="cell",cell=11),action.action)
        self.assertEqual(Intent.REPOSITION,action.intent)
        self.assertIn(16,targets(p))
        self.assertFalse(p.completed_room_rewards)


if __name__=="__main__":
    unittest.main()
