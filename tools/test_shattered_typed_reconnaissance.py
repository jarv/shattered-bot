import copy
from pathlib import Path
import tempfile
import unittest

from tools.test_shattered_strength_before_descent import ready
from tools.preparation_prerequisites import sentry_reobservation, observe_reconnaissance
from tools.policy_decision import BlockerKind, PlannerStuck, Finished
from tools.floor_abandonment import FloorAbandonment
from tools.test_shattered_floor_abandonment import fixture
from tools.policy_runner import run


def sentry():
    s,p=ready()
    s["hero"]["cell"]=56
    for tile in s["map"]["cells"]:
        tile["terrain"]=4
    for c,t in {56:1,57:5,58:1,59:1,60:11,61:14}.items():
        s["map"]["cells"][c]["terrain"]=t
    s["map"]["cells"]=[t for t in s["map"]["cells"] if t["cell"]!=49]
    p.tiles.clear()
    s["objects"]=[dict(cell=60,name="red sentry")]
    p.update(s)
    return s,p


class TypedReconnaissanceTests(unittest.TestCase):
    def test_ordinary_reobservation_owns_target_and_counts_only_accepted_actions(self):
        s,p=sentry()
        original=copy.deepcopy(s)
        action=sentry_reobservation(p,s)
        self.assertIsNotNone(action)
        target=p.preparation_scout["target"]
        self.assertEqual(59,target)
        self.assertEqual(57,action.action["cell"])
        self.assertEqual(0,p.preparation_scout["accepted"])
        self.assertEqual(original,s)
        # Opening the door is accepted time, not a fabricated arrival.
        after=copy.deepcopy(s)
        next(t for t in after["map"]["cells"] if t["cell"]==57)["terrain"]=6
        observe_reconnaissance(p,s,action,after)
        self.assertEqual(1,p.preparation_scout["accepted"])
        self.assertEqual([],p.preparation_scout["visited"])
        s=after;p.update(s)
        for _ in range(5):
            action=sentry_reobservation(p,s)
            self.assertNotEqual(61,action.action["cell"])
            self.assertEqual(target,p.preparation_scout["target"])
            after=copy.deepcopy(s);after["hero"]["cell"]=action.action["cell"]
            observe_reconnaissance(p,s,action,after)
            s=after;p.update(s)
            if s["hero"]["cell"]==target:break
        self.assertIn(target,p.preparation_scout["visited"])
        self.assertIsNone(p.preparation_scout["target"])
        self.assertNotIn(49,p.tiles) # Observation travel does not invent a wall.
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.room_journey)

    def test_scout_keeps_hazards_ownership_and_budget_gates(self):
        for bad in ("trap","effect","unknown","danger","enemy","stash","health","budget"):
            s,p=sentry()
            if bad=="trap":p.tiles[57]["trap"]="dart"
            elif bad=="effect":p.tiles[57]["effects"]=["toxic gas"]
            elif bad=="unknown":p.tiles[57]["observed"]=False
            elif bad=="danger":s["danger_cells"]=[57]
            elif bad=="enemy":s["objects"].append(dict(cell=57,name="marsupial rat"))
            elif bad=="stash":p.potion_stash={"phase":"retrieve"}
            elif bad=="health":s["hero"]["hp"]=5
            else:
                sentry_reobservation(p,s);p.preparation_scout["accepted"]=48
            self.assertIsNone(sentry_reobservation(p,s),bad)

    def test_fallback_uses_category_not_error_wording(self):
        s,p,recovery=fixture()
        self.assertIsNotNone(recovery.start(s,PlannerStuck("New wording with no magic phrases",
                             kind=BlockerKind.OPTIONAL),{},4))
        s,p,recovery=fixture()
        self.assertIsNone(recovery.start(s,PlannerStuck("Piranha-room chest remains uncollected",
                          kind=BlockerKind.SAFETY),{},4))
        self.assertEqual(BlockerKind.SAFETY,recovery.incidents[0]["blocker_kind"])

    def test_raw_safety_stop_is_logged_but_does_not_attempt_descent(self):
        s,p,_=fixture()
        class SafetyStop(type(p)):
            def choose(self,state):
                raise Finished("blocked","Toxic gas has no admitted escape",kind=BlockerKind.SAFETY)
        class API:
            observation=s
            def state(self):return self.observation
            def step(self,action):raise AssertionError("safety stop must not dispatch an input")
        with tempfile.TemporaryDirectory() as root:
            result=run(API(),SafetyStop(),5,0,Path(root)/"decisions.jsonl")
        self.assertEqual("blocked",result["outcome"])
        self.assertEqual(1,result["planner_incident_count"])
        self.assertEqual(BlockerKind.SAFETY,result["planner_incidents"][0]["blocker_kind"])
        self.assertEqual("declined",result["planner_incidents"][0]["status"])

    def test_execution_stop_without_hero_is_reportable(self):
        _,p,recovery=fixture()
        self.assertIsNone(recovery.start({"status":"loading"},Finished("blocked","Unknown UI"),{},0))
        self.assertEqual(BlockerKind.EXECUTION,recovery.incidents[0]["blocker_kind"])


if __name__=="__main__":
    unittest.main()
