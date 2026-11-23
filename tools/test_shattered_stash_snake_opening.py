"""Run 000194 D838: defend owned potion retrieval before a new snake lure.

Reduced public geometry and explicitly reconstructed stash bookkeeping from
the played revision 0beaaaae6cbf404166af834317944678ff5405d6.
No observations after an alternative decision are supplied.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=1003, hp=30, max_hp=30, level=3, strength=10,
                     buffs=[{"name": "hungry"}])
    groups = {
        4: [816,817,819,854,856,890,891,893,894,927,931,932,933,
            964,970,1001,1007,1038,1044,1075,1076,1077,1081,1082,
            1083,1084,1114,1151],
        2: [818,855,928,965,1002,1039,1040,1120,1121],
        1: [929,930,967,968,969,1041,1043,1078,1080,1117,1118,1119,1152],
        29: [966,1003,1004,1005,1042,1079,1116,1153,1154,1155,1156,1157,1158],
        5: [892], 20: [1115], 18: [1006],
    }
    s["map"] = dict(width=37, height=39, cells=[
        dict(cell=c, terrain=t, visible=c not in {818,855},
             observed=True, effects=[])
        for t, cells in groups.items() for c in cells])
    s["inventory"][0].update(name="staff of magic missile +2", status="4/6",
                             identified=True, curse_known=True, known_cursed=False)
    s["inventory"].append(dict(id="amber", name="amber potion", identified=False,
                               quantity=1, actions=["DRINK", "DROP", "THROW"]))
    s["objects"] = [
        dict(cell=967, name="crimson potion",
             top_item=dict(name="crimson potion", quantity=1)),
        dict(cell=1156, name="sewer snake", status_icons=[])]
    p = verified()
    p.update(s)
    # D835-836 drops and D838's combat interruption establish this obligation.
    p.potion_stash = dict(depth=2, bank=1079, cell=967, candidate="amber potion",
                          phase="retrieve", steps=6, pending=None,
                          purpose="pre-descent-strength",
                          dropped={"potion of healing":1, "crimson potion":1})
    return s, p


class StashSnakeOpeningTests(unittest.TestCase):
    def test_admitted_magic_defends_retrieval_before_new_optional_lure(self):
        s, p = fixture()
        before, stash = copy.deepcopy(s), copy.deepcopy(p.potion_stash)
        self.assertTrue(p.shot_clear(s, 1156))
        d = p.choose(s)
        self.assertEqual({"type":"item", "id":"item-0", "action":"ZAP"}, d.action,
                         "Owned retrieval must not start a new lure when magic is admitted")
        self.assertEqual(1156, p.target)
        self.assertIsNone(p.ambush_plan)
        self.assertEqual(stash["dropped"], p.potion_stash["dropped"])
        self.assertEqual("retrieve", p.potion_stash["phase"])
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.strength_identified)
        self.assertEqual(before, s)

    def test_without_owned_retrieval_the_recorded_lure_remains(self):
        s, p = fixture()
        p.potion_stash = None
        d = p.choose(s)
        self.assertEqual({"type":"cell", "cell":965}, d.action)
        self.assertEqual("snake: reach ambush doorway", d.reason)

    def test_no_shot_no_charge_or_multiple_foes_do_not_gain_override(self):
        for case in ("wall", "empty", "multiple", "ready"):
            with self.subTest(case=case):
                s, p = fixture()
                if case == "wall":
                    # Intercept the recorded missile ray without inventing a route.
                    p.shot_clear = lambda *_: False
                elif case == "empty":
                    s["inventory"][0]["status"] = "0/6"
                elif case == "multiple":
                    s["objects"].append(dict(cell=1117, name="marsupial rat"))
                else:
                    p.potion_stash["phase"] = "ready"
                d = p.snake_combat(s, s["objects"][1:], "hungry")
                self.assertNotEqual("snake: defend potion retrieval with magic", d.reason)
                self.assertIsNotNone(p.potion_stash)


if __name__ == "__main__":
    unittest.main()
