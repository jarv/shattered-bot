"""Reduced public-evidence fixture for run 000008, decisions 3186–3188.

This is not a reconstructed runtime ledger or a gameplay replay. Fresh refusal
receipts establish pack pressure; the reward remains unfinished throughout.
"""
import copy
import unittest

from tools.inventory_tactics import observe_accepted
from tools.loot_completion import required_loot
from tools.mage_policy import MagePolicy
from tools.mimic_hunt import begin_hunt, hunt_missing_mimic, observe_hunts
from tools.policy_decision import Decision, Intent
from tools.policy_geometry import distance
from tools.priority_resources import choose as progression_pickup, targets
from tools.room_loot import inventory_context
from tools.test_survival_bot import state


class RefusedMimicRewardTests(unittest.TestCase):
    def fixture(self, name="corrupting whip", refused=True):
        s = state()
        s["depth"] = 7
        s["hero"].update(cell=446, hp=47, max_hp=65, strength=13,
                         buffs=[{"name": "hungry"}])
        s["inventory"][0]["status"] = "0/7"
        # Reduced inventory: no item is certified disposable. Full-pack evidence
        # comes from the public receipt, not this fixture's inventory length.
        s["inventory"].append(dict(id="item-4", name="dirk",
                                   identified=False, actions=["DROP", "EQUIP"]))
        floors = {406, 445, 446, 485}
        s["map"] = dict(width=40, height=37, cells=[
            dict(cell=c, terrain=1 if c in floors else 4,
                 visible=True, observed=True) for c in range(1480)])
        p = MagePolicy()
        p.update(s)
        begin_hunt(p, s, 323, {"description": "A suspicious chest."})
        p.mimic_obligations[323]["last"] = 446
        s["objects"] = [dict(cell=446, name=name, top_item=dict(
            name=name, quantity=1, identified=False))]
        p.update(s)
        observe_hunts(p, s, distance)
        if refused:
            pickup = Decision(dict(type="cell", cell=446),
                              "loot: finish shortest observed-room collection tour",
                              Intent.LOOT)
            for _ in range(2):
                after = copy.deepcopy(s)
                after["ui"]["texts"].append(f"You can't carry: {name}.")
                observe_accepted(p, s, pickup, after)
                p.last_state, p.last_decision = copy.deepcopy(s), pickup
                p.update(after)
                s = after
            self.assertEqual(inventory_context(s), p.room_loot_deferred[446])
        return s, p

    def test_refused_reward_yields_without_reacquisition_or_collection_credit(self):
        s, p = self.fixture()
        # Even an exhausted search budget must not turn a *known* refused reward
        # into another vanished-mimic search or a blocking search exception.
        p.mimic_obligations[323]["steps"] = 16
        self.assertIsNone(hunt_missing_mimic(p, s, [], distance))
        self.assertIn(446, required_loot(p))
        self.assertIn(323, p.mimic_obligations)
        self.assertFalse(p.loot_collection_receipts)
        self.assertNotIn(446, p.blocked)
        # A tactical recovery step away must not restart the same refused tour.
        away = copy.deepcopy(s)
        away["hero"]["cell"] = 406
        self.assertIsNone(hunt_missing_mimic(p, away, [], distance))
        self.assertEqual(16, p.mimic_obligations[323]["steps"])

    def test_inventory_change_reopens_pickup_but_charge_gain_does_not(self):
        s, p = self.fixture()
        s["inventory"][0]["status"] = "1/7"
        self.assertIsNone(hunt_missing_mimic(p, s, [], distance))
        s["inventory"].pop()
        decision = hunt_missing_mimic(p, s, [], distance)
        self.assertEqual(dict(type="cell", cell=446), decision.action)
        self.assertEqual(Intent.LOOT, decision.intent)
        self.assertIn(323, p.mimic_obligations)

    def test_no_refusal_keeps_pickup_and_existing_danger_gate(self):
        s, p = self.fixture(refused=False)
        self.assertEqual(446, hunt_missing_mimic(p, s, [], distance).action["cell"])
        s["danger_cells"] = [446]
        self.assertIsNone(hunt_missing_mimic(p, s, [], distance))

    def test_progression_reward_is_still_mandatory(self):
        for name in ("scroll of upgrade", "potion of strength"):
            with self.subTest(name=name):
                s, p = self.fixture(name)
                self.assertIsNone(hunt_missing_mimic(p, s, [], distance))
                self.assertIn(446, targets(p))
                self.assertIn(446, required_loot(p))
                self.assertFalse(p.loot_collection_receipts)
                # Its dedicated higher-priority selector still owns admission.
                p.inventory_pressure = None
                decision = progression_pickup(p, s, [])
                self.assertEqual(446, decision.action["cell"])
                self.assertEqual(Intent.LOOT, decision.intent)


if __name__ == "__main__":
    unittest.main()
