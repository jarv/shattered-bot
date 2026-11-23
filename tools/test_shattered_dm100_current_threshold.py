"""Reduced public run 163 decision 3528 geometry; no recovered runtime memory."""
import copy
import unittest

from tools.dm100_escape import choose, sight_tiles
from tools.policy_geometry import line_clear, projectile_line_clear
from tools.test_challenge_rules import verified


def threshold_scene():
    # Only recorded tiles are retained. Missing surroundings remain unknown,
    # hence transparent to the conservative cover proof.
    groups = {
        1: (378, 421, 464, 508, 553, 595, 598, 688),
        4: (379, 380, 381, 382, 383, 384, 385, 386, 387,
            599, 600, 601, 602, 645, 687, 689, 690),
        6: (335, 643),
        29: (373, 644),
    }
    hidden = {335, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387,
              602, 690}
    s = dict(scene="GameScene", status="ready", modal=False, depth=8, branch=0,
             hero=dict(cell=643, hp=31, max_hp=65, level=10, strength=13,
                       buffs=[], talents=[]),
             map=dict(width=44, height=29, cells=[
                 dict(cell=c, terrain=t, observed=True, visible=c not in hidden)
                 for t, cells in groups.items() for c in cells]),
             objects=[dict(name="DM-100", cell=373, sleeping=True),
                      dict(name="DM-100", cell=595)],
             inventory=[], ui=dict(texts=[], buttons=[]))
    p = verified()
    p.update(s)
    return s, p


class CurrentThresholdTests(unittest.TestCase):
    def test_step_off_current_door_instead_of_crossing_lightning_room(self):
        s, p = threshold_scene()
        original = copy.deepcopy(s)
        d = choose(p, s, s["objects"])
        self.assertIn(d.action["cell"], (644, 688),
                      "Use the current threshold, not the seven-step exposed route to 335")
        self.assertEqual("retreat", d.intent.value)
        self.assertEqual("bank", p.ranged_plan["stage"])
        self.assertEqual(643, p.ranged_plan["door"])
        self.assertEqual(d.action["cell"], p.ranged_plan["goal"])
        self.assertFalse(p.ranged_plan["armed"])
        self.assertEqual(0, p.ranged_plan["waits"])
        closed = sight_tiles(p, s)
        closed[643] = dict(terrain=5)
        for e in s["objects"]:
            self.assertFalse(line_clear(e["cell"], d.action["cell"], 44, closed))
            self.assertFalse(projectile_line_clear(e["cell"], d.action["cell"], 44, closed))
        self.assertEqual(original, s)
        self.assertFalse(p.loot_collection_receipts)

    def test_bank_requires_fresh_clean_observed_ground(self):
        for hazard in ("trap", "plant", "effects", "unseen", "unobserved", "loot"):
            with self.subTest(hazard=hazard):
                s, p = threshold_scene()
                for c in (644, 688):
                    if hazard in ("unseen", "unobserved"):
                        p.tiles[c]["visible" if hazard == "unseen" else "observed"] = False
                    elif hazard == "loot":
                        p.loot[c] = dict(name="scroll of upgrade", cell=c)
                    else:
                        p.tiles[c][hazard] = ["fire"] if hazard == "effects" else "poison"
                d = choose(p, s, s["objects"])
                self.assertTrue(d is None or d.action.get("cell") not in (644, 688))

    def test_sleeping_second_caster_must_also_be_screened(self):
        s, p = threshold_scene()
        s["objects"][0]["cell"] = 732  # Isolated counterexample, not a later observation.
        p.update(s)
        d = choose(p, s, s["objects"])
        self.assertTrue(d is None or d.action.get("cell") not in (644, 688))

    def test_heap_on_threshold_cannot_prove_door_closure(self):
        s, p = threshold_scene()
        p.loot[643] = dict(name="scroll of upgrade", cell=643)
        d = choose(p, s, s["objects"])
        self.assertTrue(d is None or d.action.get("cell") not in (644, 688))


if __name__ == "__main__":
    unittest.main()
