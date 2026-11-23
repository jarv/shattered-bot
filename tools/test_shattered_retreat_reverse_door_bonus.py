"""Run 187 D1544 reduced public geometry, not original runtime memory.

D1543's accepted 398 -> 429 establishes the reduced escape edge. No
observations after an alternative selection are supplied to the policy.
"""
import unittest

from tools.escape_commitment import reverses
from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.policy_geometry import distance
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=429, hp=13, max_hp=40)
    s["inventory"][0]["status"] = "0/7"
    terrain = {
        274: 1, 304: 20, 305: 29, 306: 29, 307: 29, 308: 29,
        338: 29, 368: 29, 398: 5, 427: 1, 428: 1, 429: 1,
        456: 2, 457: 1, 458: 29, 459: 1, 486: 1, 487: 29,
        488: 29, 489: 1, 516: 1, 517: 29, 518: 1, 519: 1}
    s["map"] = dict(width=30, height=40, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c >= 398, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="sewer crab", cell=486,
                         health_bar=[12, 21], status_icons=["vertigo"])]
    p = MagePolicy()
    p.update(s)
    # Reduced reconstruction from D1543's accepted movement, not a saved plan.
    p.escape_commitment = dict(edges=[(398, 429)], hp=13, charges=0, age=0)
    p.loot[547] = dict(name="iron key", cell=547)
    return s, p


class RetreatReverseDoorBonusTests(unittest.TestCase):
    def test_reverse_door_has_no_bonus_over_equally_separated_onward_ground(self):
        s, p = fixture()
        self.assertTrue(reverses(p, s, 398))
        self.assertEqual(distance(398, 486, 30), distance(459, 486, 30))
        decision = p.retreat(s, s["objects"])
        self.assertEqual(459, decision.action["cell"],
                         "Do not reward returning through the just-left escape door")
        self.assertEqual(Intent.RETREAT, decision.intent)
        self.assertEqual([(398, 429)], p.escape_commitment["edges"])
        self.assertEqual("iron key", p.loot[547]["name"])

    def test_ordinary_door_bonus_without_reverse_edge_is_preserved(self):
        s, p = fixture()
        p.escape_commitment = None
        self.assertEqual(398, p.retreat(s, s["objects"]).action["cell"])

    def test_no_unsafe_onward_square_is_invented(self):
        for hazard in ("trap", "fire", "unknown"):
            with self.subTest(hazard=hazard):
                s, p = fixture()
                if hazard == "trap":
                    p.tiles[459].update(terrain=18, trap="poison dart trap")
                elif hazard == "fire":
                    p.tiles[459]["effects"] = ["A fire is raging here."]
                else:
                    p.tiles.pop(459)
                self.assertFalse(p.walkable(459))
                decision = p.retreat(s, s["objects"])
                self.assertTrue(decision is None or decision.action["cell"] != 459)


if __name__ == "__main__":
    unittest.main()
