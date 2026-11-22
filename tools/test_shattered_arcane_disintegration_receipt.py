"""Reduced public inputs at recording 000121 decisions 3907-3909.

Only targeting/receipt memory is reconstructed, not the run's full policy state.
No dispatched inputs or generated observations follow an alternative decision.
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
    before.update(depth=8, branch=0)
    before["hero"].update(cell=935, hp=70, max_hp=70, level=11,
                          hero_class="mage",
                          talents=[dict(name="arcane vision", points=1)],
                          buffs=[dict(name="hungry"), dict(name="magic charge",
                              description="Your wands are boosted to: +3.\n\n"
                                          "Turns of magic charge remaining: 4.")])
    before["inventory"] = [dict(id="item-13", name="wand of disintegration",
        identified=False, curse_known=True, known_cursed=False, equipped=False,
        actions=["DROP", "THROW", "ZAP"])]
    before["evaluation_stats"] = dict(experience=26, elapsed_turns=3799)
    terrain = {935: 1, 936: 1, 904: 1, 905: 1, 873: 1, 874: 1,
               840: 1, 841: 1, 842: 1, 875: 33, 906: 1, 907: 1, 908: 33}
    before["map"] = dict(width=33, height=40, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    before["objects"] = [dict(name="DM-100", cell=874,
                              health_bar=[3, 21], status_icons=[])]
    before["ui"]["texts"] = ["You defeated DM-100.", "You defeated prison guard."]
    targeting = copy.deepcopy(before)
    targeting["status"] = "targeting"
    after = copy.deepcopy(before)
    after["objects"] = []
    after["evaluation_stats"].update(experience=32, elapsed_turns=3800)
    after["hero"]["buffs"] = [dict(name="hungry")]
    for tile in after["map"]["cells"]:
        if tile["cell"] in {840, 841, 842}:
            tile["visible"] = False
    return before, targeting, after


class ArcaneDisintegrationReceiptTests(unittest.TestCase):
    def accept(self, before, targeting, after, other_memory=False):
        p = verified()
        p.update(before)
        if other_memory:
            p.dm100_threat["cell"] = 842
        # Both reconstructed targeting inputs equal the recorded 3907/3908 inputs.
        d = p.use(before["inventory"][0], "ZAP", "cast", target=874)
        self.assertEqual(dict(type="item", id="item-13", action="ZAP"), d.action)
        observe_accepted_attack(p, before, d, targeting)
        d = p.cell(874, "target")
        self.assertEqual(dict(type="cell", cell=874), d.action)
        observe_accepted_attack(p, targeting, d, after)
        return p

    def test_arcane_tracked_survivor_cannot_disappear_into_fog(self):
        p = self.accept(*fixture())
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.damage_samples)  # Not an exact damage sample.
        self.assertFalse(p.loot_collection_receipts)

    def test_phantom_lane_no_longer_vetoes_progress_arbitration(self):
        before, targeting, after = fixture()
        p = self.accept(before, targeting, after)
        p.update(after)
        self.assertFalse(exposed_memory(p, after))
        self.assertIsNone(dm100_door_escape(Context(p, after)))

    def test_ambiguous_receipts_retain_threat(self):
        for mode in ("no-talent", "no-charge", "unknown-range", "out-of-range",
                     "unconsumed-charge", "expiring-charge",
                     "cursed", "unknown-curse", "other-wand", "survivor",
                     "no-xp", "long-interval", "level", "branch", "floor",
                     "other-actor", "status", "other-memory"):
            with self.subTest(mode=mode):
                before, targeting, after = fixture()
                if mode == "no-talent":
                    targeting["hero"]["talents"][0]["points"] = 0
                elif mode == "no-charge": targeting["hero"]["buffs"] = []
                elif mode == "unknown-range":
                    targeting["hero"]["buffs"][1]["description"] = ""
                elif mode == "unconsumed-charge":
                    after["hero"]["buffs"] = copy.deepcopy(targeting["hero"]["buffs"])
                elif mode == "expiring-charge":
                    targeting["hero"]["buffs"][1]["description"] = (
                        "Your wands are boosted to: +3.\n\n"
                        "Turns of magic charge remaining: 1.")
                elif mode == "out-of-range":
                    targeting["hero"]["cell"] = after["hero"]["cell"] = 1300
                elif mode == "cursed": targeting["inventory"][0]["known_cursed"] = True
                elif mode == "unknown-curse": targeting["inventory"][0]["curse_known"] = False
                elif mode == "other-wand": targeting["inventory"][0]["name"] = "wand of lightning"
                elif mode == "survivor": after["objects"] = copy.deepcopy(before["objects"])
                elif mode == "no-xp": after["evaluation_stats"]["experience"] = 26
                elif mode == "long-interval": after["evaluation_stats"]["elapsed_turns"] = 3802
                elif mode == "level": after["hero"]["level"] = 12
                elif mode == "branch": after["branch"] = 1
                elif mode == "floor": after["depth"] = 9
                elif mode == "other-actor":
                    targeting["objects"].append(dict(name="skeleton", cell=840))
                elif mode == "status": targeting["objects"][0]["status_icons"] = ["terror"]
                p = self.accept(before, targeting, after, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
