"""Reduced public D2879 facts from run 000219, not recorded runtime memory.

The door, HP, silver potion and remote fire/upgrade were publicly observed.
This tests recovery arbitration only; no changed input is dispatched.
"""
import copy
import unittest

from tools.policy_nodes import preparation_and_recovery
from tools.policy_runtime import Context
from tools.priority_resources import targets
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=7, branch=0)
    s["hero"].update(cell=541, hp=49, max_hp=55, buffs=[])
    terrain = {496: 1, 497: 1, 498: 1, 540: 4, 541: 6, 542: 4,
               584: 4, 585: 1, 586: 1, 596: 1, 599: 14}
    s["map"] = dict(width=44, height=38, cells=[
        dict(cell=c, terrain=t, observed=True, visible=c not in {596, 599})
        for c, t in terrain.items()])
    s["inventory"] += [
        dict(id="silver", name="silver potion", identified=False,
             quantity=1, actions=["DRINK", "THROW", "DROP"]),
        dict(id="fruit", name="blandfruit", actions=["EAT", "DROP"])]
    p = verified()
    p.update(s)
    # Remembered effects and reward from D2838–2861, not fresh visibility.
    p.tiles[596]["effects"] = [
        "A wall of dense bright green fire is here, seemingly caused by magic. "
        "You'll need to use something to extinguish it."]
    p.loot[599] = dict(cell=599, name="scroll of upgrade",
                       top_item=dict(name="scroll of upgrade", identified=True))
    p.strength_identified = True  # Public strength drink already occurred on D1148.
    p.puzzle_drinks.add((7, "charcoal potion"))  # D2841, revealed as mind vision.
    return s, p


class RequiredFrostRecoveryTests(unittest.TestCase):
    def test_regular_recovery_funds_required_test_threshold_before_exploration(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertNotIn(599, p.paths(s))
        self.assertEqual(24, p.recovery_limit(s, False))
        self.assertEqual(.95, p.recovery_target(s),
                         "Required frost preparation needs more than ordinary 65% recovery")
        d = preparation_and_recovery(Context(p, s))
        self.assertIsNotNone(d, "Do not explore while affordable preparation recovery is excluded")
        self.assertEqual(dict(type="wait"), d.action)
        self.assertEqual("recover: natural healing", d.reason)
        self.assertEqual(before, s)
        self.assertIn(599, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.room_journey)

    def test_full_selector_chooses_recovery_not_an_unknown_drink(self):
        s, p = fixture()
        d = p.choose(s)
        self.assertEqual("preparation-and-recovery", d.controller)
        self.assertEqual(dict(type="wait"), d.action)
        self.assertIn(599, targets(p))
        self.assertFalse(p.loot_collection_receipts)

    def test_no_extra_wait_budget_or_unsafe_drink_is_created(self):
        for case in ("spent", "hungry", "starving", "poison", "active", "full"):
            with self.subTest(case=case):
                s, p = fixture()
                enemies = []
                if case == "spent":
                    p.natural_healing_waits = p.rests = 24
                elif case in {"hungry", "starving", "poison"}:
                    s["hero"]["buffs"] = [dict(name=case)]
                elif case == "active":
                    enemies = [dict(cell=497, name="skeleton")]
                elif case == "full":
                    s["hero"]["hp"] = 53
                self.assertIsNone(preparation_and_recovery(
                    Context(p, s, enemies=enemies, active=enemies)))
                self.assertIn(599, targets(p))
                self.assertIsNone(p.puzzle_probe)

    def test_only_unfinished_mandatory_fire_preparation_raises_target(self):
        for case in ("no-reward", "food-only", "no-fire", "no-candidate",
                     "already-tested", "no-drink", "unrelated-reward", "known-frost"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "no-reward": p.loot.clear()
                elif case == "food-only":
                    p.loot[599] = dict(cell=599, name="pasty", top_item=dict(name="pasty"))
                elif case == "no-fire": p.tiles[596]["effects"] = []
                elif case == "no-candidate": s["inventory"].pop(1)
                elif case == "already-tested": p.puzzle_drinks.add((7, "silver potion"))
                elif case == "no-drink": s["inventory"][1]["actions"] = ["THROW"]
                elif case == "unrelated-reward":
                    p.loot[1500] = p.loot.pop(599)
                elif case == "known-frost":
                    s["inventory"].append(dict(name="potion of frost", actions=["THROW"]))
                self.assertEqual(.65, p.recovery_target(s))


if __name__ == "__main__":
    unittest.main()
