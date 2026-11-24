"""Run 000252 D279–284: a receipted crystal alternative is not a flight reward.

Reduced public room geometry and paired key/chest observations, not original
runtime memory. Recognition tests do not authorize crossing the dart trap.
"""
import copy
import unittest

from tools.keyed_rooms import chest_choice
from tools.policy_geometry import distance
from tools.puzzle_supplies import demands
from tools.room_supplies import discovery_requirements
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["hero"].update(cell=1009, hp=25, max_hp=25, level=2, strength=10)
    terrain = {
        977: 5, 978: 14, 979: 14, 980: 14, 981: 14, 982: 14,
        1007: 14, 1008: 18, 1009: 1, 1010: 1, 1011: 14,
        1036: 14, 1037: 11, 1038: 1, 1039: 11, 1040: 14,
        1065: 14, 1066: 2, 1067: 15, 1068: 1, 1069: 14,
        1094: 14, 1095: 14, 1096: 14, 1097: 14, 1098: 14,
    }
    s["map"] = dict(width=29, height=40, cells=[
        dict(cell=c, terrain=terrain.get(c, 4), observed=True,
             visible=True, effects=[],
             **({"trap": "worn dart trap"} if c == 1008 else {}))
        for y in range(32, 39) for x in range(19, 27)
        for c in [y * 29 + x]])
    s["objects"] = [
        dict(cell=1037, name="Crystal chest", description="You can see an artifact inside."),
        dict(cell=1039, name="Crystal chest", description="You can see a ring inside.")]
    s["keys"] = [dict(name="Crystal key", depth=1, quantity=1)]
    p = verified()
    p.update(s)
    chest_choice(p, s, 1039, {1037, 1039})
    return p, s


def flight(p, s):
    return [d for d in demands(p, s, distance, include_deferred=True)
            if d.kind == "flight"]


def spend(p, s):
    after = copy.deepcopy(s)
    after["keys"] = []
    after["objects"][1] = dict(cell=1039, name="emerald ring",
                               top_item=dict(name="emerald ring", quantity=1))
    p.update(after)
    return after


class ResolvedCrystalFlightTests(unittest.TestCase):
    def test_receipted_alternative_no_longer_reserves_flight(self):
        p, s = fixture()
        self.assertTrue(flight(p, s))
        s = spend(p, s)
        self.assertEqual({1037}, p.resolved_crystal_alternatives)
        # Isolate the remaining alternative after ordinary ring pickup.
        p.loot.pop(1039, None)
        self.assertFalse(flight(p, s),
                         "A witnessed one-key alternative is not a flight retrieval")
        self.assertFalse(discovery_requirements(p, s))
        self.assertIn(1037, p.loot)
        self.assertFalse(p.loot_collection_receipts)
        self.assertNotIn(1008, p.paths(s))
        self.assertEqual("worn dart trap", p.tiles[1008]["trap"])
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.completed_room_rewards)

    def test_key_loss_without_open_chest_is_not_a_choice_receipt(self):
        p, s = fixture()
        s["keys"] = []
        p.update(s)
        self.assertFalse(p.resolved_crystal_alternatives)
        self.assertTrue(flight(p, s))

    def test_new_key_reopens_alternative_for_ordinary_access(self):
        p, s = fixture()
        s = spend(p, s)
        s["keys"] = [dict(name="Crystal key", depth=1, quantity=1)]
        p.update(s)
        self.assertFalse(p.resolved_crystal_alternatives)
        self.assertIn(1037, p.paths(s))
        self.assertTrue(any(lock["cell"] == 1037
                            for lock in p.planner.report["keyed_rooms"]["locks"]))

    def test_independent_mandatory_reward_keeps_flight_obligation(self):
        p, s = fixture()
        s = spend(p, s)
        p.loot.pop(1039, None)
        p.loot[1008] = dict(cell=1008, name="scroll of upgrade")
        self.assertTrue(flight(p, s))
        self.assertTrue(discovery_requirements(p, s))
        self.assertIn(1008, p.loot)
        self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
