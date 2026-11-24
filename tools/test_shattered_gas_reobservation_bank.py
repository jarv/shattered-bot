"""Reduced D195 public geometry; staging is not a successful potion test.

The original selector was separately reconstructed against inputs 0..195.
This fixture retains the chasm-adjacent approach and the observed western bank.
It does not supply any observation after a changed decision.
"""
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.puzzle_supplies import Demand, revisit_flight_room, safe_test_bank
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import Intent


def fixture():
    s = state()
    s["hero"].update(cell=891, hp=25, max_hp=25, strength=10)
    s["map"] = dict(width=50, height=29, cells=[])
    groups = {
        (4, False): [888, 889, 887, 1040],
        (4, True): [890, 990, 844, 894, 944, 991, 992, 994, 840],
        (1, False): [939, 989, 1039, 1041, 1042, 1043, 1093, 1094],
        (5, True): [940, 993],
        (14, False): [1037, 1038],
        (1, True): [841, 891, 941, 942],
        (0, True): [842, 843, 892, 893],
        (29, True): [943],
        (29, False): [937, 938, 987, 988, 1044, 1045, 1095],
    }
    for (terrain, visible), cells in groups.items():
        for c in cells:
            t = dict(cell=c, terrain=terrain, visible=visible, observed=True)
            if c >= 1041:
                t["effects"] = ["A greenish cloud of toxic gas is swirling here."]
            s["map"]["cells"].append(t)
    s["objects"] = []
    s["inventory"] = [
        dict(id=str(i), name=name, quantity=1, identified=False,
             actions=["DRINK", "DROP", "THROW"])
        for i, name in enumerate(("charcoal potion", "bistre potion"))]
    p = verified()
    p.update(s)
    p.loot[1095] = dict(cell=1095, name="Chest")
    p.puzzle_gas_bank = 942
    # Both doors were entered before D195 (D190 and D192); reclosure
    # does not erase the original controller's accepted entrance receipts.
    p.gas_entrance_receipts.update({(1, 0, 940), (1, 0, 993)})
    return s, p


class GasReobservationBankTests(unittest.TestCase):
    def test_revisit_uses_observed_test_geometry_not_chasm_adjacent_bank(self):
        s, p = fixture()
        d = revisit_flight_room(p, s, Demand("gas", "potion of purity", 1042), distance)
        self.assertIsNotNone(d)
        self.assertEqual(938, p.puzzle_gas_bank,
                         "Gas staging must not prefer the untestable chasm-adjacent bank")
        self.assertEqual(dict(type="cell", cell=940), d.action)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertEqual((891, 940, 939, 938), d.navigation_route)
        # Remembered geometry authorizes only ordinary reobservation travel.
        self.assertFalse(safe_test_bank(p, s, 938, distance, neighbors, allow_dry=True))
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.loot_collection_receipts)
        self.assertIn(1095, p.loot)

    def test_no_compatible_bank_does_not_authorize_hazard_or_drink(self):
        s, p = fixture()
        p.tiles[937]["terrain"] = 0
        p.tiles[987]["terrain"] = 0
        p.tiles[1037]["terrain"] = 0
        self.assertIsNone(revisit_flight_room(
            p, s, Demand("gas", "potion of purity", 1042), distance))
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)


if __name__ == "__main__":
    unittest.main()
