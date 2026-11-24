"""Run 000246 D5408: reduced public fixture, not recovered runtime memory.

The original scouting step was 631 -> 583 with a bat at 679. No later
observations are fed to a changed selector, and no survival is asserted.
"""
import unittest

from tools.challenge_combat import exposure
from tools.doorway_tactics import doorway_first
from tools.policy_geometry import distance, neighbors, line_clear
from tools.policy_runtime import Context
from tools.policy_tree import POLICY
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=11, branch=0)
    s["hero"].update(cell=631, hp=4, max_hp=85, strength=14, level=14,
                     buffs=[{"name": "starving"}, {"name": "wands empowered"}])
    terrain = {
        441: 4, 442: 4, 443: 29, 444: 1, 445: 4, 446: 4,
        488: 5, 489: 29, 490: 29, 491: 4, 492: 4,
        535: 4, 536: 29, 537: 29, 538: 4,
        582: 4, 583: 29, 584: 29, 585: 4,
        629: 4, 630: 29, 631: 29, 632: 12, 633: 4,
        676: 4, 677: 29, 678: 29, 679: 29, 680: 4, 681: 4,
    }
    s["map"] = dict(width=47, height=50, cells=[
        dict(cell=c, terrain=t, observed=True,
             visible=c not in {445, 446, 492, 633, 681}, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="vampire bat", cell=679, status_icons=[],
        description="These brisk and tenacious inhabitants of the caves are "
                    "much more dangerous than they seem. They replenish their "
                    "health with each successful attack, which allows them "
                    "to defeat much larger opponents.")]
    s["inventory"] = [dict(id="item-0",
        name="vampiric staff of magic missile +4", equipped=True,
        identified=True, curse_known=True, known_cursed=False, status="6/8",
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE", "ZAP"],
        description="This tier-1 melee weapon deals 5-14 damage and requires "
                    "8 strength. Each bolt from this wand deals 6-16 damage.")]
    p = verified()
    p.update(s)
    return p, s


class BatDoorwayPressureTests(unittest.TestCase):
    def test_two_cell_bat_gap_is_not_zero_exposure(self):
        p, s = fixture()
        risk = exposure(p, s, s["objects"], 583, distance, line_clear)
        self.assertEqual(0, risk["melee"])
        self.assertEqual(1, risk["fast_pursuit"])

    def test_critical_scout_yields_to_existing_stationary_attack(self):
        p, s = fixture()
        self.assertIsNone(doorway_first(p, s, s["objects"],
                                       distance, neighbors, line_clear))
        self.assertIn("low_health_exposed",
                      p.planner.report["doorway_first"]["violations"])
        attack = p.best_attack(s, s["objects"][0])
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"},
                         attack.action)
        self.assertEqual(679, p.target)
        self.assertIsNone(p.doorway_hold)

    def test_species_speed_is_not_inferred_for_other_fliers(self):
        p, s = fixture()
        s["objects"][0]["name"] = "golden bee"
        self.assertEqual(0, exposure(p, s, s["objects"], 583,
                                    distance, line_clear)["fast_pursuit"])

    def test_selector_uses_charged_attack_instead_of_another_scout(self):
        p, s = fixture()
        # D5406/5407 publicly inspected this bat; the recording's D5408
        # report says no status buffs. This is explicit reduced bookkeeping,
        # not a claim that the complete runtime policy was reconstructed.
        p.inspection_cache = dict(name="vampire bat", cell=679, buffs=set())
        context = Context(p, s, enemies=s["objects"], active=s["objects"])
        decision = POLICY(context)
        self.assertEqual("ordinary-combat", decision.controller)
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"},
                         decision.action)
        self.assertEqual(679, p.target)

    def test_sleep_and_distant_gaps_still_add_no_pursuit(self):
        p, s = fixture()
        s["objects"][0]["sleeping"] = True
        self.assertEqual(0, exposure(p, s, s["objects"], 583,
                                    distance, line_clear)["exposure"])
        s["objects"][0]["sleeping"] = False
        self.assertEqual(0, exposure(p, s, s["objects"], 536,
                                    distance, line_clear)["exposure"])

    def test_species_gate_and_other_known_fast_species(self):
        p, s = fixture()
        s["objects"][0]["name"] = "sewer crab"
        self.assertEqual(1, exposure(p, s, s["objects"], 583,
                                    distance, line_clear)["fast_pursuit"])
        p.unit_strategies_enabled = False
        self.assertEqual(0, exposure(p, s, s["objects"], 583,
                                    distance, line_clear)["fast_pursuit"])


if __name__ == "__main__":
    unittest.main()
