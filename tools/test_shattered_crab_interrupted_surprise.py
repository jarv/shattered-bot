"""Reduced public D1846/D1863 geometry from recording 000243.

The armed plan is a source-constrained reconstruction, not recorded memory.
The clock gap and repeated doorway occupant are public observations. These
isolated selector probes dispatch nothing and assert no eventual quest success.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.great_crab_tactics import choose, guard_movement
from tools import test_shattered_explored_ghost_crab_escape as crab_fixtures


class InterruptedCrabSurpriseTests(unittest.TestCase):
    def fixture(self):
        terrain = {548: 29, 579: 29, 610: 5, 640: 29, 670: 1,
                   700: 1, 730: 1, 761: 1, 793: 1, 825: 9,
                   856: 20, 887: 1, 918: 6}
        s = dict(scene="GameScene", status="ready", modal=False,
                 depth=4, branch=0, danger_cells=[],
                 hero=dict(cell=887, hp=36, max_hp=45, strength=12, buffs=[]),
                 evaluation_stats=dict(elapsed_turns=1847),
                 inventory=[], objects=[dict(name="great crab", cell=918)],
                 ui=dict(texts=[], buttons=[]),
                 map=dict(width=31, height=46, cells=[
                     dict(cell=c, terrain=t, observed=True,
                          visible=c not in {548, 579, 610, 730, 761}, effects=[])
                     for c, t in terrain.items()]))
        p = MagePolicy()
        p.update(s)
        p.great_crab_plan = dict(depth=4, branch=0, door=918, hide=887,
                                start_hp=44, steps=5, waits=5, last_crab=None,
                                armed=True, departing=True, clock=1838)
        return s, p

    def test_intervening_combat_cannot_reuse_an_old_entry_claim(self):
        s, p = self.fixture()
        d = choose(p, s, s["objects"])
        self.assertEqual(dict(type="cell", cell=856), d.action,
                         "An interrupted lure must retreat, not strike the old doorway occupant")
        self.assertIsNone(p.great_crab_plan)
        guard_movement(p, s, d)
        self.assertIsNone(p.best_attack(s, s["objects"][0]))
        self.assertNotIn(p.ghost_quest["stage"], {"reward", "done"})

    def test_uninterrupted_departure_and_arrival_still_allow_one_strike(self):
        s, p, door, hide = crab_fixtures.CrabEscapeTests().begin_hide()
        s["evaluation_stats"] = dict(elapsed_turns=10)
        p.great_crab_plan["clock"] = 9
        self.assertEqual("wait", choose(p, s, []).action["type"])
        import copy
        arrived = copy.deepcopy(s)
        arrived["evaluation_stats"]["elapsed_turns"] = 11
        arrived["objects"] = [dict(name="great crab", cell=door)]
        next(t for t in arrived["map"]["cells"] if t["cell"] == door)["terrain"] = 6
        p.update(arrived)
        self.assertEqual(dict(type="cell", cell=door),
                         choose(p, arrived, arrived["objects"]).action)
        self.assertIsNone(p.great_crab_plan)


if __name__ == "__main__":
    unittest.main()
