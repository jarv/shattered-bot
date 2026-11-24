"""Reduced D3399-3401 public receipt from recording 000268.

Only targeting and threat bookkeeping is reconstructed, not original memory.
No observation is supplied after an alternative selected action.
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
    b.update(depth=9, branch=0)
    b["hero"].update(cell=806, hp=40, max_hp=65, level=10,
                     hero_class="mage", buffs=[dict(name="starving")],
                     talents=[dict(name="arcane vision", points=1)])
    b["evaluation_stats"] = dict(experience=49, experience_to_level=55,
                                 elapsed_turns=3253)
    b["inventory"] = [dict(id="item-0", name="eldritch staff of frost +3",
        identified=True, curse_known=True, known_cursed=False, equipped=True,
        status="1/6", actions=["ZAP"])]
    groups = {29: [608, 640, 641, 642, 643, 675, 676, 677],
              23: [609], 1: [673], 2: [674, 773, 806],
              32: [706, 707, 708, 740, 741, 774],
              15: [739, 772, 807], 4: [607, 771, 805]}
    b["map"] = dict(width=34, height=44, cells=[
        dict(cell=c, terrain=terrain, visible=True, observed=True, effects=[])
        for terrain, cells in groups.items() for c in cells])
    b["objects"] = [
        dict(name="DM-100", cell=642, health_bar=[16, 21],
             status_icons=["chilled"]),
        dict(name="Chest", cell=673),
        dict(name="dewdrop", cell=806, top_item=dict(name="dewdrop"))]
    b["ui"]["texts"] = ["You are starving!"]
    t = copy.deepcopy(b)
    t["status"] = "targeting"
    a = copy.deepcopy(b)
    a["hero"].update(hp=45, max_hp=70, level=11)
    a["evaluation_stats"].update(experience=0, experience_to_level=60,
                                 elapsed_turns=3254)
    a["objects"] = a["objects"][1:]
    a["inventory"][0]["status"] = "0/6"
    a["ui"]["texts"] = ["15", "6", "Level up!", "You are starving!"]
    return b, t, a


class ArcaneFrostRetirementTests(unittest.TestCase):
    def accept(self, b, t, a, other_memory=False):
        p = verified()
        p.update(b)
        if other_memory:
            p.dm100_threat["cell"] = 640
        d = p.use(b["inventory"][0], "ZAP", "cast", target=642)
        self.assertEqual(dict(type="item", id="item-0", action="ZAP"), d.action)
        observe_accepted_attack(p, b, d, t)
        self.assertIsNotNone(p.damage_pending)
        observe_accepted_attack(p, t, p.cell(642, "target"), a)
        return p

    def test_chilled_frost_levelup_retires_only_matching_lane(self):
        b, t, a = fixture()
        p = self.accept(b, t, a)
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.damage_samples)
        self.assertFalse(p.loot_collection_receipts)
        self.assertIn(673, p.loot)
        p.update(a)
        self.assertFalse(exposed_memory(p, a))
        self.assertIsNone(dm100_door_escape(Context(p, a)))

    def test_ambiguous_receipts_preserve_lane(self):
        for mode in ("no-talent", "wrong-xp", "missing-threshold", "long-interval",
                     "floor", "branch", "moved", "unconsumed", "unknown-charge",
                     "cursed", "unidentified", "other-actor", "survivor",
                     "blocked-ray", "unseen-ray", "effect-ray", "frozen",
                     "other-status", "other-memory", "other-wand"):
            with self.subTest(mode=mode):
                b, t, a = fixture()
                if mode == "no-talent": t["hero"]["talents"] = []
                elif mode == "wrong-xp": a["evaluation_stats"]["experience"] = 1
                elif mode == "missing-threshold": t["evaluation_stats"].pop("experience_to_level")
                elif mode == "long-interval": a["evaluation_stats"]["elapsed_turns"] += 1
                elif mode == "floor": a["depth"] += 1
                elif mode == "branch": a["branch"] += 1
                elif mode == "moved": a["hero"]["cell"] = 807
                elif mode == "unconsumed": a["inventory"][0]["status"] = "1/6"
                elif mode == "unknown-charge": t["inventory"][0]["status"] = "?/6"
                elif mode == "cursed": t["inventory"][0]["known_cursed"] = True
                elif mode == "unidentified": t["inventory"][0]["identified"] = False
                elif mode == "other-actor": t["objects"].append(dict(name="prison guard", cell=674))
                elif mode == "survivor": a["objects"].append(copy.deepcopy(t["objects"][0]))
                elif mode in {"blocked-ray", "unseen-ray", "effect-ray"}:
                    tile = next(ti for ti in t["map"]["cells"] if ti["cell"] == 773)
                    if mode == "blocked-ray": tile["terrain"] = 4
                    elif mode == "unseen-ray": tile["observed"] = False
                    else: tile["effects"] = ["fire"]
                elif mode == "frozen": t["objects"][0]["status_icons"] = ["frozen"]
                elif mode == "other-status": t["objects"][0]["status_icons"] = ["hasted"]
                elif mode == "other-wand":
                    for s in (b, t, a): s["inventory"][0]["name"] = "wand of fireblast"
                p = self.accept(b, t, a, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
