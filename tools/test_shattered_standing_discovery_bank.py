"""Run 179 D229: use admitted standing preparation, not another water detour.

Reduced contemporaneous public geometry and inventory. These are independent
selector fixtures, not observations generated after an alternative movement.
No potion effect, drop, pickup, or successful retrieval is assumed.
"""
import copy
import unittest

from tools.descent_potions import begin
from tools.policy_decision import Intent, PlannerStuck
from tools.policy_geometry import distance, neighbors
from tools.potion_stash import can_protect_potions, stash_cells
from tools.puzzle_supplies import safe_test_bank
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    groups = {
        (4, False): [533, 595, 620, 624, 625],
        (20, True): [534, 592, 622],
        (4, True): [535, 561, 562, 563, 565, 591, 621, 623, 653,
                    680, 681, 682, 683],
        (1, True): [564, 593, 594],
        (27, False): [619, 679, 709],
        (14, False): [649],
        (5, True): [650],
        (29, True): [651, 652],
    }
    s["map"] = dict(width=30, height=35, cells=[
        dict(cell=c, terrain=t, visible=v, observed=True)
        for (t, v), cells in groups.items() for c in cells])
    s["hero"].update(cell=622, hp=25, max_hp=25, strength=10, level=2)
    s["inventory"] += [
        dict(id="food", name="ration of food", identified=True,
             quantity=1, actions=["DROP", "THROW", "EAT"]),
        dict(id="flame", name="potion of liquid flame", identified=True,
             quantity=1, actions=["DROP", "THROW", "DRINK"]),
        dict(id="jade", name="jade potion", identified=False,
             quantity=1, actions=["DROP", "THROW", "DRINK"]),
    ]
    p = verified()
    p.update(s)
    # D229's reconstructed commitment from the accepted preceding selections.
    # This is fixture bookkeeping, not originally recorded runtime memory.
    p.descent_potion_plan = dict(depth=1, steps=10, waits=0,
        candidate="jade potion", bank=652, pending=False, return_steps=9)
    return s, p


class StandingDiscoveryBankTests(unittest.TestCase):
    def test_fresh_standing_bank_starts_protection_before_remote_water(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        jade = s["inventory"][-1]
        for bank in (622, 652):
            staged = dict(s, hero=dict(s["hero"], cell=bank))
            self.assertTrue(safe_test_bank(p, s, bank, distance, neighbors, allow_dry=True))
            self.assertTrue(can_protect_potions(
                p, staged, jade, distance, neighbors, safe_test_bank, isolated_stack=True))
        self.assertEqual([534], stash_cells(p, s, distance, neighbors, safe_test_bank))
        d = begin(p, s)
        self.assertEqual(622, p.descent_potion_plan["bank"])
        self.assertEqual({"type": "cell", "cell": 593}, d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertEqual((622, 534, "drop"),
                         (p.potion_stash["bank"], p.potion_stash["cell"], p.potion_stash["phase"]))
        self.assertFalse(p.potion_stash["dropped"])
        self.assertIsNone(p.potion_stash["pending"])
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.descent_potion_tests)
        self.assertEqual(before, s)

    def test_current_bank_preference_does_not_override_hazard_or_storage_checks(self):
        for hazard in ("trap", "effects", "plant", "visible", "no-drop", "threat"):
            s, p = fixture()
            if hazard == "visible":
                for tile in p.tiles.values():
                    tile["visible"] = False
            elif hazard == "no-drop":
                s["inventory"][-2]["actions"].remove("DROP")
            elif hazard == "threat":
                p.recent_threats[593] = dict(cell=593, name="marsupial rat")
            else:
                for bank in (622, 652):
                    p.tiles[bank][hazard] = ["fire"] if hazard == "effects" else "hazard"
            with self.assertRaises(PlannerStuck, msg=hazard):
                begin(p, s)
            self.assertIsNone(p.potion_stash)
            self.assertIsNone(p.puzzle_probe)

    def test_recorded_water_arrival_cannot_drink_from_departure_visibility(self):
        s, p = fixture()
        s["hero"]["cell"] = 652
        # D228 public visibility: storage at 534/564/594 is no longer visible.
        visible = {591, 592, 593, 620, 621, 622, 623, 650, 651, 652, 653,
                   680, 681, 682, 683}
        for tile in s["map"]["cells"]:
            tile["visible"] = tile["cell"] in visible
        p = verified()
        p.update(s)
        with self.assertRaises(PlannerStuck):
            begin(p, s)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)


if __name__ == "__main__":
    unittest.main()
