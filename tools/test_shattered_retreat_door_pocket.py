"""Run 82 D2442: door 1383 leads to one floor tile and an active shock trap.

Reduced public geometry. Later sequence observations are synthetic, not replay.
"""
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance


def fixture():
    s=state()
    s["depth"]=6
    s["hero"].update(cell=1462,hp=9,max_hp=55,strength=12,buffs=[])
    groups={
        0:[1306,1307,1344,1420,1422,1423,1424,1458,1496,1501,1534,1539,
           1572,1610,1611,1612,1613,1614],
        4:[1308,1310,1311,1312,1350,1382,1384,1385,1386,1388,1426,1464,
           1502,1540,1578,1616,1648,1649,1650,1651,1652,1654,1686,1687,
           1688,1689,1690,1724,1725,1726,1727,1728,1762,1763,1764,1765,1766],
        20:[1309,1348],1:[1345,1347,1349],18:[1346],5:[1383,1387,1653],
        14:[1421,1425,1459,1460,1461,1462,1463,1497,1498,1499,1500,
            1535,1536,1537,1538,1573,1574,1575,1576,1577,1615],
        29:[1691,1692,1729,1730,1767,1768],
    }
    s["map"]=dict(width=38,height=62,cells=[
        dict(cell=c,terrain=t,observed=True,visible=True,effects=[],
             **({"trap":"shocking trap"} if c==1346 else {}))
        for t,cells in groups.items() for c in cells])
    s["objects"]=[dict(cell=1425,name="skeleton",health_bar=[9,16])]
    s["inventory"]=[dict(id="staff",name="staff of magic missile +2",equipped=True,
        identified=True,status="0/6",actions=["IMBUE","UNEQUIP"],
        description="This melee weapon deals 3-10 damage and requires 9 strength.")]
    p=verified()
    p.update(s)
    return s,p


class RetreatDoorPocketTests(unittest.TestCase):
    def test_full_selector_chooses_open_room_instead_of_trap_pocket(self):
        s,p=fixture()
        d=p.choose(s)
        self.assertEqual({"type":"cell","cell":1499},d.action)
        self.assertEqual("retreat",d.intent)

    def test_retreat_can_continue_after_rejecting_false_door_bonus(self):
        s,p=fixture()
        # Unit-speed pursuit is synthetic; no health/survival outcome is claimed.
        for _ in range(4):
            old=s["hero"]["cell"]
            d=p.retreat(s,s["objects"])
            self.assertIsNotNone(d)
            self.assertNotIn(d.action["cell"],{1383,1345,1346,1421})
            self.assertGreater(distance(d.action["cell"],s["objects"][0]["cell"],38),1)
            s["hero"]["cell"]=d.action["cell"]
            s["objects"][0]["cell"]=old
            p.update(s)

    def test_unknown_beyond_door_cannot_earn_escape_preference(self):
        s,p=fixture()
        del p.tiles[1345]
        self.assertNotIn(1461,p.retreat_preferences(s,s["objects"],[1461]))

    def test_real_onward_space_can_still_earn_door_preference(self):
        s,p=fixture()
        # A separate counterfactual: replace the shock plate by observed floor.
        p.tiles[1346].update(terrain=1,trap=None)
        self.assertGreater(p.retreat_preferences(s,s["objects"],[1461]).get(1461,0),0)

    def test_telegraph_evasion_still_has_its_emergency_admission(self):
        s,p=fixture()
        action=p.retreat(s,s["objects"],danger={1462})
        self.assertIsNotNone(action)
        self.assertNotEqual(1462,action.action["cell"])


if __name__=="__main__":
    unittest.main()
