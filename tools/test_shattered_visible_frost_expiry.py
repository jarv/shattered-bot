"""Reduced public geometry at recording 000120 decision 2704, not a replay."""
import unittest

from tools.test_challenge_rules import verified
from tools.policy_geometry import distance
from tools.policy_decision import Finished
from tools.resource_tactics import recheck_hazards


COLD = "The air is unnaturally frigid here."


def fixture():
    terrain = {
        1306: 1, 1307: 4, 1308: 2, 1309: 2, 1310: 2, 1311: 2,
        1312: 2, 1313: 4, 1314: 2, 1315: 4, 1346: 29, 1347: 5,
        1348: 1, 1349: 2, 1350: 0, 1351: 2, 1352: 2, 1353: 4,
        1354: 1, 1355: 4, 1386: 4, 1387: 4, 1388: 1, 1389: 1,
        1390: 0, 1391: 0, 1392: 2, 1393: 6, 1394: 20, 1395: 4,
        1427: 4, 1428: 1, 1429: 0, 1430: 1, 1431: 0, 1432: 1,
        1433: 4, 1434: 4, 1435: 4,
    }
    s = dict(scene="GameScene", status="ready", modal=False, depth=6, branch=0,
             hero=dict(name="mage", hero_class="mage", cell=1393, hp=55,
                       max_hp=55, strength=13, buffs=[dict(name="barrier")]),
             inventory=[dict(id="item-0", name="staff of magic missile +3",
                             equipped=True, identified=True, curse_known=True,
                             known_cursed=False, status="0/7",
                             actions=["DROP", "THROW", "UNEQUIP", "IMBUE"],
                             description="This tier-1 melee weapon deals 4-12 damage and requires 8 strength.")],
             objects=[], danger_cells=[], keys=[],
             ui=dict(texts=[], buttons=[]),
             map=dict(width=40, height=40, cells=[
                 dict(cell=c, terrain=t, visible=True, observed=True, mapped=True,
                      effects=[COLD] if c in {1308, 1347, 1348, 1388} else [])
                 for c, t in terrain.items()]))
    p = verified()
    p.update(s)
    # Explicit reduced-fixture bookkeeping, not originally recorded memory.
    # Accepted mapping is public at decisions 2050 and 2069.
    p.mapped_floors.add((6, 0))
    p.shop_visited_floors.add(6)
    p.exhausted.update(p.tiles)
    p.visits.update({c: 1 for c in p.tiles})
    return s, p


class VisibleFrostExpiryTests(unittest.TestCase):
    def test_full_selector_retains_expiry_observation(self):
        s, p = fixture()
        try:
            d = p.choose(s)
        except Finished as error:
            self.fail("No safe frost observation reached: " + error.reason)
        self.assertEqual({"type": "wait"}, d.action)
        self.assertIn("freezing", d.reason)

    def test_exhausted_explorer_observes_finite_cold_without_entering_it(self):
        s, p = fixture()
        try:
            d = p.explore(s, [])
        except Finished as error:
            self.fail("Visible finite frost must retain safe observation: " + error.reason)
        self.assertEqual({"type": "wait"}, d.action)
        self.assertIn("freezing", d.reason)
        self.assertEqual(1, p.hazard_recheck_waits)
        self.assertTrue(p.effects_block_movement(p.tiles[1348]))
        self.assertNotIn(1348, p.paths(s))
        self.assertFalse(p.cleared_floors)
        self.assertFalse(p.searched_walls)

    def test_observation_never_credits_clearance_and_retains_existing_bound(self):
        s, p = fixture()
        for _ in range(16):
            d = recheck_hazards(p, s, p.paths(s), distance)
            self.assertIsNotNone(d)
            self.assertEqual({"type": "wait"}, d.action)
            self.assertEqual([COLD], p.tiles[1348]["effects"])
        self.assertIsNone(recheck_hazards(p, s, p.paths(s), distance))
        with self.assertRaises(Finished):
            p.explore(s, [])

    def test_refuse_unsafe_or_unobserved_holds(self):
        for case in ("enemy", "memory", "danger", "bank_effect", "bank_trap",
                     "bank_plant", "unseen_bank", "unseen_neighbor",
                     "mixed", "starving", "health", "modal", "targeting", "spent"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "enemy":
                    s["objects"] = [dict(name="skeleton", cell=1349)]
                elif case == "memory":
                    p.recent_threats[1349] = dict(name="skeleton", cell=1349)
                elif case == "danger":
                    s["danger_cells"] = [1393]
                elif case.startswith("bank_"):
                    key = "effects" if case == "bank_effect" else case[5:]
                    p.tiles[1393][key] = [COLD] if key == "effects" else "icecap"
                elif case == "unseen_bank":
                    p.tiles[1393]["visible"] = False
                elif case == "unseen_neighbor":
                    p.tiles[1352]["visible"] = False
                elif case == "mixed":
                    for c in (1308, 1347, 1348, 1388):
                        p.tiles[c]["effects"].append("Unknown magical effect.")
                elif case == "starving":
                    s["hero"]["buffs"] = [dict(name="starving")]
                elif case == "health":
                    s["hero"]["hp"] = 10
                elif case == "modal":
                    s["modal"] = True
                elif case == "targeting":
                    s["status"] = "targeting"
                else:
                    p.hazard_recheck_waits = 16
                self.assertIsNone(recheck_hazards(p, s, p.paths(s), distance))

    def test_fresh_clearance_is_required_and_is_not_manufactured(self):
        s, p = fixture()
        for t in s["map"]["cells"]:
            t["effects"] = []
        p.update(s)
        self.assertIsNone(recheck_hazards(p, s, p.paths(s), distance))
        self.assertIn(1348, p.paths(s))


if __name__ == "__main__":
    unittest.main()
