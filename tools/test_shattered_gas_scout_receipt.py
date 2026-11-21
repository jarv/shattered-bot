"""Reduced run 000076 public door/bank observations, decisions 202-204.

Synthetic helper memory retains earlier observed gas and chest 615, not recorded
runtime memory or a full-run reconstruction. Validate the opening and escape,
then stop at the first changed local helper selection. No game execution or
observations after that changed input.
"""
import copy
import unittest

from tools.policy_decision import Decision, Intent
from tools.policy_geometry import neighbors
from tools.puzzle_supplies import stage_known_gas, unscouted_entrance
from tools.room_tactics import Journey
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.toxic_escape import escape


GAS = "A greenish cloud of toxic gas is swirling here."


def approach():
    s = state()
    s["hero"].update(cell=767, strength=10)
    groups = {
        4: [613,651,726,727,728,729,731,732,764,770,802,808],
        1: [614,653,690,691,692,765,766,767,768,803,807],
        29: [615,618,619,620,654,655,656,693,694,804,805,806],
        19: [616,657],
        25: [617],
        20: [652,769],
        5: [730],
    }
    gas = {614,615,616,618,619,620,652,653,654,655,656,657,
           690,691,692,693,694}
    s["map"] = dict(width=38, height=38, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c>=726,
             effects=[GAS] if c in gas else [])
        for t, cells in groups.items() for c in cells])
    s["inventory"].append(dict(id="purity", name="potion of purity",
        identified=True, quantity=1, actions=["DROP", "THROW", "DRINK"]))
    p = verified()
    p.update(s)
    p.loot[615] = dict(cell=615, name="Chest")
    return p, s


def opened(s):
    s = copy.deepcopy(s)
    s["hero"]["cell"] = 730
    door = next(t for t in s["map"]["cells"] if t["cell"] == 730)
    door.update(terrain=6, effects=[GAS])
    return s


class GasScoutReceiptTests(unittest.TestCase):
    def scouted(self):
        p, s = approach()
        d = stage_known_gas(p, s, s["inventory"][-1], neighbors)
        self.assertEqual(dict(type="cell", cell=730), d.action)
        p.last_decision = d
        arrival = opened(s)
        p.update(arrival)
        d = escape(p, arrival)
        self.assertEqual(dict(type="cell", cell=767), d.action)
        p.last_decision = d
        p.update(s)
        return p, s

    def test_observed_gas_arrival_does_not_restart_unprotected_scout(self):
        p, s = self.scouted()
        before = copy.deepcopy(s)
        d = stage_known_gas(p, s, s["inventory"][-1], neighbors)
        self.assertEqual(dict(type="item", id="purity", action="DRINK"), d.action,
                         "Use known protection, not another unprotected door scout")
        self.assertEqual(before, s)
        self.assertEqual("gas", p.room_journey.kind)
        self.assertIn(615, p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertIsNone(p.room_supply_permit)
        # Selection is not a receipt of the buff, consumption, or collection.
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))
        self.assertIsNone(p.room_journey)
        self.assertIn(615, p.loot)

    def test_rejected_or_unobserved_arrivals_do_not_supply_scouting(self):
        for case in ("no-arrival", "unseen", "floor", "branch", "wrong-input",
                     "trap", "plant", "other-cloud"):
            p, s = approach()
            p.last_decision = Decision(dict(type="cell", cell=730),
                                       "room: scout", Intent.REPOSITION)
            a = opened(s)
            door = next(t for t in a["map"]["cells"] if t["cell"] == 730)
            if case == "no-arrival": a["hero"]["cell"] = 767
            elif case == "unseen": door["visible"] = False
            elif case == "floor": a["depth"] = 2
            elif case == "branch": a["branch"] = 1
            elif case == "wrong-input": p.last_decision.action = dict(type="wait")
            elif case == "trap": door["trap"] = "burning trap"
            elif case == "plant": door["plant"] = "firebloom"
            elif case == "other-cloud": door["effects"].append("Fire is raging here.")
            p.update(a)
            self.assertFalse(getattr(p, "gas_entrance_receipts", set()), case)

    def test_receipt_does_not_waive_fresh_hazards_or_floor_identity(self):
        for change in ("trap", "plant", "effects", "branch", "floor"):
            p, s = self.scouted()
            if change in {"branch", "floor"}:
                s["branch" if change == "branch" else "depth"] = 2
            else:
                p.tiles[730][change] = [GAS] if change == "effects" else "hazard"
            self.assertEqual(730, unscouted_entrance(
                p, s, Journey("gas", [767,730,691,652,615], 1)), change)
        p, _ = self.scouted()
        p.memory.reset_floor(767)
        self.assertFalse(getattr(p, "gas_entrance_receipts", set()))


if __name__ == "__main__":
    unittest.main()
