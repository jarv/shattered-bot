"""Reduced public D1230 geometry from run 000183, not a gameplay replay.

Played source: 108fa9c75a72fbc6c0ebbda361763314ae47f713.

The stash/plan dictionaries are explicit reconstructed fixture bookkeeping:
D1225-1226 dropped other colors at 451, D1229 returned to bank 562.
No hidden potion identity or original runtime-memory recovery is claimed.
"""
import copy
import unittest

from tools import descent_potions as discovery
from tools.policy_geometry import distance, neighbors
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=562, hp=40, max_hp=40, strength=10, buffs=[])
    # Only the observed local bank/storage pocket; omitted space is not a route.
    terrain = {
        414:4, 415:1, 416:1, 417:20, 418:4,
        450:4, 451:1, 452:29, 453:1, 454:4, 455:4,
        486:4, 487:1, 488:29, 489:1, 490:1, 491:4,
        522:4, 523:1, 524:29, 525:29, 526:1, 527:4,
        558:4, 559:1, 560:1, 561:29, 562:1, 563:4,
        594:4, 595:4, 596:1, 597:29, 598:20, 599:4,
        631:4, 632:1, 633:29, 634:1, 635:4,
    }
    s["map"] = dict(width=36, height=37, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [dict(id="item-10", name="indigo potion", quantity=1,
                            identified=False, actions=["DROP", "THROW", "DRINK"])]
    s["objects"] = [dict(cell=451, name="turquoise potion",
                         top_item=dict(name="turquoise potion", quantity=1))]
    p = verified()
    p.update(s)
    p.descent_potion_plan = dict(depth=3, steps=8, waits=0, pending=False,
                                 candidate="indigo potion", bank=562)
    p.potion_stash = dict(depth=3, bank=562, cell=451, candidate="indigo potion",
                          phase="ready", steps=8, pending=None,
                          purpose=discovery.PURPOSE,
                          dropped={"potion of haste":1, "turquoise potion":1})
    return p, s


class StashBankCommitmentTests(unittest.TestCase):
    def test_ready_stash_keeps_freshly_safe_dry_bank_not_preferred_water(self):
        p, s = fixture()
        self.assertTrue(discovery.safe_test_bank(
            p, s, 562, distance, neighbors, allow_dry=True))
        self.assertTrue(discovery.safe_test_bank(
            p, s, 525, distance, neighbors, allow_dry=True))
        before = copy.deepcopy(s)
        decision = discovery.advance(p, s)
        self.assertEqual({"type":"item", "id":"item-10", "action":"DRINK"},
                         decision.action,
                         "Do not leave stash bank 562 for preferred water 525")
        self.assertEqual(562, p.descent_potion_plan["bank"])
        self.assertEqual("retrieve", p.potion_stash["phase"])
        self.assertTrue(p.descent_potion_plan["pending"])
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)
        self.assertFalse(p.loot_collection_receipts)
        self.assertEqual(before, s)

    def test_lost_bank_admission_does_not_switch_banks_or_drink(self):
        for hazard in ("effects", "trap", "plant", "visible", "collateral"):
            with self.subTest(hazard=hazard):
                p, s = fixture()
                if hazard == "visible":
                    p.tiles[562]["visible"] = False
                elif hazard == "collateral":
                    # Changed fuel can connect the bank's fire footprint to storage.
                    for c in (525, 488, 452):
                        p.tiles[c]["terrain"] = 2
                else:
                    p.tiles[562][hazard] = ["cold"] if hazard == "effects" else "hazard"
                decision = discovery.advance(p, s)
                self.assertIsNone(decision)
                self.assertIsNotNone(p.potion_stash)
                self.assertEqual("ready", p.potion_stash["phase"])
                self.assertFalse(p.descent_potion_plan["pending"])
                self.assertFalse(p.strength_identified)

    def test_unstashed_discovery_still_prefers_water(self):
        p, s = fixture()
        p.potion_stash = None
        decision = discovery.advance(p, s)
        self.assertEqual({"type":"cell", "cell":525}, decision.action)


if __name__ == "__main__":
    unittest.main()
