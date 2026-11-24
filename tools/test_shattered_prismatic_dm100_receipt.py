"""Reduced public decisions 3180-3182 of recording 000242.

Only receipt/targeting bookkeeping is reconstructed, not original run memory.
No game dispatch or observations after an alternative selection.
"""
import copy
import unittest

from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory
from tools.policy_nodes import dm100_door_escape
from tools.policy_runtime import Context
from tools.test_challenge_rules import verified


def fixture():
    before = dict(scene="GameScene", status="ready", modal=False,
        depth=8, branch=0, danger_cells=[],
        hero=dict(cell=867, hp=33, max_hp=70, level=11, strength=12,
                  hero_class="mage", buffs=[dict(name="hungry")],
                  talents=[dict(name="arcane vision", points=1)]),
        evaluation_stats=dict(experience=8, experience_to_level=60,
                              elapsed_turns=3043),
        inventory=[dict(id="item-0", name="staff of prismatic light +5",
            equipped=True, identified=True, curse_known=True, known_cursed=False,
            status="6/8", actions=["ZAP", "IMBUE", "UNEQUIP"])],
        objects=[dict(cell=1179, name="DM-100", status_icons=[]),
                 dict(cell=791, name="silver potion",
                      top_item=dict(name="silver potion", identified=False))],
        ui=dict(texts=[], buttons=[]),
        map=dict(width=39, height=41, cells=[
            dict(cell=c, terrain=8 if c == 1023 else 29,
                 visible=True, observed=True, effects=[])
            for c in range(867, 1180, 39)]))
    targeting = copy.deepcopy(before)
    targeting["status"] = "targeting"
    after = copy.deepcopy(before)
    after["objects"] = [before["objects"][1], dict(cell=1179,
        name="scroll of rage", top_item=dict(name="scroll of rage"))]
    after["inventory"][0]["status"] = "5/8"
    after["evaluation_stats"].update(experience=14, elapsed_turns=3044)
    after["ui"]["texts"] = ["Blinded", "21", "6"]
    return before, targeting, after


class PrismaticDM100ReceiptTests(unittest.TestCase):
    def accept(self, before, targeting, after, other_memory=False):
        p = verified()
        p.update(before)
        d = p.use(before["inventory"][0], "ZAP", "combat", target=1179)
        self.assertEqual(dict(type="item", id="item-0", action="ZAP"), d.action)
        observe_accepted_attack(p, before, d, targeting)
        if other_memory:
            p.dm100_threat["cell"] = 1140
        d = p.cell(1179, "target")
        self.assertEqual(dict(type="cell", cell=1179), d.action)
        observe_accepted_attack(p, targeting, d, after)
        return p

    def test_no_health_bar_does_not_discard_a_tracked_kill_receipt(self):
        p = self.accept(*fixture())
        self.assertIsNone(p.dm100_threat)
        self.assertIsNone(p.damage_pending)
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)

    def test_confirmed_kill_releases_early_lane_gate(self):
        before, targeting, after = fixture()
        p = self.accept(before, targeting, after)
        p.update(after)
        self.assertFalse(exposed_memory(p, after))
        self.assertIsNone(dm100_door_escape(Context(p, after)))

    def test_ambiguous_or_unexecuted_receipts_keep_threat(self):
        for mode in ("no-talent", "unknown", "curse", "unknown-curse",
                     "other-wand", "unspent", "wrong-xp", "long-interval",
                     "level", "floor", "branch", "moved", "survivor",
                     "other-actor", "status", "hidden-ray", "blocked-ray",
                     "effects", "other-memory", "no-xp", "wrong-cell"):
            with self.subTest(mode=mode):
                before, targeting, after = fixture()
                if mode == "no-talent": targeting["hero"]["talents"] = []
                elif mode == "unknown": targeting["inventory"][0]["identified"] = False
                elif mode == "curse": targeting["inventory"][0]["known_cursed"] = True
                elif mode == "unknown-curse": targeting["inventory"][0]["curse_known"] = False
                elif mode == "other-wand": targeting["inventory"][0]["name"] = "wand of lightning"
                elif mode == "unspent": after["inventory"][0]["status"] = "6/8"
                elif mode == "wrong-xp": after["evaluation_stats"]["experience"] = 15
                elif mode == "no-xp": after["evaluation_stats"]["experience"] = 8
                elif mode == "long-interval": after["evaluation_stats"]["elapsed_turns"] = 3046
                elif mode == "level": after["hero"]["level"] = 12
                elif mode == "floor": after["depth"] = 9
                elif mode == "branch": after["branch"] = 1
                elif mode == "moved": after["hero"]["cell"] = 906
                elif mode == "survivor": after["objects"] = copy.deepcopy(before["objects"])
                elif mode == "other-actor": targeting["objects"].append(dict(cell=906, name="skeleton"))
                elif mode == "status": targeting["objects"][0]["status_icons"] = ["burning"]
                elif mode == "hidden-ray": targeting["map"]["cells"][3]["visible"] = False
                elif mode == "blocked-ray": targeting["map"]["cells"][3]["terrain"] = 4
                elif mode == "effects": targeting["map"]["cells"][3]["effects"] = ["fire"]
                elif mode == "wrong-cell": targeting["objects"][0]["cell"] = 1140
                p = self.accept(before, targeting, after, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
