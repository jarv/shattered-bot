"""Run 269: public water alcove and health-funded discovery prerequisite.

This is a reduced deterministic fixture, not recovered controller memory.
"""
import copy
import unittest
from unittest.mock import patch

from tools.challenge_rules import ChallengeRules
from tools.descent_potions import begin
from tools.policy_decision import PlannerStuck
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 2
    s["hero"].update(cell=341, hp=23, max_hp=30, strength=10, buffs=[])
    terrain = {310:4,311:5,312:4,340:12,341:29,342:4,
               369:29,370:29,371:29,372:4,399:29,400:29,401:29,402:4,
               429:0,430:29,431:29,432:4}
    s["map"] = dict(width=30, height=45, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, mapped=True, effects=[])
        for c,t in terrain.items()])
    s["map"]["cells"] += [
        dict(cell=368, terrain=2, visible=False, observed=True, mapped=True),
        dict(cell=397, terrain=14, visible=False, observed=True, mapped=True),
        dict(cell=427, terrain=14, visible=True, observed=True, mapped=True, effects=[])]
    s["objects"] = []
    s["inventory"] = [
        dict(id="dew", name="waterskin", identified=True, status="11/20",
             actions=["DROP","THROW","DRINK"]),
        dict(id="heal", name="potion of healing", identified=True, actions=["DRINK","DROP"]),
        dict(id="gas", name="potion of paralytic gas", identified=True, actions=["DRINK","DROP"]),
        dict(id="ivory", name="ivory potion", identified=False, actions=["DRINK","DROP"]),
        dict(id="invis", name="potion of invisibility", identified=True, actions=["DRINK","DROP"]),
        dict(id="indigo", name="indigo potion", identified=False, actions=["DRINK","DROP"])]
    p = verified()
    p.update(s)
    p.floor_recovery = 24
    return s,p


def proposal(p,s):
    try:
        return begin(p,s)
    except PlannerStuck:
        return None


class DiscoveryDewPreparationTests(unittest.TestCase):
    def test_wounded_discovery_chooses_known_dew_without_claiming_test_or_heal(self):
        s,p = fixture()
        healthy = copy.deepcopy(s)
        healthy["hero"]["hp"] = 30
        self.assertEqual({"type":"cell","cell":371}, begin(copy.deepcopy(p),healthy).action)
        action = proposal(p,s)
        self.assertIsNotNone(action, "admitted discovery must provision its health prerequisite")
        self.assertEqual({"type":"item","id":"dew","action":"DRINK"}, action.action)
        self.assertEqual(23,s["hero"]["hp"])
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)

    def test_safety_and_positive_continuation_are_required(self):
        for kind in ("empty","insufficient","missing-status","poison","hungry","threat",
                     "danger","unseen","no-bank","pharmacophobia","delayed-healing"):
            with self.subTest(kind=kind):
                s,p = fixture()
                if kind=="empty":s["inventory"][0]["status"]="0/20"
                elif kind=="insufficient":s["inventory"][0]["status"]="1/20"
                elif kind=="missing-status":s["inventory"][0].pop("status")
                elif kind in {"poison","hungry"}:s["hero"]["buffs"]=[{"name":kind}]
                elif kind=="threat":p.recent_threats[311]={"cell":311,"name":"snake"}
                elif kind=="danger":s["danger_cells"]=[341]
                elif kind=="unseen":p.unseen_damage_turns=1
                elif kind=="no-bank":
                    for t in p.tiles.values():
                        if t["cell"]!=341:t["effects"]=["toxic gas"]
                elif kind=="pharmacophobia":p.rules=ChallengeRules(pharmacophobia=True)
                elif kind=="delayed-healing":s["inventory"].append(
                    dict(id="vial",name="vial of blood",actions=[]))
                self.assertIsNone(proposal(p,s))

    def test_one_proposal_only_and_transaction_rollback(self):
        s,p = fixture()
        tx = Transaction(p)
        self.assertIsNotNone(proposal(p,s))
        self.assertIsNone(proposal(p,s), "unchanged observations must not repeat dew preparation")
        tx.rollback()
        self.assertIsNotNone(proposal(p,s))

    def test_item_eligibility_remains_binding(self):
        s,p = fixture()
        with patch.object(p,"item_action_allowed",return_value=False):
            self.assertIsNone(proposal(p,s))


if __name__ == "__main__":
    unittest.main()
