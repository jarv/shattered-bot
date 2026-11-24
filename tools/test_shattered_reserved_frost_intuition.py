"""Reduced D626/D665 public facts from run 000215, not runtime memory.

The fire cache is reconstructed from D626. D665 selected intuition at
24/30 HP while hungry, but D668 confirmed strength instead of frost.
No observation following a changed hypothesis is simulated.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.runestone_tactics import prepare_intuition
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=933, hp=24, max_hp=30, strength=10,
                     buffs=[dict(name="hungry")])
    s["map"] = dict(width=37, height=30, cells=[
        dict(cell=933, terrain=2, visible=True, observed=True, effects=[]),
        dict(cell=226, terrain=14, visible=False, observed=True)])
    s["inventory"] = [
        dict(id="item-7", name="crimson potion", quantity=1, identified=False,
             actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-12", name="stone of intuition", quantity=1,
             identified=True, actions=["DROP", "THROW", "USE"]),
        dict(id="food", name="ration of food x2", quantity=2, actions=["EAT"])]
    s["objects"] = []
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    # Minimal remembered public fire observation, not a fresh safety receipt.
    p.tiles[226]["effects"] = [
        "A wall of dense bright green fire is here, seemingly caused by magic. "
        "You'll need to use something to extinguish it."]
    return s, p


class ReservedFrostIntuitionTests(unittest.TestCase):
    def test_already_admitted_information_uses_the_blocking_room_hypothesis(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        d = prepare_intuition(p, s)
        self.assertEqual(dict(type="item", id="item-12", action="USE"), d.action)
        self.assertEqual("potion of frost", p.intuition_plan["guess"])
        self.assertEqual("crimson potion", p.intuition_plan["item"])
        self.assertEqual(before, s)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.room_attempts)  # No meal or drink is authorized.
        self.assertIsNone(prepare_intuition(p, s))

    def test_explicit_guess_is_not_rewritten(self):
        s, p = fixture()
        prepare_intuition(p, s, guess="potion of strength",
                          candidate=s["inventory"][0])
        self.assertEqual("potion of strength", p.intuition_plan["guess"])

    def test_no_missing_frost_keeps_the_original_default(self):
        for case in ("no-fire", "held-frost"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "no-fire":
                    p.tiles[226].pop("effects")
                else:
                    s["inventory"].append(dict(name="potion of frost",
                        quantity=1, identified=True, actions=["THROW"]))
                prepare_intuition(p, s)
                self.assertEqual("potion of strength", p.intuition_plan["guess"])

    def test_scroll_default_is_unchanged(self):
        s, p = fixture()
        s["inventory"][0].update(name="scroll of BERKANAN", actions=["READ"])
        prepare_intuition(p, s)
        self.assertEqual("scroll of recharging", p.intuition_plan["guess"])


if __name__ == "__main__":
    unittest.main()
