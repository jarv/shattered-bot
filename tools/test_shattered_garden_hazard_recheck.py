"""Public garden-description reduction from recording 000137, decisions 1042–1110.

This is a deterministic geometry fixture, not recorded policy memory or replay.
"""
import copy
import unittest

from tools.garden_tactics import GARDEN_DESCRIPTION
from tools.policy_geometry import distance
from tools.resource_tactics import recheck_hazards
from tools.test_regular_feedback import arena


def fixture(effects):
    s, p = arena()
    s["depth"] = 2
    s["hero"].update(cell=40, hp=30, max_hp=30, buffs=[])
    # Reduce the observed path to a garden to three ordinary corridor cells.
    for tile in s["map"]["cells"]:
        tile.update(terrain=1 if tile["cell"] in (40, 41, 42, 43) else 4,
                    effects=[])
        if tile["cell"] == 43:
            tile.update(visible=False, effects=list(effects))
    p.update(s)
    p.exhausted.update(p.tiles)
    p.visits.update({c: 1 for c in p.tiles})
    return s, p


class GardenHazardRecheckTests(unittest.TestCase):
    def test_remembered_garden_does_not_create_an_expiry_observation_trip(self):
        s, p = fixture([GARDEN_DESCRIPTION])
        tiles = copy.deepcopy(p.tiles)
        self.assertFalse(p.effects_block_movement(p.tiles[43]))
        self.assertIsNone(recheck_hazards(p, s, p.paths(s), distance))
        self.assertIsNone(p.hazard_recheck_pending)
        self.assertEqual(0, p.hazard_recheck_steps)
        self.assertEqual(tiles, p.tiles)  # No invented visibility or clearance.
        self.assertFalse(p.cleared_floors)

    def test_missing_exit_search_is_not_preempted_by_garden_description(self):
        s, p = fixture([GARDEN_DESCRIPTION])
        d = p.explore(s, [])
        self.assertEqual("search", d.action["type"])
        self.assertEqual("explore: search walls for missing rooms/keys", d.reason)
        self.assertEqual(0, p.hazard_recheck_steps)
        self.assertEqual(1, p.searches)

    def test_smoke_still_has_an_observation_route(self):
        s, p = fixture(["A cloud of thick black smoke is swirling here."])
        self.assertIsNotNone(recheck_hazards(p, s, p.paths(s), distance))
        self.assertEqual(43, p.hazard_recheck_pending["hazard"])

    def test_real_unknown_and_mixed_effects_still_require_observation(self):
        for effects in (
            ["A greenish cloud of toxic gas is swirling here."],
            ["The air is unnaturally frigid here."],
            ["Unrecognized public effect."],
            [GARDEN_DESCRIPTION, "A fire is raging here."],
        ):
            with self.subTest(effects=effects):
                s, p = fixture(effects)
                before = copy.deepcopy(p.tiles[43])
                d = recheck_hazards(p, s, p.paths(s), distance)
                self.assertIsNotNone(d)
                self.assertIn("recheck remembered hazard", d.reason)
                self.assertNotEqual(43, d.action["cell"])
                self.assertEqual(43, p.hazard_recheck_pending["hazard"])
                self.assertEqual(before, p.tiles[43])
                self.assertNotIn(43, p.paths(s))


if __name__ == "__main__":
    unittest.main()
