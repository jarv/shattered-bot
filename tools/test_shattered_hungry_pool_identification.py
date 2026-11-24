"""Run 000265 D1319/D1369 public reduction, not recorded runtime memory.

Chest 718 and fish 647/681/719 were seen at D1319. D1369 is hungry,
40/40 on clean floor 693, with two unknown singleton potions and intuition.
Earlier strength menus cancelled; that does not test invisibility.
No observations after a changed decision are replayed.
"""
import copy
import unittest

from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.puzzle_supplies import prepare_supplies
from tools.room_supplies import requirements
from tools.runestone_tactics import intuition_menu
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=693, hp=40, max_hp=40,
                     buffs=[dict(name="hungry"), dict(name="barrier")])
    s["map"] = dict(width=35, height=41, cells=[
        dict(cell=693, terrain=1, observed=True, visible=True),
        dict(cell=692, terrain=1, observed=True, visible=True)])
    s["objects"] = []
    s["inventory"] = [
        dict(id="item-12", name="bistre potion", quantity=1,
             identified=False, actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-13", name="magenta potion", quantity=1,
             identified=False, actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-21", name="stone of intuition", quantity=1,
             identified=True, actions=["DROP", "THROW", "USE"])]
    p = verified()
    p.update(s)
    # Reduced public objective cache, not a route or protection receipt.
    p.piranha_rooms[718] = dict(water={647, 681, 719}, collected=False)
    p.loot[718] = dict(cell=718, name="Chest")
    p.intuition_attempts.update({"bistre potion", "magenta potion"})
    return s, p


def proposal(p, s, enemies=()):
    return prepare_supplies(p, s, enemies, distance, neighbors)


class HungryPoolIdentificationTests(unittest.TestCase):
    def test_stationary_pool_hypothesis_survives_unrelated_cancelled_guesses(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertEqual(["pool"], [d.kind for d in requirements(p, s)])
        d = proposal(p, s)
        self.assertIsNotNone(d, "Hungry pool preparation must admit safe intuition")
        self.assertEqual(dict(type="item", id="item-21", action="USE"), d.action)
        self.assertEqual("potion of invisibility", p.intuition_plan["guess"])
        self.assertEqual("bistre potion", p.intuition_plan["item"])
        self.assertEqual(before, s)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.piranha_rooms[718]["collected"])
        self.assertIn(718, p.loot)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.room_attempts)
        # Bounded by room/color, not an invitation to retry the same guess.
        self.assertIsNotNone(proposal(p, s))  # The other untested color.
        self.assertIsNone(proposal(p, s))

    def test_rollback_and_unavailable_menu_keep_honest_receipts(self):
        s, p = fixture()
        tx = Transaction(p)
        self.assertIsNotNone(proposal(p, s))
        tx.rollback()
        self.assertIsNotNone(proposal(p, s))
        p.intuition_plan["stage"] = "guess"
        d = intuition_menu(p, dict(s, ui=dict(texts=[], buttons=[])))
        self.assertEqual(dict(type="back"), d.action)
        self.assertIsNone(p.intuition_plan)
        self.assertFalse(p.piranha_rooms[718]["collected"])
        self.assertFalse(s["inventory"][0]["identified"])

    def test_existing_information_safety_gates_are_preserved(self):
        for case in ("no-stone", "no-use", "tested", "danger", "recent",
                     "damage", "wounded", "starving", "blind", "immune",
                     "invisible", "trap", "effects", "plant", "hidden",
                     "modal", "enemy", "collected"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "no-stone": s["inventory"].pop()
                elif case == "no-use": s["inventory"][-1]["actions"] = ["DROP"]
                elif case == "tested":
                    p.puzzle_guesses.update((3, "pool", c) for c in
                                           ("bistre potion", "magenta potion"))
                elif case == "danger": s["danger_cells"] = [693]
                elif case == "recent": p.recent_threats[692] = dict(cell=692, name="slime")
                elif case == "damage": p.unseen_damage_turns = 1
                elif case == "wounded": s["hero"]["hp"] = 37
                elif case in {"starving", "blind", "immune", "invisible"}:
                    s["hero"]["buffs"].append(dict(name={
                        "immune": "magic immunity"}.get(case, case)))
                elif case in {"trap", "effects", "plant"}:
                    p.tiles[693][case] = ["fire"] if case == "effects" else "hazard"
                elif case == "hidden": p.tiles[693]["visible"] = False
                elif case == "modal": s["modal"] = True
                elif case == "collected": p.piranha_rooms[718]["collected"] = True
                enemies = [dict(cell=692, name="slime")] if case == "enemy" else []
                self.assertIsNone(proposal(p, s, enemies))
                self.assertFalse(p.completed_room_rewards)
                self.assertFalse(p.puzzle_drinks)


if __name__ == "__main__":
    unittest.main()
