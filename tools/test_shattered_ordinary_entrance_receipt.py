"""Run 63 decisions 182-183: ordinary exploration really enters door 593.

Reduced public observations, not reconstructed controller memory or a replay.
An entrance receipt certifies scouting only, never protection or collection.
"""
import copy
import unittest
from types import SimpleNamespace

from tools.policy_decision import Decision, Intent
from tools.puzzle_supplies import observe_pool_entrance, unscouted_entrance
from tools.room_tactics import Journey


def arrival():
    before = dict(depth=1, branch=0, hero=dict(cell=633),
                  map=dict(width=41, height=34, cells=[
                      dict(cell=593, terrain=5, visible=True, observed=True)]))
    after = copy.deepcopy(before)
    after["hero"]["cell"] = 593
    after["map"]["cells"][0]["terrain"] = 6
    p = SimpleNamespace(
        pool_approach_pending=None, pool_entrance_pending=None,
        flight_entrance_pending=None, pool_entrance_receipts=set(),
        flight_entrance_receipts=set(),
        tiles={c: dict(terrain=5 if c==593 else 18)
               for c in [551,593,594,595,596,638,680]},
        effects_block_movement=lambda tile: bool(tile.get("effects")),
        last_decision=Decision(dict(type="cell", cell=593),
                               "explore: frontier", Intent.EXPLORE))
    return p, before, after


class OrdinaryEntranceReceiptTests(unittest.TestCase):
    def test_exploration_arrival_counts_as_scouting_after_reclosure(self):
        p, before, after = arrival()
        observe_pool_entrance(p, before, after)
        self.assertIn((1, 0, 593), p.flight_entrance_receipts)
        journey = Journey("flight", [551, 593, 594, 595, 596, 638, 680], 1)
        self.assertIsNone(unscouted_entrance(p, before, journey))
        self.assertIsNone(p.flight_entrance_pending)

    def test_only_actual_visible_same_floor_adjacent_door_arrival_counts(self):
        for case in ("no-arrival", "closed", "unseen", "floor", "branch",
                     "wrong-input", "no-before", "distant", "trap", "effect"):
            p, before, after = arrival()
            tile = after["map"]["cells"][0]
            if case == "no-arrival": after["hero"]["cell"] = 633
            elif case == "closed": tile["terrain"] = 5
            elif case == "unseen": tile["visible"] = False
            elif case == "floor": after["depth"] = 2
            elif case == "branch": after["branch"] = 1
            elif case == "wrong-input": p.last_decision.action = dict(type="wait")
            elif case == "no-before": before = None
            elif case == "distant": before["hero"]["cell"] = 1163
            elif case == "trap": tile["trap"] = "burning trap"
            elif case == "effect": tile["effects"] = ["cloud of toxic gas"]
            observe_pool_entrance(p, before, after)
            self.assertFalse(p.flight_entrance_receipts, case)

    def test_receipt_does_not_waive_new_door_hazards(self):
        p, before, after = arrival()
        observe_pool_entrance(p, before, after)
        p.tiles[593]["trap"] = "burning trap"
        self.assertEqual(593, unscouted_entrance(
            p, before, Journey("flight", [551, 593, 594], 1)))


if __name__ == "__main__":
    unittest.main()
