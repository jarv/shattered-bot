"""Run 181 D2444 public pool geometry, reduced; no gameplay continuation.

Bandolier protection is a separate acquisition-bookkeeping premise, not inferred
from merely seeing a bag. Equipment alternatives are isolated copies.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.piranha_tactics import choose, pending
from tools.policy_geometry import neighbors
from tools.room_tactics import plan_journey


def fixture():
    groups = {
        1: [1745, 1778, 1810], 20: [1811], 6: [1843], 11: [2040],
        4: [1744,1746,1776,1777,1779,1809,1812,1839,1840,1842,
            1844,1845,1846,1879,1912,1945,1978,2011,2044,
            2070,2071,2072,2073,2074,2075,2076,2077],
        12: [1841], 14: list(range(1872,1879)),
        29: [1905,1906,1907,1908,1909,1910,1911,1938,1939,1940,
             1941,1942,1943,1944,1971,1972,1973,1974,1975,1976,
             1977,2004,2005,2006,2007,2008,2009,2010,
             2037,2038,2039,2041,2042,2043],
    }
    unseen = {1744,1839,1840,1841,1845,1846,1872,1873,1879,1905}
    armor = dict(id="leather", name="leather armor of obfuscation",
                 equipped=True, identified=False, curse_known=True,
                 known_cursed=False, actions=["UNEQUIP"],
                 description="Typically this _tier-2_ armor blocks _0-4 damage_ and requires _12 strength_ to use properly.")
    cloth = dict(id="cloth", name="cloth armor", equipped=False,
                 identified=True, curse_known=True, known_cursed=False,
                 actions=["EQUIP"],
                 description="This _tier-1_ armor blocks _0-2 damage_ and requires _10 strength_ to use properly.")
    s = dict(scene="GameScene", status="ready", modal=False, depth=6,
             branch=0, danger_cells=[], ui=dict(texts=[], buttons=[]),
             hero=dict(cell=1843, hp=50, max_hp=50, strength=12, buffs=[]),
             inventory=[armor, cloth,
                        dict(id="bag", name="potion bandolier", identified=True),
                        dict(id="ivory", name="ivory potion", quantity=1,
                             identified=False, actions=["DRINK","DROP","THROW"])],
             objects=[dict(cell=c, name="giant piranha") for c in (1906,1908,1940)]
                     + [dict(cell=2040, name="Chest")],
             map=dict(width=33, height=64, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=c not in unseen)
                 for t, cells in groups.items() for c in cells]))
    p = MagePolicy()
    p.update(s)
    p.bandolier_inventory = (True, False)
    return p, s


class PoolArmorPreparationTests(unittest.TestCase):
    def test_known_cloth_prepares_pool_without_inventing_protection_or_pickup(self):
        p, s = fixture()
        before = copy.deepcopy(s)
        self.assertIsNone(plan_journey(p,s,[],neighbors,probe_kind="pool",plan_only=True))
        alternative = copy.deepcopy(s)
        alternative["inventory"][0]["equipped"] = False
        alternative["inventory"][1]["equipped"] = True
        self.assertIsNotNone(plan_journey(p,alternative,[],neighbors,
                                         probe_kind="pool",plan_only=True))
        d = choose(p,s,[])
        self.assertIsNotNone(d, "Known safe cloth must unblock pool preparation")
        self.assertEqual(dict(type="item",id="cloth",action="EQUIP"),d.action)
        self.assertEqual(before,s)
        self.assertIn(2040,pending(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.room_attempts)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)

    def test_unsafe_unfunded_or_unnecessary_swaps_decline(self):
        for case in ("cursed-worn","unknown-curse","unknown-spare","heavy-spare",
                     "cursed-spare","no-equip","enemy","memory","damage","danger",
                     "wounded","hungry","poison","no-supply","no-trip",
                     "no-bank","unseen-bank","bag-uncertain","already-safe",
                     "deferred","test-limit","already-tested"):
            with self.subTest(case=case):
                p,s = fixture()
                worn,spare=s["inventory"][:2]
                enemies=[]
                if case=="cursed-worn": worn["known_cursed"]=True
                elif case=="unknown-curse": worn["curse_known"]=False
                elif case=="unknown-spare": spare["identified"]=False
                elif case=="heavy-spare": s["hero"]["strength"]=9
                elif case=="cursed-spare": spare["known_cursed"]=True
                elif case=="no-equip": spare["actions"]=[]
                elif case=="enemy": enemies=[dict(name="prison guard",cell=1810)]
                elif case=="memory": p.recent_threats[1810]=dict(name="prison guard",cell=1810)
                elif case=="damage": p.unseen_damage_turns=1
                elif case=="danger": s["danger_cells"]=[1843]
                elif case=="wounded": s["hero"]["hp"]=30
                elif case in ("hungry","poison"): s["hero"]["buffs"]=[dict(name=case)]
                elif case=="no-supply": s["inventory"].pop()
                elif case=="no-trip": p.loot.pop(2040)
                elif case=="no-bank": p.tiles[1810]["trap"]="chilling trap"
                elif case=="unseen-bank": p.tiles[1810]["visible"]=False
                elif case=="bag-uncertain": p.bandolier_inventory=(True,True)
                elif case=="already-safe": worn["identified"]=True
                elif case=="deferred": p.deferred_room_controllers.add("potion-supplies")
                elif case=="test-limit": p.puzzle_drinks.update((6,str(i)) for i in range(12))
                elif case=="already-tested": p.puzzle_drinks.add((6,"ivory potion"))
                d=choose(p,s,enemies)
                self.assertFalse(d and d.action.get("action")=="EQUIP")
                self.assertIn(2040,pending(p))
                self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
