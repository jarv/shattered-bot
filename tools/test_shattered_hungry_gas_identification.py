"""Run 153 D330: reduced public facts, not recovered runtime memory.

D244 observed toxic gas and chest 250; D330 retains amber and intuition,
hungry at 25/25 on open door 1044. D324's failed guess was strength,
not purity. Geometry is reduced; no subsequent game observation is invented.
"""
import copy
import unittest

from tools.descent_potions import begin
from tools.policy_decision import PlannerStuck
from tools.policy_runtime import Transaction
from tools.room_supplies import requirements
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=1, branch=0)
    s["hero"].update(cell=1044, hp=25, max_hp=25, strength=10,
                     buffs=[dict(name="hungry")])
    s["map"] = dict(width=41, height=33, cells=[
        dict(cell=1044, terrain=6, observed=True, visible=True),
        dict(cell=1004, terrain=1, observed=True, visible=True),
        dict(cell=1085, terrain=4, observed=True, visible=True),
        dict(cell=330, terrain=15, observed=True, visible=False),
        dict(cell=250, terrain=19, trap="toxic vent", observed=True, visible=False)])
    s["inventory"] = [
        dict(id="amber", name="amber potion", quantity=1, identified=False,
             actions=["DRINK", "DROP", "THROW"]),
        dict(id="intuition", name="stone of intuition", quantity=1,
             identified=True, actions=["USE", "DROP", "THROW"]),
        dict(id="food", name="ration of food x2", quantity=2, actions=["EAT"])]
    s["objects"] = []
    p = verified()
    p.update(s)
    # Reduced remembered public evidence. Terminal report independently names
    # gas 330 as its missing-supply blocker; this is not a live effect receipt.
    p.tiles[330]["effects"] = ["A greenish cloud of toxic gas is swirling here."]
    p.loot[250] = dict(cell=250, name="Chest")
    p.intuition_attempts.add("amber potion")  # Earlier strength hypothesis failed.
    return s, p


def proposal(p, s):
    try:
        return begin(p, s)
    except PlannerStuck:
        return None


class HungryGasIdentificationTests(unittest.TestCase):
    def test_missing_purity_can_use_carried_intuition_without_eating_or_drinking(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertEqual(["gas"], [d.kind for d in requirements(p, s)])
        action = proposal(p, s)
        self.assertIsNotNone(action, "Hunger must not veto safe nonconsumptive gas identification")
        self.assertEqual(dict(type="item", id="intuition", action="USE"), action.action)
        self.assertEqual("potion of purity", p.intuition_plan["guess"])
        self.assertEqual("amber potion", p.intuition_plan["item"])
        self.assertEqual(before, s)
        self.assertFalse(p.strength_identified)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        self.assertIn(250, p.loot)
        self.assertNotIn((1, "puzzle-meal"), p.room_attempts)
        self.assertIsNone(proposal(p, s))  # Same room/color hypothesis is bounded.

    def test_rollback_restores_hypothesis_not_collection(self):
        s, p = fixture()
        tx = Transaction(p)
        self.assertIsNotNone(proposal(p, s))
        tx.rollback()
        self.assertIsNotNone(proposal(p, s))
        self.assertIn(250, p.loot)

    def test_unsafe_or_unavailable_identification_retains_terminal_gate(self):
        for case in ("no-stone", "no-use", "tested", "danger", "recent",
                     "wounded", "blind", "immune", "invisible", "trap", "effects"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "no-stone": s["inventory"].pop(1)
                elif case == "no-use": s["inventory"][1]["actions"] = ["DROP"]
                elif case == "tested": p.puzzle_guesses.add((1, "gas", "amber potion"))
                elif case == "danger": s["danger_cells"] = [1044]
                elif case == "recent": p.recent_threats[1004] = dict(cell=1004, name="marsupial rat")
                elif case == "wounded": s["hero"]["hp"] = 10
                elif case in {"blind", "immune", "invisible"}:
                    s["hero"]["buffs"].append(dict(name={
                        "blind": "blind", "immune": "magic immunity",
                        "invisible": "invisible"}[case]))
                elif case == "trap": p.tiles[1044]["trap"] = "toxic vent"
                else: p.tiles[1044]["effects"] = ["fire"]
                self.assertIsNone(proposal(p, s))
                self.assertIn(250, p.loot)
                self.assertFalse(p.completed_room_rewards)


if __name__ == "__main__":
    unittest.main()
