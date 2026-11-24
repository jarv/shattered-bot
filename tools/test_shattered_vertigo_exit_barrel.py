"""Reduced public decision-414 geometry from run 000218, not runtime memory."""
import copy
import unittest

from tools import vertigo_tactics as vertigo
from tools.policy_decision import PlannerStuck
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def encounter():
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=819, hp=17, max_hp=25, buffs=[
        {"name": "hungry"},
        {"name": "vertigo", "description": "Turns of vertigo remaining: 2."}])
    terrain = {783: 1, 784: 8, 785: 1, 818: 1, 819: 19,
               820: 1, 853: 1, 854: 1, 855: 33, 890: 1}
    gas = {784, 818, 819, 820, 854}
    s["map"] = dict(width=35, height=36, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True,
             effects=["A cloud of confusion gas is swirling here."] if c in gas else [],
             **({"trap": "confusion gas trap"} if c == 819 else {}))
        for c, t in terrain.items()])
    s["objects"] = [dict(cell=890, name="scroll of upgrade",
                         top_item=dict(name="scroll of upgrade", identified=True))]
    p = verified()
    p.update(s)
    return s, p


class VertigoExitBarrelTests(unittest.TestCase):
    def test_public_exit_and_solid_barrel_do_not_exhaust_escape(self):
        s, p = encounter()
        before = copy.deepcopy(s)
        try:
            d = vertigo.choose(p, s)
        except PlannerStuck:
            self.fail("A passable exit landing and an impassable barrel must not veto escape")
        self.assertEqual({"type": "cell", "cell": 783}, d.action)
        self.assertEqual([783, 784, 785, 818, 820, 853, 854],
                         p.planner.report["vertigo_response"]["possible_landings"])
        self.assertEqual(before, s)
        self.assertFalse(d.movement_batch)
        self.assertEqual(0, p.vertigo_plan["moves"])
        self.assertIn(890, p.loot)
        self.assertNotIn(890, p.loot_collection_receipts)

    def test_barrel_is_not_a_requested_destination(self):
        s, p = encounter()
        self.assertFalse(vertigo.safe_tile(p, s, 855))
        self.assertNotIn(855, vertigo.landings(p, s, 819) or [])

    def test_each_terrain_mismatch_independently_and_tree_selection(self):
        for normalized in (784, 855, None):
            with self.subTest(normalized=normalized):
                s, p = encounter()
                if normalized is not None:
                    next(t for t in s["map"]["cells"] if t["cell"] == normalized)["terrain"] = 1
                try:
                    d = p.choose(s)
                except PlannerStuck:
                    self.fail("Each recorded terrain mismatch needs its own outcome classification")
                self.assertEqual("vertigo-response", d.controller)
                self.assertEqual({"type": "cell", "cell": 783}, d.action)
                self.assertIn(890, p.loot)

    def test_exit_is_only_admitted_as_random_landing_not_requested_stairs(self):
        s, p = encounter()
        self.assertFalse(vertigo.safe_tile(p, s, 784))
        self.assertIn(784, vertigo.landings(p, s, 819) or [])

    def test_hazards_on_exit_or_other_landings_remain_vetoes(self):
        for mode in ("pit", "active-trap", "toxic", "plant", "unseen",
                     "warning", "fire-buffer", "budget"):
            with self.subTest(mode=mode):
                s, p = encounter()
                t = p.tiles[784]
                if mode == "pit":
                    t["terrain"] = 0
                elif mode == "active-trap":
                    t["trap"] = "dart trap"
                elif mode == "toxic":
                    t["effects"].append("A cloud of toxic gas")
                elif mode == "plant":
                    t["plant"] = "stormvine"
                elif mode == "unseen":
                    t["visible"] = False
                elif mode == "warning":
                    s["danger_cells"] = [784]
                elif mode == "fire-buffer":
                    p.fire_buffer.add(784)
                else:
                    p.vertigo_plan = dict(moves=vertigo.MAX_MOVES, waits=0, stale=0)
                with self.assertRaises(PlannerStuck):
                    vertigo.choose(p, s)


if __name__ == "__main__":
    unittest.main()
