"""Reduced public run 000175 D1087 (selection line 3297), not a replay.

The local terrain, foes and known staff charge are public observations.
The 24 accepted retreats and zero interventions come from line 3296.
Other runtime memory is not reconstructed; omitted terrain changes route ranking.
No observations following a changed decision are supplied.
"""
import unittest

from tools import multi_enemy_tactics as multi
from tools.policy_decision import Intent
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=331, hp=17, max_hp=40, level=5, strength=11,
                     buffs=[{"name": "hungry"}])
    terrain = {
        186: 4, 187: 29, 188: 29, 189: 14, 190: 29, 191: 29, 192: 29,
        222: 4, 223: 29, 224: 29, 225: 14, 226: 29, 227: 29, 228: 29,
        258: 4, 259: 1, 260: 1, 261: 1, 262: 1, 263: 1, 264: 1,
        292: 4, 293: 4, 294: 4, 295: 1, 296: 1, 297: 4, 298: 4,
        299: 4, 300: 4, 328: 1, 329: 1, 330: 1, 331: 1, 332: 1,
        333: 4, 364: 8, 365: 1, 366: 1, 367: 1, 368: 1, 369: 4,
        400: 1, 401: 1, 402: 29, 403: 29, 404: 29, 405: 4,
        436: 29, 437: 14, 438: 29, 439: 29, 440: 29, 441: 4,
        444: 12, 472: 29, 473: 14, 474: 29, 475: 29, 476: 29,
        477: 4, 478: 12, 479: 12, 480: 29, 508: 1, 509: 1,
        510: 1, 511: 1, 512: 1, 513: 5, 514: 29, 515: 29, 516: 29,
    }
    s["map"] = dict(width=36, height=40, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [dict(name="slime", cell=368, status_icons=[]),
                    dict(name="slime", cell=475, status_icons=[], health_bar=[3, 19])]
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +2", status="1/6",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["ZAP", "IMBUE", "UNEQUIP"],
        description="Each bolt deals 4-12 damage.")]
    p = verified()
    p.update(s)
    p.pursuit_retreat_moves = 24
    return p, s


class MultiPursuitReassessmentTests(unittest.TestCase):
    def test_due_known_shot_precedes_another_non_choke_retreat(self):
        p, s = fixture()
        self.assertFalse(p.rules.combat_pressure)
        self.assertTrue(multi.needs_retreat(p, s, s["objects"]))
        d = multi.choose(p, s, s["objects"])
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"}, d.action)
        self.assertEqual(368, p.target)
        self.assertEqual(1, p.pursuit_interventions)
        self.assertEqual(24, p.pursuit_last_intervention_move)
        self.assertIsNone(p.multi_retreat_pending)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_full_regular_selector_reaches_bounded_intervention(self):
        p, s = fixture()
        d = p.choose(s)
        self.assertEqual({"type": "item", "id": "item-0", "action": "ZAP"}, d.action)
        self.assertEqual("multi-threat-retreat", d.controller)
        self.assertEqual(368, p.target)

    def test_not_due_or_spent_budget_keeps_retreat_available(self):
        for moves, interventions, last in ((3, 0, 0), (24, 2, 0), (24, 1, 23)):
            with self.subTest(moves=moves, interventions=interventions, last=last):
                p, s = fixture()
                p.pursuit_retreat_moves = moves
                p.pursuit_interventions = interventions
                p.pursuit_last_intervention_move = last
                d = multi.choose(p, s, s["objects"])
                self.assertEqual(Intent.RETREAT, d.intent)
                self.assertEqual(interventions, p.pursuit_interventions)

    def test_unknown_empty_or_cursed_magic_does_not_become_an_intervention(self):
        for status, cursed in (("0/6", False), ("?/6", False), ("1/6", True)):
            with self.subTest(status=status, cursed=cursed):
                p, s = fixture()
                s["inventory"][0].update(status=status, known_cursed=cursed)
                d = multi.choose(p, s, s["objects"])
                self.assertEqual(Intent.RETREAT, d.intent)
                self.assertEqual(0, p.pursuit_interventions)

    def test_hazard_and_multiple_contact_still_veto_intervention(self):
        for case in ("danger", "poison", "contact"):
            with self.subTest(case=case):
                p, s = fixture()
                if case == "danger":
                    s["danger_cells"] = [331]
                elif case == "poison":
                    s["hero"]["buffs"].append({"name": "poisoned"})
                else:
                    s["objects"][1]["cell"] = 330
                d = multi.choose(p, s, s["objects"])
                self.assertTrue(d is None or d.action.get("type") != "item")
                self.assertEqual(0, p.pursuit_interventions)


if __name__ == "__main__":
    unittest.main()
