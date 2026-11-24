"""Condensed public warning/loot geometry from recording 224, decision 2147."""
import unittest

from tools.artifact_tactics import use_artifact
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["depth"] = 6
    s["hero"].update(cell=737, hp=50, max_hp=50,
                     buffs=[{"name": "hungry"}, {"name": "foresight"}])
    # Before the move, 781 was rendered ordinary floor, not a known trap.
    s["map"] = dict(width=45, height=38, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
        for c in (693, 737, 781, 825)])
    s["inventory"].append(dict(
        id="talisman", name="talisman of foresight", equipped=True,
        known_cursed=False, status="100%", actions=["SCRY", "UNEQUIP"]))
    s["objects"] = [dict(cell=825, name="turquoise potion",
                         top_item=dict(name="turquoise potion", identified=False))]
    p = verified()
    p.update(s)
    p.shop_visited_floors.add(6)
    return p, s


class ForesightLootScryTests(unittest.TestCase):
    def test_warning_admits_information_before_loot_movement(self):
        p, s = fixture()
        d = use_artifact(p, s, [])
        self.assertIsNotNone(d, "A public foresight warning should prompt a bounded loot-route scry")
        self.assertEqual(dict(type="item", id="talisman", action="SCRY"), d.action)
        self.assertEqual(825, p.target)
        self.assertIn(825, p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.puzzle_drinks)
        self.assertNotIn("trap", p.tiles[781])
        self.assertIsNone(use_artifact(p, s, []), "Do not repeatedly scan the same target")

    def test_full_selector_scans_before_ordinary_collection(self):
        p, s = fixture()
        d = p.choose(s)
        self.assertEqual("SCRY", d.action.get("action"))

    def test_scan_requires_quiet_warning_visible_loot_and_budget(self):
        for condition in ("warning-absent", "enemy", "memory", "danger", "modal",
                          "low-charge", "unseen", "sale", "budget", "probe"):
            with self.subTest(condition=condition):
                p, s = fixture()
                enemies = []
                if condition == "warning-absent": s["hero"]["buffs"] = []
                if condition == "enemy": enemies = [{"name": "skeleton", "cell": 693}]
                if condition == "memory": p.recent_threats[693] = {"name": "skeleton"}
                if condition == "danger": s["danger_cells"] = [737]
                if condition == "modal": s["modal"] = True
                if condition == "low-charge": s["inventory"][-1]["status"] = "4%"
                if condition == "unseen": p.tiles[825]["visible"] = False
                if condition == "sale": p.loot[825]["for_sale"] = True
                if condition == "budget": p.scry_attempts.update({(6, 100), (6, 101)})
                if condition == "probe": p.puzzle_probe = {"kind": "frost"}
                self.assertIsNone(use_artifact(p, s, enemies))


if __name__ == "__main__":
    unittest.main()
