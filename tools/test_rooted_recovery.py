"""Independent public observations, not a continuation of changed run-262 input."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.policy_decision import Finished,Intent
from tools.policy_runtime import Context,Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state,fully_known


def fixture():
    s=fully_known(state())
    s["depth"]=7
    s["evaluation_stats"]={"elapsed_turns":100.0}
    s["hero"]["buffs"]=[{"name":"rooted","description":"Turns of root remaining: 1."}]
    for t in s["map"]["cells"]:t.update(observed=True,effects=[])
    s["objects"]=[{"cell":25,"name":"iron key","top_item":{"name":"iron key","quantity":1}}]
    return s,verified()


def advanced(s,*,rooted=True,turns=1):
    after=copy.deepcopy(s)
    after["observation_id"]+=1
    after["evaluation_stats"]["elapsed_turns"]+=turns
    if not rooted:after["hero"]["buffs"]=[]
    return after


class RootedRecoveryTests(unittest.TestCase):
    def test_rooted_movement_does_not_poison_navigation_or_erase_real_failures(self):
        s,p=fixture()
        p.update(s)
        p.blocked.add(18)
        p.failed_moves[18]=2
        for _ in range(3):
            p.last_decision=p.cell(25,"test",intent=Intent.LOOT)
            p.update(advanced(s,turns=0))
        self.assertEqual(0,p.failed_moves[25])
        self.assertNotIn(25,p.blocked)
        self.assertIn(18,p.blocked)
        self.assertEqual(2,p.failed_moves[18])
        self.assertIn(25,p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_unrooted_failure_and_underfoot_pickup_keep_existing_semantics(self):
        for rooted,cell in ((False,25),(True,24)):
            with self.subTest(rooted=rooted,cell=cell):
                s,p=fixture()
                if not rooted:s["hero"]["buffs"]=[]
                p.update(s)
                for _ in range(2):
                    p.last_decision=p.cell(cell,"test",intent=Intent.LOOT)
                    p.update(copy.deepcopy(s))
                self.assertEqual(2,p.failed_moves[cell])
                self.assertIn(cell,p.blocked)

    def test_engine_selects_time_advancing_wait_without_settling_key(self):
        s,p=fixture()
        action=p.choose(s)
        self.assertEqual({"type":"wait"},action.action)
        self.assertEqual("rooted-recovery",action.controller)
        self.assertEqual(Intent.RECOVER,action.intent)
        self.assertIn(25,p.loot)
        self.assertFalse(p.blocked)
        self.assertFalse(p.loot_collection_receipts)
        self.assertEqual(0,p.root_recovery_plan.accepted)

    def test_runner_renewal_fresh_clearance_then_real_key_pickup(self):
        from tools.policy_runner import run
        s,p=fixture()
        class API:
            observation=s
            actions=[]
            def state(self):return self.observation
            def step(self,action):
                self.actions.append(action)
                after=advanced(self.observation,rooted=len(self.actions)<2)
                if len(self.actions)==3:
                    self_outer.assertEqual({"type":"cell","cell":25},action)
                    after["hero"]["cell"]=25
                    after["objects"]=[]
                    after["keys"]=[{"name":"iron key","depth":7,"quantity":1}]
                else:self_outer.assertEqual({"type":"wait"},action)
                self.observation=after
                return after
        self_outer=self
        api=API()
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/"decisions.jsonl"
            result=run(api,p,3,0,log,bounded=True)
            rows=[json.loads(line) for line in log.read_text().splitlines()]
        receipts=[r["observed_root_recovery"] for r in rows if "observed_root_recovery" in r]
        self.assertEqual([False,True],[r["root_absence_observed"] for r in receipts])
        self.assertEqual([1,2],[r["accepted_inputs"] for r in receipts])
        self.assertTrue(all(not r["collection_credited"] for r in receipts))
        self.assertIsNone(p.root_recovery_plan)
        self.assertTrue(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)
        self.assertNotIn(result["outcome"],{"dead","won","victory"})

    def test_accepted_stagnant_clock_stops_without_another_wait(self):
        from tools.rooted_recovery import observe
        s,p=fixture()
        action=p.choose(s)
        after=advanced(s,turns=0)
        observe(p,s,action,after)
        self.assertEqual(1,p.root_recovery_plan.accepted)
        self.assertTrue(p.root_recovery_plan.stagnant)
        with self.assertRaises(Finished):p.choose(after)

    def test_runner_rejection_does_not_charge_or_rearm_the_episode(self):
        from tools.player_api import PlayerAPIError
        from tools.policy_runner import run
        s,p=fixture()
        class API:
            observation=s
            calls=0
            def state(self):return self.observation
            def step(self,action):
                self.calls+=1
                if self.calls==1:
                    raise PlayerAPIError(400,"A menu requires input; use its buttons or back")
                after=advanced(self.observation,rooted=self.calls<3)
                self.observation=after
                return after
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/"decisions.jsonl"
            result=run(API(),p,3,0,log,bounded=True)
            rows=[json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(3,result["attempts"])
        self.assertEqual(2,result["actions"])
        self.assertEqual(1,sum("rejected" in r for r in rows))
        self.assertEqual([1,2],[r["observed_root_recovery"]["accepted_inputs"]
                               for r in rows if "observed_root_recovery" in r])
        self.assertIsNone(p.root_recovery_plan)
        self.assertIn(25,p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_replanning_and_changed_position_do_not_reset_an_accepted_budget(self):
        from tools.rooted_recovery import choose,observe
        s,p=fixture()
        action=p.choose(s)
        after=advanced(s)
        observe(p,s,action,after)
        p.update(after)
        for _ in range(3):
            self.assertIsNotNone(choose(Context(p,after)))
        self.assertEqual(1,p.root_recovery_plan.accepted)
        displaced=advanced(after)
        displaced["hero"]["cell"]=23
        p.update(displaced)
        self.assertIsNotNone(choose(Context(p,displaced)))
        self.assertEqual(100,p.root_recovery_plan.start)
        self.assertEqual(1,p.root_recovery_plan.accepted)
        wrong_scope=copy.deepcopy(displaced)
        wrong_scope["branch"]=1
        self.assertIsNone(choose(Context(p,wrong_scope)))
        self.assertEqual(1,p.root_recovery_plan.accepted)
        clear=advanced(displaced,rooted=False)
        p.update(clear)
        self.assertIsNone(choose(Context(p,clear)))
        self.assertIsNone(p.root_recovery_plan)

    def test_renewal_and_interruptions_never_reset_budget(self):
        from tools.rooted_recovery import choose,observe,MAX_INPUTS
        s,p=fixture()
        p.update(s)
        for _ in range(MAX_INPUTS):
            action=choose(Context(p,s))
            self.assertEqual({"type":"wait"},action.action)
            after=advanced(s)
            observe(p,s,action,after)
            s=after
            p.update(s)
            spent=p.root_recovery_plan.accepted
            p.recent_threats[26]={"name":"rat","cell":26}
            self.assertIsNone(choose(Context(p,s)))
            self.assertEqual(spent,p.root_recovery_plan.accepted)
            p.recent_threats.clear()
        with self.assertRaises(Finished):choose(Context(p,s))
        self.assertIn(25,p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_rejected_selection_rolls_back_and_unowned_wait_does_not_charge(self):
        from tools.rooted_recovery import observe
        s,p=fixture()
        p.update(s)
        tx=Transaction(p)
        self.assertEqual({"type":"wait"},p.choose(s).action)
        tx.rollback()
        self.assertIsNone(p.root_recovery_plan)
        action=p.choose(s)
        other=p.decision({"type":"wait"},"some other controller",intent=Intent.RECOVER)
        observe(p,s,other,advanced(s))
        self.assertEqual(0,p.root_recovery_plan.accepted)
        observe(p,s,action,advanced(s))
        self.assertEqual(1,p.root_recovery_plan.accepted)

    def test_safety_clock_duration_and_fuel_refusals(self):
        from tools.rooted_recovery import choose
        for case in ("enemy","recent","damage","danger","hurt","poison","starving",
                     "unknown-root","long-root","no-clock","nan","unseen","unobserved",
                     "fire","near-fire","plant","trap","room","actor","hunger","modal"):
            with self.subTest(case=case):
                s,p=fixture()
                if case=="danger":s["danger_cells"]=[24]
                elif case=="hurt":s["hero"]["hp"]-=1
                elif case in {"poison","starving"}:s["hero"]["buffs"].append({"name":case})
                elif case=="unknown-root":s["hero"]["buffs"][0]["description"]=""
                elif case=="long-root":s["hero"]["buffs"][0]["description"]="Turns of root remaining: 5."
                elif case=="no-clock":s["evaluation_stats"]={}
                elif case=="nan":s["evaluation_stats"]["elapsed_turns"]=float("nan")
                elif case=="modal":s["modal"]=True
                tile=next(t for t in s["map"]["cells"] if t["cell"]==25)
                if case=="unseen":tile["visible"]=False
                elif case=="unobserved":tile["observed"]=False
                elif case=="fire":tile["effects"]=["A fire is raging here."]
                elif case=="near-fire":
                    next(t for t in s["map"]["cells"] if t["cell"]==27)["effects"]=["fire"]
                elif case=="plant":tile["plant"]="earthroot"
                elif case=="trap":tile["trap"]="burning trap"
                p.update(s)
                if case=="recent":p.recent_threats[26]={"cell":26,"name":"rat"}
                elif case=="damage":p.unseen_damage_turns=1
                elif case=="room":p.room_blocked.add(24)
                elif case=="actor":p.room_actors[26]={"name":"red sentry","cell":26}
                elif case=="hunger":p.hunger_projection["remaining"]=1
                enemies=[{"name":"rat","cell":26}] if case=="enemy" else []
                self.assertIsNone(choose(Context(p,s,enemies=enemies)))
                self.assertIsNone(p.root_recovery_plan)

    def test_new_fire_pauses_owned_recovery_without_clearance_or_credit(self):
        from tools.rooted_recovery import choose,observe
        s,p=fixture()
        action=p.choose(s)
        after=advanced(s)
        next(t for t in after["map"]["cells"] if t["cell"]==25)["effects"]=["fire"]
        observe(p,s,action,after)
        p.update(after)
        self.assertIsNone(choose(Context(p,after)))
        self.assertEqual(1,p.root_recovery_plan.accepted)
        self.assertTrue(p.tiles[25]["effects"])
        self.assertIn(25,p.loot)
        self.assertFalse(p.loot_collection_receipts)


if __name__=="__main__":
    unittest.main()
