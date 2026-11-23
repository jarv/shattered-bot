"""Reduced run 000214 public door history, not a gameplay replay.

Door 746 was crossed at D4490 and is closed both before and after the
D4586 victory. Visits below are fixture bookkeeping, not saved memory.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import Finished
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=10, boss_health_text=None)
    s["hero"].update(cell=874, hp=26, max_hp=80, level=13,
                     buffs=[{"name": "starving"}])
    # Observed post-victory pocket and approach to the reused door.
    floor = {746, 778, 810, 842, 874}
    s["map"] = dict(width=32, height=32, cells=[
        dict(cell=c, terrain=5 if c == 746 else 1 if c in floor else 4,
             visible=True, observed=True, effects=[])
        for c in sorted({n for c in floor for n in
                         (c-33, c-32, c-31, c-1, c, c+1, c+31, c+32, c+33)})])
    s["ui"]["texts"] = ['Tengu: "Free at last..."']
    p = MagePolicy()
    p.challenges_verified = True
    p.update(copy.deepcopy(s))
    p.visits[746] = 3
    p.exhausted.update(floor)
    p.boss_strategies["tengu"].engaged = True
    return s, p


class TenguVictoryDoorTests(unittest.TestCase):
    def test_final_victory_rearms_reused_door_before_exhaustion(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        try:
            d = p.choose(s)
        except Finished:
            d = None
        self.assertIsNotNone(d, "Final victory must not hide the visited closed exit door")
        self.assertEqual({"type": "cell", "cell": 842}, d.action)
        self.assertEqual("explore: unopened door", d.reason)
        self.assertEqual([746], p.exploration_report(s, p.paths(s))["unopened_doors"])
        self.assertEqual(3, p.visits[746])
        self.assertEqual(before, s)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)

    def test_not_rearmed_again_after_receipt(self):
        s, p = fixture()
        boss = p.boss_strategies["tengu"]
        self.assertTrue(boss.victory(p, s))
        self.assertIn(746, p.changed_door_cells)
        p.defeated_bosses.add("tengu")
        opened = copy.deepcopy(s)
        opened["hero"]["cell"] = 746
        next(t for t in opened["map"]["cells"] if t["cell"] == 746)["terrain"] = 6
        p.update(opened)
        p.update(s)  # Ordinary reclosure is not a second victory obligation.
        self.assertTrue(boss.victory(p, s))
        self.assertNotIn(746, p.changed_door_cells)

    def test_reward_pickup_still_precedes_reopened_route(self):
        s, p = fixture()
        s["hero"]["cell"] = 842
        s["objects"] = [dict(cell=874, name="Tengu's mask",
                            top_item={"name": "Tengu's mask", "quantity": 1})]
        d = p.choose(s)
        self.assertEqual({"type": "cell", "cell": 874}, d.action)
        self.assertIn("loot:", d.reason)
        self.assertIn(874, p.loot)
        self.assertFalse(p.loot_collection_receipts)

    def test_requires_final_evidence_and_fresh_observed_closed_door(self):
        for change in ("no-victory", "boss-bar", "unseen", "unobserved", "open"):
            s, p = fixture()
            door = next(t for t in s["map"]["cells"] if t["cell"] == 746)
            if change == "no-victory":
                s["ui"]["texts"] = ["Tengu: Let's make this interesting..."]
            elif change == "boss-bar":
                s["boss_health_text"] = "2/200"
            elif change == "unseen":
                door["visible"] = False
            elif change == "unobserved":
                door["observed"] = False
            else:
                door["terrain"] = 6
            p.update(s)
            p.boss_strategies["tengu"].victory(p, s)
            self.assertNotIn(746, p.changed_door_cells, change)

    def test_rearming_does_not_remove_hazard_or_failed_movement_veto(self):
        for change in ("gas", "blocked"):
            s, p = fixture()
            if change == "gas":
                next(t for t in s["map"]["cells"] if t["cell"] == 746)["effects"] = [
                    "A greenish cloud of toxic gas is swirling here."]
            else:
                p.blocked.add(746)
                p.failed_moves[746] = 2
            p.update(s)
            p.boss_strategies["tengu"].victory(p, s)
            self.assertNotIn(746, p.paths(s))
            self.assertNotIn(746, p.exploration_report(s, p.paths(s))["unopened_doors"])


if __name__ == "__main__":
    unittest.main()
