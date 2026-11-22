"""Reduced public receipt from recording 000141, decisions 3681-3683.

Only targeting/receipt memory is reconstructed; this is not a run replay.
"""
import copy
import unittest

from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory
from tools.policy_nodes import dm100_door_escape
from tools.policy_runtime import Context
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    before = state()
    before.update(depth=9, branch=0)
    before["hero"].update(cell=1072, hp=51, max_hp=70, level=11,
                          hero_class="mage", buffs=[],
                          talents=[dict(name="arcane vision", points=1)])
    before["evaluation_stats"] = dict(experience=56, experience_to_level=60,
                                      elapsed_turns=3577)
    before["inventory"] = [dict(id="item-0", name="staff of magic missile +5",
        identified=True, curse_known=True, known_cursed=False, equipped=True,
        status="4/9", actions=["ZAP"])]
    # Projectile ray and the observed cage boundary around the target.
    before["map"] = dict(width=32, height=55, cells=[
        dict(cell=c, terrain=33 if c in {904, 936, 968} else 1,
             visible=True, observed=True, effects=[])
        for c in (1072, 1039, 1038, 1005, 1004, 971, 938, 937,
                  904, 905, 906, 936, 968, 969, 970)])
    before["objects"] = [dict(name="DM-100", cell=937,
                              health_bar=[11, 21], status_icons=[])]
    before["ui"]["texts"] = ["You are crippled!"]
    targeting = copy.deepcopy(before)
    targeting["status"] = "targeting"
    after = copy.deepcopy(before)
    after["objects"] = [dict(name="scroll of lullaby", cell=937,
                              top_item=dict(name="scroll of lullaby"))]
    after["hero"].update(hp=56, max_hp=75, level=12)
    after["evaluation_stats"].update(experience=2, experience_to_level=65,
                                     elapsed_turns=3578)
    after["inventory"][0]["status"] = "3/9"
    after["ui"]["texts"] = ["Level up!", "You picked up: ration of food."]
    for t in after["map"]["cells"]:
        if t["cell"] in {904, 936}:
            t["visible"] = False
            t.pop("effects")
    return before, targeting, after


class ArcaneMissileLevelupTests(unittest.TestCase):
    def accept(self, before, targeting, after, other_memory=False):
        p = verified()
        p.update(before)
        if other_memory:
            p.dm100_threat["cell"] = 517
        d = p.use(before["inventory"][0], "ZAP", "cast", target=937)
        self.assertEqual(dict(type="item", id="item-0", action="ZAP"), d.action)
        observe_accepted_attack(p, before, d, targeting)
        d = p.cell(937, "target")
        self.assertEqual(dict(type="cell", cell=937), d.action)
        observe_accepted_attack(p, targeting, d, after)
        return p

    def test_recorded_levelup_retires_only_matching_lightning_memory(self):
        p = self.accept(*fixture())
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)

    def test_receipt_releases_phantom_veto_without_selecting_a_move(self):
        b, t, a = fixture()
        p = self.accept(b, t, a)
        p.update(a)
        self.assertFalse(exposed_memory(p, a))
        self.assertIsNone(dm100_door_escape(Context(p, a)))

    def test_ambiguous_receipts_preserve_the_threat(self):
        for mode in ("no-talent", "wrong-xp", "missing-threshold", "two-levels",
                     "long-interval", "other-floor", "other-branch", "moved",
                     "unconsumed", "unknown-charge", "cursed", "unidentified",
                     "other-actor", "survivor", "blocked-ray", "unseen-ray",
                     "effect-ray", "status", "other-memory"):
            with self.subTest(mode=mode):
                b, t, a = fixture()
                if mode == "no-talent": t["hero"]["talents"] = []
                elif mode == "wrong-xp": a["evaluation_stats"]["experience"] = 3
                elif mode == "missing-threshold": t["evaluation_stats"].pop("experience_to_level")
                elif mode == "two-levels": a["hero"]["level"] = 13
                elif mode == "long-interval": a["evaluation_stats"]["elapsed_turns"] += 1
                elif mode == "other-floor": a["depth"] += 1
                elif mode == "other-branch": a["branch"] = 1
                elif mode == "moved": a["hero"]["cell"] = 1071
                elif mode == "unconsumed": a["inventory"][0]["status"] = "4/9"
                elif mode == "unknown-charge": t["inventory"][0]["status"] = "?/9"
                elif mode == "cursed": t["inventory"][0]["known_cursed"] = True
                elif mode == "unidentified": t["inventory"][0]["identified"] = False
                elif mode == "other-actor": t["objects"].append(dict(name="skeleton", cell=938))
                elif mode == "survivor": a["objects"].append(copy.deepcopy(t["objects"][0]))
                elif mode in {"blocked-ray", "unseen-ray", "effect-ray"}:
                    tile = next(c for c in t["map"]["cells"] if c["cell"] == 1039)
                    if mode == "blocked-ray": tile["terrain"] = 4
                    elif mode == "unseen-ray": tile["observed"] = False
                    else: tile["effects"] = ["fire"]
                elif mode == "status": t["objects"][0]["status_icons"] = ["hasted"]
                p = self.accept(b, t, a, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
