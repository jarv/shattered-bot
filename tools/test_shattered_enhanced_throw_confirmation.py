"""Reduced public inputs from recording 000142, decision 3161.

Only the selecting attack and its pending target are reconstructed. The later
targeting fixture is an isolated UI contract probe, not a gameplay replay.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Finished
from tools.test_survival_bot import state


WARNING = ("If the last thrown weapon in your enhanced thrown weapon set breaks, "
           "the set will be permanently lost. Are you sure you want to throw it?")


def fixture():
    s = state()
    s.update(depth=7, branch=0)
    s["hero"].update(cell=455, hp=65, max_hp=65, level=10, strength=13)
    s["inventory"] = [
        dict(id="item-0", name="staff of magic missile +3", status="0/7",
             equipped=True, actions=["ZAP"]),
        dict(id="item-13", name="shocking shuriken +1", quantity=1,
             identified=True, curse_known=True, known_cursed=False,
             actions=["DROP", "THROW"],
             description="This set of _tier-2_ thrown weapons deals _5-10 damage_ "
             "and requires _10 strength_ to use. This set of thrown weapons "
             "has _1/8_ uses left before one breaks.")]
    s["map"] = dict(width=30, height=38, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in ((275, 2), (305, 2), (335, 2), (365, 20),
                     (395, 1), (425, 1), (455, 1))])
    s["objects"] = [dict(name="crazy thief", cell=275,
                          health_bar=[11, 16], status_icons=[])]
    p = MagePolicy()
    p.update(s)
    d = p.best_attack(s, s["objects"][0])
    assert d.action == dict(type="item", id="item-13", action="THROW")
    s.update(status="menu", modal=True)
    s["ui"] = dict(texts=["Shocking Shuriken +1", WARNING, "Yes", "No"],
                   buttons=[dict(id="button-0", label="Yes"),
                            dict(id="button-1", label="No")])
    return p, s


class EnhancedThrowConfirmationTests(unittest.TestCase):
    def test_recorded_warning_continues_selected_attack_once(self):
        p, s = fixture()
        try:
            d = p.menu(s)
        except Finished:
            self.fail("The selected enhanced throw must handle its exact durability warning")
        self.assertEqual(dict(type="button", id="button-0"), d.action)
        self.assertEqual(275, p.target)
        self.assertEqual(1, s["inventory"][1]["quantity"])
        with self.assertRaises(Finished):
            p.menu(s)  # No repeated confirmation using an unrelated last input.

    def test_isolated_targeting_contract_preserves_observed_cell(self):
        p, s = fixture()
        try:
            p.menu(s)
        except Finished:
            self.fail("Durability confirmation must not block the targeting contract")
        s = copy.deepcopy(s)
        s.update(status="targeting", modal=False)
        p.challenges_verified = True
        p.verified_challenges = p.enabled_challenges
        d = p.choose(s)
        self.assertEqual(dict(type="cell", cell=275), d.action)
        self.assertIsNone(p.target)

    def test_unknown_or_unplanned_confirmation_still_fails_closed(self):
        for mode in ("warning", "title", "buttons", "no-target", "no-input",
                     "other-action", "missing-item", "cursed", "blocked-ray",
                     "missing-enemy"):
            with self.subTest(mode=mode):
                p, s = fixture()
                if mode == "warning": s["ui"]["texts"][1] = "Destroy this item?"
                elif mode == "title": s["ui"]["texts"][0] = "Other weapon"
                elif mode == "buttons": s["ui"]["buttons"].pop()
                elif mode == "no-target": p.target = None
                elif mode == "no-input": p.last_decision = None
                elif mode == "other-action": p.last_decision.action["action"] = "DROP"
                elif mode == "missing-item": s["inventory"].pop()
                elif mode == "cursed": s["inventory"][1]["known_cursed"] = True
                elif mode == "blocked-ray": p.tiles[365]["terrain"] = 4
                else: s["objects"] = []
                with self.assertRaises(Finished):
                    p.menu(s)


if __name__ == "__main__":
    unittest.main()
