"""Reduced public D1350, run 000251, selection line 4031; not a replay.

The twelve accepted retreats and exhausted-lure flag are recorded in that
selection's pursuit report (last receipt: line 4030). This is a deterministic
local fixture, not a reconstruction of the original mutable policy memory.
No observations after an alternative selection are fed to the policy.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools import pursuit_budget as pursuit
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=676, hp=37, max_hp=40, level=5, strength=12,
                     buffs=[{"name": "hungry"}, {"name": "barrier"}])
    terrain = {
        632: 5, 633: 4, 634: 4, 635: 4, 636: 4, 637: 4, 638: 4,
        670: 4, 671: 1, 672: 1, 673: 1, 674: 1, 675: 1, 676: 1,
        677: 1, 678: 4,
        710: 4, 711: 29, 712: 29, 713: 29, 714: 29, 715: 29,
        716: 14, 717: 29, 718: 4,
        750: 4, 751: 29, 752: 29, 753: 29, 754: 29, 755: 29,
        756: 14, 757: 29, 758: 4,
    }
    s["map"] = dict(width=40, height=50, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [
        dict(name="swarm of flies", cell=673, health_bar=[3, 21]),
        dict(name="swarm of flies", cell=675, health_bar=[3, 21])]
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +2", equipped=True,
        identified=True, curse_known=True, known_cursed=False, status="1/6",
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE", "ZAP"],
        description="This tier-1 melee weapon deals 3-10 damage and requires "
                    "9 strength. Each bolt from this wand deals 4-12 damage.")]
    p = verified()
    p.update(s)
    p.pursuit_retreat_moves = 12
    pursuit.review_outcome(p, s)
    return p, s


class HealthyExhaustedPursuitTests(unittest.TestCase):
    def test_exhausted_healthy_pursuit_reaches_existing_bounded_shot(self):
        p, s = fixture()
        self.assertTrue(p.pursuit_lure_exhausted)
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))
        d = multi.choose(p, s, s["objects"])
        self.assertIsNotNone(d, "Healthy HP must not suppress an exhausted-pursuit shot")
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"}, d.action)
        self.assertEqual(675, p.target)
        self.assertEqual(1, p.pursuit_interventions)
        self.assertEqual(12, p.pursuit_last_intervention_move)
        self.assertIsNone(p.multi_retreat_pending)
        self.assertEqual("1/6", s["inventory"][0]["status"])
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_regular_selector_reaches_the_same_bounded_intervention(self):
        p, s = fixture()
        d = p.choose(s)
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"}, d.action)
        self.assertEqual("multi-threat-retreat", d.controller)
        self.assertEqual(675, p.target)

    def test_healthy_unexhausted_pursuit_still_conserves_magic(self):
        p, s = fixture()
        p.pursuit_retreat_moves = 4
        p.pursuit_lure_exhausted = False
        self.assertIsNone(pursuit.reassess(p, s, s["objects"]))
        self.assertEqual(0, p.pursuit_interventions)

    def test_exhaustion_does_not_bypass_attack_or_safety_gates(self):
        for case in ("empty", "unknown", "cursed", "blocked", "danger",
                     "poison", "contact", "spent", "not-due"):
            with self.subTest(case=case):
                p, s = fixture()
                staff = s["inventory"][0]
                if case == "empty":
                    staff["status"] = "0/6"
                elif case == "unknown":
                    staff["status"] = "?/6"
                elif case == "cursed":
                    staff["known_cursed"] = True
                elif case == "blocked":
                    s["objects"][1]["cell"] = 674
                    p.tiles[675]["terrain"] = 4
                elif case == "danger":
                    s["danger_cells"] = [676]
                elif case == "poison":
                    s["hero"]["buffs"].append({"name": "poisoned"})
                elif case == "contact":
                    s["objects"][0]["cell"] = 677
                elif case == "spent":
                    p.pursuit_interventions = 2
                else:
                    p.pursuit_last_intervention_move = 11
                self.assertIsNone(pursuit.reassess(p, s, s["objects"]))
                self.assertIsNone(p.target)


if __name__ == "__main__":
    unittest.main()
