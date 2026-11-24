"""Reduced public pickup D429 of recording 000211; no gameplay replay."""
import copy
import unittest

from tools.policy_decision import Decision, Intent, TacticalBlocked
from tools.policy_geometry import distance, neighbors, line_clear
from tools.room_supplies import observe
from tools.tactical_recovery import recover
from tools.objective_planning import preparation_allowed
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture(stash_changes=None):
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=459, hp=30, max_hp=30)
    s["map"] = dict(width=36, height=40, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
        for c in (422, 423, 424, 458, 459, 460, 494, 495, 496)])
    potion = dict(name="ivory potion", id="item-6", quantity=1,
                  identified=False, actions=["DROP", "THROW", "DRINK"])
    s["objects"] = [dict(cell=459, name="ivory potion", top_item=potion)]
    p = verified()
    p.update(s)
    # Explicit reconstructed recovery bookkeeping from D299, not saved memory.
    p.potion_stash = dict(depth=2, bank=1195, cell=1198,
                         candidate="turquoise potion", phase="retrieve",
                         steps=9, dropped={"azure potion": 1,
                                           "potion of liquid flame": 1},
                          pending=None)
    p.potion_stash.update(stash_changes or {})
    p.puzzle_drinks.add((2, "turquoise potion"))
    blocked = TacticalBlocked("obligation:potion-stash",
        "Potion stash retrieval blocked by observed hazard or unreachable ground")
    recover(p, s, [], blocked, distance, neighbors, line_clear)
    after = copy.deepcopy(s)
    after["inventory"].append(potion)
    after["objects"] = []
    d = Decision(dict(type="cell", cell=459), "loot: pickup", Intent.LOOT)
    return p, s, d, after


class StashSupplyRearmingTests(unittest.TestCase):
    def test_verified_new_supply_rearms_preparation_not_collection(self):
        p, s, d, after = fixture()
        self.assertFalse(preparation_allowed(p, s))
        receipt = observe(p, s, d, after)
        self.assertEqual(["potion-preparation"], receipt["preparation_reactivated"])
        self.assertTrue(preparation_allowed(p, after),
                        "A blocked old stash must not veto newly collected supplies")
        self.assertEqual(1, p.room_supply_pickups["ivory potion"])
        self.assertIn((2, "turquoise potion"), p.puzzle_drinks)
        self.assertIsNone(p.potion_stash)
        self.assertTrue(p.deferred_obligations)
        self.assertEqual({"azure potion": 1, "potion of liquid flame": 1},
                         p.deferred_obligations[0]["obligation"]["confirmed_drops"])
        self.assertFalse(p.descent_counts_as_clear())
        self.assertFalse(p.loot_collection_receipts)

    def test_no_rearming_without_matching_accepted_pickup(self):
        for mode in ("no-gain", "no-ground", "wrong-cell", "cross-floor",
                     "cross-branch", "already-tested", "probe-failed"):
            with self.subTest(mode=mode):
                p, s, d, after = fixture()
                if mode == "no-gain": after["inventory"] = s["inventory"]
                elif mode == "no-ground": s["objects"] = []
                elif mode == "wrong-cell": after["hero"]["cell"] = 460
                elif mode == "cross-floor": after["depth"] = 3
                elif mode == "cross-branch": after["branch"] = 1
                elif mode == "already-tested": p.puzzle_drinks.add((2, "ivory potion"))
                else:
                    recover(p, s, [], TacticalBlocked("obligation:potion-probe",
                        "Potion probe exceeded its recovery budget"),
                        distance, neighbors, line_clear)
                observe(p, s, d, after)
                self.assertFalse(preparation_allowed(p, s))


if __name__ == "__main__":
    unittest.main()
