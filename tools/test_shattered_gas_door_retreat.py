"""Reduced public run 000182 D1024 geometry, not a gameplay replay.

Gas behind door 903 was public at D880 and D1023. The door closes and
its own effects become empty at D1024; the far-side gas is then unseen.
Plan fields below are explicit fixture bookkeeping from the selection report,
not a claim to have recovered the original runtime memory.
"""
import copy
import unittest

from tools import multi_enemy_tactics as multi
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


GAS = "A greenish cloud of toxic gas is swirling here."


def fixture(committed=True):
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=861, hp=26, max_hp=35, strength=11, level=4,
                     buffs=[{"name": "hungry"}])
    terrain = {817:29, 818:29, 819:29, 820:29, 821:29, 822:1,
               859:4, 860:4, 861:29, 862:29, 863:29, 864:29,
               902:4, 903:5, 904:4, 905:4, 943:29, 944:1, 945:1}
    s["map"] = dict(width=42, height=33, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c<943, effects=[])
        for c,t in terrain.items()])
    s["objects"] = [dict(name="gnoll scout", cell=c, status_icons=[])
                    for c in (820,862)]
    p = verified()
    # Feed the earlier public gas observation, then the closed-door view.
    earlier = copy.deepcopy(s)
    for t in earlier["map"]["cells"]:
        if t["cell"] >= 943:
            t.update(visible=True, effects=[GAS])
    p.update(earlier)
    for t in s["map"]["cells"]:
        if not t["visible"]:
            t.pop("effects")
    p.update(s)
    if committed:
        p.multi_door_plan = dict(depth=3, branch=0, door=903, steps=3,
                                 start_hp=26)
    return p,s


class GasDoorRetreatTests(unittest.TestCase):
    def test_reclosed_gas_entrance_is_not_a_new_or_committed_refuge(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                p,s = fixture(committed)
                before = copy.deepcopy(s)
                self.assertTrue(p.tiles[944]["effects"])
                self.assertFalse(p.tiles[944]["visible"])
                self.assertFalse(p.tiles[903]["effects"])
                d = multi.doorway_route(p,s,s["objects"],2)
                self.assertIsNone(d, "A clear closed threshold does not clear the gas beyond it")
                self.assertIsNone(p.multi_door_plan)
                self.assertEqual(before,s)
                self.assertFalse(p.cleared_floors)
                self.assertFalse(p.loot_collection_receipts)

    def test_fresh_observed_clearance_readmits_the_ordinary_door(self):
        p,s = fixture()
        clear = copy.deepcopy(s)
        for t in clear["map"]["cells"]:
            t.update(visible=True, effects=[])
        p.update(clear)
        d = multi.doorway_route(p,clear,clear["objects"],2)
        self.assertIsNotNone(d)
        self.assertEqual(dict(type="cell",cell=903),d.action)

    def test_full_selector_uses_existing_combat_not_the_gas_door(self):
        p,s = fixture()
        d = p.choose(s)
        self.assertNotEqual(dict(type="cell",cell=903),d.action)
        self.assertNotEqual("wait",d.action["type"])
        self.assertEqual(dict(type="item",id="item-0",action="ZAP"),d.action)


if __name__ == "__main__":
    unittest.main()
