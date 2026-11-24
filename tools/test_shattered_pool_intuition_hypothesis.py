"""Run 000232 D1155/D1157 public reduction, not recorded runtime memory.

The remembered unfinished chest comes from D855 and the D1270 report.
No observations after a changed guess are replayed.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.runestone_tactics import prepare_intuition, intuition_menu
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=666, hp=32, max_hp=35, buffs=[])
    s["map"] = dict(width=33, height=40, cells=[
        dict(cell=666, terrain=1, observed=True, visible=True)])
    s["objects"] = []
    s["inventory"] = [
        dict(id="item-7", name="azure potion", quantity=1, identified=False,
             actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-8", name="jade potion", quantity=1, identified=False,
             actions=["DROP", "THROW", "DRINK"]),
        dict(id="item-15", name="stone of intuition", quantity=1,
             identified=True, actions=["DROP", "THROW", "USE"])]
    p = MagePolicy()
    p.challenges_verified = True
    p.update(s)
    # Reduced public objective cache, not a fresh route or safety certificate.
    p.piranha_rooms[1173] = dict(water={1172, 1174}, collected=False)
    return s, p


class PoolIntuitionHypothesisTests(unittest.TestCase):
    def test_admitted_information_targets_unfinished_pool_not_unavailable_strength(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        d = prepare_intuition(p, s)
        self.assertEqual(dict(type="item", id="item-15", action="USE"), d.action)
        self.assertEqual("potion of invisibility", p.intuition_plan["guess"])
        self.assertEqual("azure potion", p.intuition_plan["item"])
        # D1156 is unchanged: select the same publicly rendered item.
        item_menu = dict(s, ui=dict(texts=["Select an item"], buttons=[
            dict(id="button-0", label="azure potion"),
            dict(id="button-1", label="jade potion")]))
        self.assertEqual(dict(type="button", id="button-0"),
                         intuition_menu(p, item_menu).action)
        # D1157 offered invisibility, but not the default strength hypothesis.
        modal = dict(s, ui=dict(texts=["Azure Potion"], buttons=[
            dict(id="button-3", label="Potion of Invisibility")]))
        d = intuition_menu(p, modal)
        self.assertEqual(dict(type="button", id="button-3"), d.action)
        self.assertEqual("confirm", p.intuition_plan["stage"])
        self.assertEqual(before, s)
        self.assertFalse(p.piranha_rooms[1173]["collected"])
        self.assertFalse(p.completed_room_rewards)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(s["inventory"][0]["identified"])

    def test_no_missing_pool_preserves_default(self):
        for case in ("collected", "absent", "carried"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "collected":
                    p.piranha_rooms[1173]["collected"] = True
                elif case == "absent":
                    p.piranha_rooms.clear()
                else:
                    s["inventory"].append(dict(name="potion of invisibility",
                        quantity=1, identified=True, actions=["DRINK"]))
                prepare_intuition(p, s)
                self.assertEqual("potion of strength", p.intuition_plan["guess"])

    def test_explicit_hypothesis_and_scroll_default_are_unchanged(self):
        s, p = fixture()
        prepare_intuition(p, s, guess="potion of haste", candidate=s["inventory"][0])
        self.assertEqual("potion of haste", p.intuition_plan["guess"])
        s, p = fixture()
        s["inventory"] = [dict(id="scroll", name="scroll of GYFU",
            identified=False, actions=["READ"]), s["inventory"][-1]]
        prepare_intuition(p, s)
        self.assertEqual("scroll of recharging", p.intuition_plan["guess"])

    def test_missing_rendered_guess_still_cancels(self):
        s, p = fixture()
        prepare_intuition(p, s)
        p.intuition_plan["stage"] = "guess"
        d = intuition_menu(p, dict(s, ui=dict(texts=[], buttons=[])))
        self.assertEqual(dict(type="back"), d.action)
        self.assertIsNone(p.intuition_plan)


if __name__ == "__main__":
    unittest.main()
