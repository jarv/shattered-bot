"""Reduced public receipt from recording 000209, decisions 3307-3308.

Only receipt bookkeeping is reconstructed, not original run memory. No game
dispatch or fabricated continuation follows an alternative selection.
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
    b = state()
    b.update(depth=8, branch=0)
    b["hero"].update(cell=1144, hp=12, max_hp=65, level=10,
                     hero_class="mage",
                     buffs=[dict(name="starving"), dict(name="crippled")],
                     talents=[dict(name="arcane vision", points=1)])
    b["evaluation_stats"] = dict(experience=8, experience_to_level=55,
                                  elapsed_turns=3179)
    b["inventory"] = [dict(id="item-0", name="staff of magic missile +3",
        identified=True, curse_known=True, known_cursed=False, equipped=True,
        status="3/7", actions=["ZAP"])]
    # Observed straight ray crosses chasms, which do not stop projectiles.
    b["map"] = dict(width=43, height=32, cells=[
        dict(cell=c, terrain=0 if c in {1141, 1142} else 2,
             visible=True, observed=True, effects=[])
        for c in range(1140, 1145)])
    b["objects"] = [dict(name="DM-100", cell=1140,
                         health_bar=[6, 21], status_icons=[])]
    b["ui"]["texts"] = ["You are crippled!"]
    t = copy.deepcopy(b)
    t["status"] = "targeting"
    a = copy.deepcopy(b)
    a["objects"] = [dict(name="scroll of remove curse", cell=1140,
                         top_item=dict(name="scroll of remove curse"))]
    a["evaluation_stats"].update(experience=14, elapsed_turns=3180)
    a["inventory"][0]["status"] = "2/7"
    a["ui"]["texts"] = ["12", "6", "You are crippled!"]
    return b, t, a


class ArcaneMissileSameLevelTests(unittest.TestCase):
    def accept(self, b, t, a, other_memory=False):
        p = verified()
        p.update(b)
        if other_memory:
            p.dm100_threat["cell"] = 1100
        d = p.use(b["inventory"][0], "ZAP", "cast", target=1140)
        self.assertEqual(d.action, dict(type="item", id="item-0", action="ZAP"))
        observe_accepted_attack(p, b, d, t)
        self.assertIsNotNone(p.damage_pending)
        d = p.cell(1140, "target")
        self.assertEqual(d.action, dict(type="cell", cell=1140))
        observe_accepted_attack(p, t, d, a)
        return p

    def test_recorded_same_level_receipt_retires_phantom_lane(self):
        b, t, a = fixture()
        p = self.accept(b, t, a)
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)
        # Isolated veto probe, not a later recorded selection.
        p.update(a)
        self.assertFalse(exposed_memory(p, a))
        self.assertIsNone(dm100_door_escape(Context(p, a)))

    def test_ambiguous_receipts_keep_memory(self):
        for mode in ("no-talent", "wrong-xp", "missing-threshold", "threshold-change",
                     "long-interval", "floor", "branch", "moved", "unconsumed",
                     "unknown-charge", "cursed", "unidentified", "other-actor",
                     "survivor", "blocked-ray", "unseen-ray", "effect-ray",
                     "status", "other-memory"):
            with self.subTest(mode=mode):
                b, t, a = fixture()
                if mode == "no-talent": t["hero"]["talents"] = []
                elif mode == "wrong-xp": a["evaluation_stats"]["experience"] = 13
                elif mode == "missing-threshold": t["evaluation_stats"].pop("experience_to_level")
                elif mode == "threshold-change": a["evaluation_stats"]["experience_to_level"] = 60
                elif mode == "long-interval": a["evaluation_stats"]["elapsed_turns"] += 1
                elif mode == "floor": a["depth"] += 1
                elif mode == "branch": a["branch"] += 1
                elif mode == "moved": a["hero"]["cell"] = 1143
                elif mode == "unconsumed": a["inventory"][0]["status"] = "3/7"
                elif mode == "unknown-charge": t["inventory"][0]["status"] = "?/7"
                elif mode == "cursed": t["inventory"][0]["known_cursed"] = True
                elif mode == "unidentified": t["inventory"][0]["identified"] = False
                elif mode == "other-actor": t["objects"].append(dict(name="prison guard", cell=1186))
                elif mode == "survivor": a["objects"].append(copy.deepcopy(t["objects"][0]))
                elif mode in {"blocked-ray", "unseen-ray", "effect-ray"}:
                    tile = t["map"]["cells"][2]
                    if mode == "blocked-ray": tile["terrain"] = 4
                    elif mode == "unseen-ray": tile["observed"] = False
                    else: tile["effects"] = ["fire"]
                elif mode == "status": t["objects"][0]["status_icons"] = ["hasted"]
                p = self.accept(b, t, a, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
