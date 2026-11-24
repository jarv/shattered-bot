"""Run 000258 D1604: reduced public confusion escape, not runtime replay.

The only purity dose was publicly picked up at D1574. No room demand had yet
reserved it. D1604 had a fully checked escape, but drank that dose instead.
No observations following a changed selection are supplied.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools import vertigo_tactics as vertigo


def fixture():
    s = state()
    s.update(depth=4, branch=0, danger_cells=[], objects=[])
    s["hero"].update(cell=1538, hp=35, max_hp=45, buffs=[
        {"name": "starving"},
        {"name": "vertigo", "description": "Turns of vertigo remaining: 2."}])
    terrain = {1495: 4, 1496: 1, 1497: 2, 1537: 1, 1538: 19,
               1539: 15, 1579: 1, 1580: 2, 1581: 2}
    gas = {1496, 1537, 1538, 1539, 1580}
    s["map"] = dict(width=42, height=41, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True,
             effects=["A cloud of confusion gas is swirling here."] if c in gas else [],
             **({"trap": "confusion gas trap"} if c == 1538 else {}))
        for c, t in terrain.items()])
    s["inventory"] = [dict(id="item-12", name="potion of purity",
                           identified=True, quantity=1, actions=["DRINK", "DROP", "THROW"])]
    p = verified()
    p.update(s)
    return s, p


class ConfusionLastPurityTests(unittest.TestCase):
    def test_last_dose_yields_to_existing_all_direction_escape(self):
        for full in (False, True):
            s, p = fixture()
            before = copy.deepcopy(s)
            self.assertEqual([1538, 1497], vertigo.exit_route(p, s, True))
            d = p.choose(s) if full else vertigo.choose(p, s)
            self.assertEqual(dict(type="cell", cell=1497), d.action,
                             "A checked confusion escape should preserve the last purity dose")
            if full:
                self.assertEqual("vertigo-response", d.controller)
            self.assertFalse(d.movement_batch)
            self.assertEqual(before, s)
            self.assertFalse(p.room_supply_spent_elsewhere)
            self.assertFalse(p.completed_room_rewards)
            self.assertFalse(p.loot_collection_receipts)
            self.assertIsNone(p.room_journey)
            self.assertEqual(0, p.vertigo_plan["moves"])

    def test_unsafe_landings_still_use_emergency_purity(self):
        for hazard in ("pit", "toxic", "plant", "unseen", "warning", "trap"):
            s, p = fixture()
            t = p.tiles[1539]
            if hazard == "pit": t["terrain"] = 0
            elif hazard == "toxic": t["effects"] = ["A cloud of toxic gas"]
            elif hazard == "plant": t["plant"] = "stormvine"
            elif hazard == "unseen": t["visible"] = False
            elif hazard == "warning": s["danger_cells"] = [1539]
            else: t.update(terrain=18, trap="dart trap")
            with self.subTest(hazard=hazard):
                d = vertigo.choose(p, s)
                self.assertEqual(dict(type="item", id="item-12", action="DRINK"), d.action)
                self.assertEqual("emergency", d.potion_purpose)
                self.assertFalse(p.room_supply_spent_elsewhere)

    def test_low_health_threat_and_exhausted_budget_keep_emergency_rescue(self):
        for case in ("health", "threat", "budget"):
            s, p = fixture()
            if case == "health": s["hero"]["hp"] = 10
            elif case == "threat":
                p.recent_threats[1497] = dict(cell=1497, name="gnoll scout")
            else: p.vertigo_plan = dict(moves=vertigo.MAX_MOVES, waits=0, stale=0)
            with self.subTest(case=case):
                self.assertEqual("item", vertigo.choose(p, s).action["type"])

    def test_spare_dose_keeps_existing_prompt_rescue(self):
        s, p = fixture()
        s["inventory"][0]["quantity"] = 2
        self.assertEqual("item", vertigo.choose(p, s).action["type"])

    def test_unknown_color_never_becomes_purity_rescue(self):
        s, p = fixture()
        s["inventory"][0].update(name="golden potion", identified=False)
        p.tiles[1539]["terrain"] = 0
        with self.assertRaises(vertigo.PlannerStuck):
            vertigo.choose(p, s)


if __name__ == "__main__":
    unittest.main()
