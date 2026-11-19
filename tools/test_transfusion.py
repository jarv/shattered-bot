import unittest

from tools.test_challenge_systems import ready, item
from tools.policy_geometry import distance
from tools.wand_tactics import choose_transfusion


class TransfusionTests(unittest.TestCase):
    def fixture(self):
        s,p=ready()
        s["hero"]["hp"]=10
        s["inventory"][0]["status"]="0/4"
        s["inventory"].append(dict(item("wand of transfusion","ZAP"),curse_known=True,status="2/3"))
        enemy={"name":"swarm of flies","cell":25,"description":"_Projecting Champion_"}
        return s,p,enemy

    def test_transfusion_inspects_before_cast_and_never_retargets_same_charm_name(self):
        s,p,enemy=self.fixture()
        self.assertEqual("inspect",choose_transfusion(p,s,[enemy],distance).action["type"])
        p.inspection_cache=dict(enemy,buffs=set())
        self.assertEqual("ZAP",choose_transfusion(p,s,[enemy],distance).action.get("action"))
        self.assertIn("swarm of flies",p.transfusion_names)
        self.assertIsNone(choose_transfusion(p,s,[dict(enemy,cell=26)],distance))

    def test_charmed_target_unknown_curse_and_magic_immunity_are_not_exploited(self):
        for mode in ("charmed","curse","immune"):
            s,p,enemy=self.fixture()
            p.inspection_cache=dict(enemy,buffs={"charmed"} if mode=="charmed" else set())
            if mode=="curse":s["inventory"][-1]["curse_known"]=False
            if mode=="immune":s["hero"]["buffs"]=[{"name":"magic immune"}]
            self.assertIsNone(choose_transfusion(p,s,[enemy],distance),mode)
