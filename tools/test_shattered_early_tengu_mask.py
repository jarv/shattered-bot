"""Run-246-derived progression priority, not a replay or survival claim."""
import copy
import unittest
from unittest.mock import patch

from tools.mage_tactics import prepare_mask,mage_menu
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture(depth=10,engine="legacy"):
    s=state()
    s.update(depth=depth,branch=0)
    s["hero"].update(hp=7,max_hp=20,buffs=[dict(name="hungry")])
    for tile in s["map"]["cells"]:
        tile.update(visible=True,observed=True)
    s["inventory"].append(dict(id="mask",name="Tengu's mask",actions=["WEAR","DROP"]))
    p=verified()
    p.engine=engine
    p.update(s)
    return s,p


class EarlyTenguMaskTests(unittest.TestCase):
    def test_wounded_hungry_mask_precedes_descent_and_optional_search(self):
        for depth in (10,11):
            for engine in ("legacy","planner"):
                with self.subTest(depth=depth,engine=engine):
                    s,p=fixture(depth,engine)
                    before=copy.deepcopy(s)
                    with patch("tools.mage_policy.selective_descent",
                               side_effect=AssertionError("Optional descent ran before owned progression")):
                        action=p.choose(s)
                    self.assertEqual(dict(type="item",id="mask",action="WEAR"),action.action)
                    self.assertEqual("warlock",p.mage_plan["choice"])
                    self.assertEqual(before,s)

    def test_starving_without_food_is_not_optional_crafting(self):
        s,p=fixture()
        s["hero"]["buffs"]=[dict(name="starving")]
        s["inventory"]=[i for i in s["inventory"] if "EAT" not in i.get("actions",[])]
        action=p.choose(s)
        self.assertEqual(dict(type="item",id="mask",action="WEAR"),action.action)

    def test_critical_healing_and_carried_starvation_food_keep_priority(self):
        s,p=fixture()
        s["hero"]["hp"]=4
        s["inventory"].append(dict(id="heal",name="potion of healing",identified=True,
                                    actions=["DRINK"]))
        self.assertIsNone(prepare_mask(p,s,[]))
        self.assertEqual(dict(type="item",id="heal",action="DRINK"),p.choose(s).action)
        s,p=fixture()
        s["hero"]["buffs"]=[dict(name="starving")]
        s["inventory"].append(dict(id="food",name="ration of food",quantity=1,actions=["EAT"]))
        self.assertEqual(dict(type="item",id="food",action="EAT"),p.choose(s).action)

    def test_safety_and_active_return_obligations_are_not_bypassed(self):
        for case in ("enemy","sleeper","recent","damage","warning","boss","burning",
                     "poison","starving-critical","blind","invisible","effect","trap",
                     "plant","unseen","unobserved","room","modal","targeting"):
            with self.subTest(case=case):
                s,p=fixture()
                pos=s["hero"]["cell"]
                if case in {"enemy","sleeper"}:
                    s["objects"]=[dict(cell=pos+1,name="gnoll scout",sleeping=case=="sleeper")]
                elif case=="recent":p.recent_threats[pos+1]=dict(cell=pos+1,name="gnoll scout")
                elif case=="damage":p.unseen_damage_turns=1
                elif case=="warning":s["danger_cells"]=[pos+1]
                elif case=="boss":s["boss_health_text"]="Tengu"
                elif case in {"burning","poison","blind","invisible"}:
                    s["hero"]["buffs"].append(dict(name=case))
                elif case=="starving-critical":
                    s["hero"].update(hp=2,buffs=[dict(name="starving")])
                elif case=="effect":p.tiles[pos]["effects"]=["toxic gas"]
                elif case=="trap":p.tiles[pos]["trap"]="summoning trap"
                elif case=="plant":p.tiles[pos]["plant"]="firebloom"
                elif case=="unseen":p.tiles[pos]["visible"]=False
                elif case=="unobserved":p.tiles[pos]["observed"]=False
                elif case=="room":p.room_blocked.add(pos)
                elif case=="modal":s["modal"]=True
                elif case=="targeting":s["status"]="targeting"
                self.assertIsNone(prepare_mask(p,s,[]))
                self.assertIsNone(p.mage_plan)
        for owner in ("room_journey","puzzle_probe","potion_stash","trap_payload_return",
                      "drop_plan","escape_commitment","ranged_plan","ambush_plan",
                      "doorway_hold","well_cleanse_plan","food_freeze_plan"):
            with self.subTest(owner=owner):
                s,p=fixture()
                setattr(p,owner,object())
                self.assertIsNone(prepare_mask(p,s,[]))
                self.assertIsNone(p.mage_plan)

    def test_rejection_rolls_back_choice_and_retry_keeps_same_subclass(self):
        s,p=fixture()
        tx=Transaction(p)
        self.assertEqual("WEAR",p.choose(s).action["action"])
        tx.rollback()
        self.assertIsNone(p.mage_plan)
        self.assertEqual("WEAR",p.choose(s).action["action"])
        self.assertEqual("warlock",p.mage_plan["choice"])
        self.assertFalse(p.completed_room_rewards)

    def test_rendered_warlock_selection_confirmation_and_no_duplicate_use(self):
        s,p=fixture()
        self.assertIsNotNone(prepare_mask(p,s,[]))
        s["ui"]=dict(texts=["Tengu's mask"],buttons=[
            dict(id="random",label="Random Subclass"),
            dict(id="battle",label="The _Battlemage_"),
            dict(id="war",label="The _Warlock_ heals through marked souls.")])
        self.assertEqual("war",mage_menu(p,s).action["id"])
        s["ui"]=dict(texts=["Warlock","Are you sure?"],buttons=[
            dict(id="yes",label="Yes, I've made my choice.")])
        self.assertEqual("yes",mage_menu(p,s).action["id"])
        s["hero"]["subclass"]="warlock"  # Explicit synthetic accepted result.
        self.assertIsNone(prepare_mask(p,s,[]))
        self.assertIsNone(p.mage_plan)


if __name__=="__main__":
    unittest.main()
