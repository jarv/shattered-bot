"""Reduced run 186 public evidence, not recovered original runtime memory.

D362/D392 saw fire and upgrade 1222. D371 spent the puzzle meal;
D372-375 guessed frost for golden (incorrect), D391 drank golden.
D689 retained hungry 30/30 on door 589, bistre x2 and usable intuition.
Only the remembered fire/reward and evidenced attempt keys are retained here.
No changed decision is followed by a fabricated gameplay observation.
"""
import copy
import unittest

from tools.policy_geometry import distance, neighbors
from tools.policy_runtime import Transaction
from tools.priority_resources import choose, targets
from tools.puzzle_supplies import prepare_supplies
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=589, hp=30, max_hp=30, strength=11,
                     buffs=[dict(name="hungry")])
    s["map"] = dict(width=38, height=54, cells=[
        dict(cell=589, terrain=6, visible=True, observed=True),
        dict(cell=1184, terrain=1, visible=False, observed=True),
        dict(cell=1222, terrain=14, visible=False, observed=True)])
    s["inventory"] = [
        dict(id="item-7", name="bistre potion x2", quantity=2,
             identified=False, actions=["DRINK", "DROP", "THROW"]),
        dict(id="item-15", name="stone of intuition", quantity=1,
             identified=True, actions=["USE", "DROP", "THROW"]),
        dict(id="item-5", name="pasty", quantity=1, actions=["EAT"])]
    p = verified()
    p.update(s)
    # Reduced cache from earlier public sightings, not current visible effects.
    p.tiles[1184]["effects"] = [
        "A wall of dense bright green fire is here, seemingly caused by magic. "
        "You'll need to use something to extinguish it."]
    p.loot[1222] = dict(cell=1222, name="scroll of upgrade",
                        top_item=dict(name="scroll of upgrade", identified=True))
    p.room_attempts.add((2, "puzzle-meal"))
    p.puzzle_guesses.add((2, "frost", "golden potion"))
    p.puzzle_drinks.add((2, "golden potion"))
    return s, p


class HungryFrostIdentificationTests(unittest.TestCase):
    def test_blocked_upgrade_allows_stationary_information_before_hunger_veto(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertNotIn(1222, p.paths(s))
        decision = choose(p, s, [])
        self.assertIsNotNone(decision, "Hunger must not exclude carried frost intuition")
        self.assertEqual(dict(type="item", id="item-15", action="USE"), decision.action)
        self.assertEqual("potion of frost", p.intuition_plan["guess"])
        self.assertEqual("bistre potion x2", p.intuition_plan["item"])
        self.assertEqual(before, s)
        self.assertIn(1222, targets(p))
        self.assertFalse(p.completed_room_rewards)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.potion_stash)
        # Repeated input without a new public receipt cannot drink, eat or retry.
        self.assertIsNone(prepare_supplies(p, s, [], distance, neighbors))
        self.assertFalse(s["inventory"][0]["identified"])

    def test_rejection_rolls_back_only_the_new_hypothesis(self):
        s, p = fixture()
        tx = Transaction(p)
        self.assertIsNotNone(choose(p, s, []))
        tx.rollback()
        self.assertNotIn((2, "frost", "bistre potion"), p.puzzle_guesses)
        self.assertIn((2, "frost", "golden potion"), p.puzzle_guesses)
        self.assertIn(1222, targets(p))
        self.assertIsNotNone(choose(p, s, []))

    def test_unsafe_or_unavailable_information_remains_excluded(self):
        for case in ("no-stone", "no-use", "tested", "danger", "recent", "damage",
                     "wounded", "blind", "starving", "immune", "invisible",
                     "trap", "effects", "unseen", "deferred", "enemy"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "no-stone": s["inventory"].pop(1)
                elif case == "no-use": s["inventory"][1]["actions"] = ["DROP"]
                elif case == "tested": p.puzzle_guesses.add((2, "frost", "bistre potion"))
                elif case == "danger": s["danger_cells"] = [589]
                elif case == "recent": p.recent_threats[590] = dict(cell=590, name="marsupial rat")
                elif case == "damage": p.unseen_damage_turns = 1
                elif case == "wounded": s["hero"]["hp"] = 20
                elif case in {"blind", "starving", "immune", "invisible"}:
                    s["hero"]["buffs"].append(dict(name={
                        "immune": "magic immunity", "invisible": "invisible"
                    }.get(case, case)))
                elif case == "trap": p.tiles[589]["trap"] = "toxic vent"
                elif case == "effects": p.tiles[589]["effects"] = ["fire"]
                elif case == "unseen": p.tiles[589]["visible"] = False
                elif case == "deferred":
                    from tools.objective_planning import exhaust_preparation
                    exhaust_preparation(p,s,"test: preparation exhausted")
                enemies = [dict(cell=590, name="marsupial rat")] if case == "enemy" else []
                self.assertIsNone(prepare_supplies(p, s, enemies, distance, neighbors))
                self.assertIn(1222, targets(p))
                self.assertFalse(p.completed_room_rewards)


if __name__ == "__main__":
    unittest.main()
