"""Reduced public geometry from recording 000057, decisions 3926-3927.

This is an isolated selector fixture, not recovered runtime memory or a replay.
"""
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Intent
from tools.room_loot import before_room_exit


def fixture():
    p = MagePolicy()
    p.depth = 9
    # Retain the observed key lane and the ordinary chest's approach only.
    p.tiles = {c: dict(cell=c, terrain=29 if c == 436 else 1,
                       visible=True, observed=True, effects=[])
               for c in (333, 334, 366, 368, 402, 436)}
    p.loot = {
        366: dict(cell=366, name="Chest"),
        436: dict(cell=436, name="iron key",
                  top_item=dict(name="iron key", quantity=1)),
    }
    s = dict(depth=9, status="ready", modal=False, danger_cells=[],
             hero=dict(cell=368, hp=9, max_hp=70, strength=13,
                       buffs=[dict(name="starving"), dict(name="barrier")]),
             map=dict(width=33, height=38), inventory=[],
             objects=list(p.loot.values()))
    return p, s


class KeyTourArbitrationTests(unittest.TestCase):
    def test_admitted_key_lane_is_not_reversed_by_quiet_room_tour(self):
        p, s = fixture()
        paths = p.paths(s)
        self.assertIn(436, paths)
        admitted = p.toward(s, 436, "loot: collect key", paths, intent=Intent.LOOT)
        self.assertEqual(402, admitted.action["cell"])
        selected = before_room_exit(p, s, admitted) or admitted
        self.assertEqual(402, selected.action["cell"])
        self.assertEqual("loot: collect key", selected.reason)
        self.assertIn(436, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_ordinary_tour_still_collects_chest_without_waiving_key(self):
        p, s = fixture()
        admitted = p.cell(402, "explore: frontier", intent=Intent.EXPLORE)
        selected = before_room_exit(p, s, admitted)
        self.assertEqual(334, selected.action["cell"])
        self.assertEqual({366, 436}, set(p.room_loot_plan["order"]))
        self.assertFalse(p.loot_collection_receipts)

    def test_key_admission_still_requires_walkable_observed_route(self):
        p, s = fixture()
        p.tiles[402]["trap"] = "observed trap"
        self.assertNotIn(436, p.paths(s))
        self.assertIn(436, p.loot)
        self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
