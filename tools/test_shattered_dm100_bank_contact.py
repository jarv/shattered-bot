"""Reduced run 000167 decision 2751 public geometry (selection line 7932).

The plan-shaped input is reconstructed, not recorded runtime memory.
No dispatch or changed-decision continuation is performed.
"""
import unittest

from tools.dm100_escape import choose, sees
from tools.test_challenge_rules import verified


def bank_scene():
    terrain = {
        614:4, 615:1, 616:1, 617:1, 650:4, 651:1, 652:1, 653:4,
        686:4, 687:1, 688:29, 689:4, 722:4, 723:4, 724:6, 725:4,
        759:4, 760:29, 761:4, 795:4, 796:29, 797:4,
    }
    s = dict(scene="GameScene", status="ready", modal=False, depth=7, branch=0,
             danger_cells=[], hero=dict(cell=687, hp=27, max_hp=55, strength=12,
             level=8, buffs=[], talents=[]), inventory=[], objects=[
                 dict(name="prison guard", cell=724, status_icons=[])],
             map=dict(width=36, height=39, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=c not in
                      {759,795,796,797}, effects=[]) for c,t in terrain.items()]),
             ui=dict(texts=[], buttons=[]))
    p = verified()
    p.update(s)
    # Prior public route: 832 -> 796 -> 760 -> 724 -> 687; last
    # observed caster cell 904. Only this helper's relevant fields are supplied.
    p.ranged_plan = dict(name="dm-100", mode="door-flight", stage="bank",
                         door=724, goal=687, approach=760, steps=3, waits=0,
                         depth=7, branch=0, last_seen=904, hp=26, armed=False)
    p.previous_position = 724
    return s,p


class DM100BankContactTests(unittest.TestCase):
    def test_contact_guard_interrupts_caster_wait_before_first_damage(self):
        s,p = bank_scene()
        self.assertFalse(sees(p,s,904,687))
        self.assertIsNone(choose(p,s,s["objects"]),
                          "Caster cover does not authorize waiting beside a guard")
        self.assertIsNone(p.ranged_plan)
        self.assertEqual(0,p.ranged_cover_waits["dm-100"])
        self.assertFalse(p.loot_collection_receipts)

    def test_quiet_or_sleeping_guard_still_allows_bounded_wait(self):
        for sleeping in (False,True):
            with self.subTest(sleeping=sleeping):
                s,p = bank_scene()
                s["objects"] = [dict(name="prison guard",cell=724,sleeping=True)] if sleeping else []
                a = choose(p,s,s["objects"])
                self.assertEqual({"type":"wait"},a.action)
                self.assertEqual(1,p.ranged_cover_waits["dm-100"])

    def test_exposed_caster_or_active_effect_still_vetoes_wait(self):
        for case in ("caster","effect"):
            with self.subTest(case=case):
                s,p = bank_scene()
                s["objects"]=[]
                if case=="caster":p.ranged_plan["last_seen"]=652
                else:p.tiles[687]["effects"]=["toxic gas"]
                a=choose(p,s,s["objects"])
                self.assertTrue(a is None or a.action!={"type":"wait"})


if __name__ == "__main__":
    unittest.main()
