"""Reduced public decision-425 room from run 000104; no replay or runtime memory."""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import neighbors
from tools.room_tactics import plan_journey


def fixture():
    # Only cells publicly observed at decision 425, before using levitation.
    groups = {
        4: [639,681,723,765,807,891,927,928,929,930,931,932,933],
        0: [678,679,719,720,721,722,761,763,764,801,803,805,806,
            843,844,845,846,847,848,885,886,887,888,889],
        14: [680,760,762,802,804,890],
        5: [849],
    }
    s = dict(scene="GameScene", status="ready", modal=False, depth=2, branch=0,
             danger_cells=[], ui=dict(texts=[], buttons=[]),
             hero=dict(cell=890, hp=25, max_hp=25, strength=10, buffs=[]),
             inventory=[dict(id="flight", name="potion of levitation",
                             identified=True, quantity=1, actions=["DRINK"])],
             keys=[dict(name="golden key", depth=2, quantity=1)],
             objects=[dict(cell=680, name="golden key",
                           top_item=dict(name="golden key", quantity=1))] +
                     [dict(cell=c, name="Locked chest") for c in (760,762,802,804)],
             map=dict(width=42, height=41, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=True)
                 for t, cells in groups.items() for c in cells]))
    p = MagePolicy()
    p.update(s)
    return p, s


class FlightContainerTransitTests(unittest.TestCase):
    def test_key_route_does_not_spend_held_key_on_intermediate_chests(self):
        p, s = fixture()
        before = copy.deepcopy(s)
        j = plan_journey(p, s, [], neighbors, probe_kind="flight", plan_only=True)
        self.assertIsNotNone(j)
        self.assertEqual(680, j.route[-1])
        self.assertFalse(set(j.route[1:-1]) & {760,762,802,804},
                         "A chest click is an interaction, not a protected movement step")
        self.assertLessEqual(2*(len(j.route)-1)+j.interaction_budget+3, 20)
        self.assertEqual(before, s)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        self.assertIn(680, p.loot)

    def test_chest_remains_an_admitted_endpoint_when_keys_cover_locks(self):
        p, s = fixture()
        p.keys["golden"] = 4
        j = plan_journey(p, s, [], neighbors, probe_kind="flight", plan_only=True)
        self.assertEqual(804, j.route[-1])
        self.assertEqual(4, j.interaction_budget)

    def test_alternative_route_keeps_existing_safety_gates(self):
        for case in ("enemy", "warning", "heavy", "blocked"):
            with self.subTest(case=case):
                p, s = fixture()
                enemies = []
                if case == "enemy":
                    enemies = [dict(cell=847, name="gnoll scout")]
                elif case == "warning":
                    s["danger_cells"] = [847]
                elif case == "heavy":
                    s["inventory"].append(dict(name="plate armor", equipped=True,
                        identified=False, description="Requires 18 strength."))
                else:
                    p.blocked.update(c for c,t in p.tiles.items() if t["terrain"] == 0)
                self.assertIsNone(plan_journey(p, s, enemies, neighbors,
                                              probe_kind="flight", plan_only=True))


if __name__ == "__main__":
    unittest.main()
