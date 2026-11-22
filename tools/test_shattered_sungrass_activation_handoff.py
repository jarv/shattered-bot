"""Run 99 decisions 937–939: garden activation must not lose seed recovery."""
import copy
import unittest

from tools.seed_strategies import choose as seed
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    # Minimal public-input derivative, not a reconstruction of run memory.
    s = state()
    s["hero"].update(hp=16, max_hp=30, buffs=[{"name": "hungry"}])
    s["evaluation_stats"] = {"elapsed_turns": 920}
    s["inventory"] += [
        {"id": "food", "name": "ration of food", "actions": ["EAT"]},
        {"id": "sungrass", "name": "seed of sungrass", "actions": ["PLANT"]},
    ]
    p = verified()
    return s, p


def activated():
    s, p = fixture()
    first = p.choose(s)
    assert first.action == {"type": "item", "id": "sungrass", "action": "PLANT"}
    assert first.reason == "seed: prepare sungrass with verified setup time margin"
    tile = next(t for t in s["map"]["cells"] if t["cell"] == 24)
    s["inventory"] = [i for i in s["inventory"] if i["id"] != "sungrass"]
    tile["plant"] = "sungrass"
    s["evaluation_stats"]["elapsed_turns"] = 921
    second = p.choose(s)
    assert second.action == {"type": "cell", "cell": 24}
    assert second.reason == "garden: activate publicly observed Sungrass for efficient recovery"
    assert p.seed_plan["stage"] == "activate"
    tile.pop("plant")
    s["hero"]["buffs"].append({"name": "herbal healing"})
    s["evaluation_stats"]["elapsed_turns"] = 922
    return s, p


class SungrassActivationHandoffTests(unittest.TestCase):
    def test_garden_activation_resumes_bounded_seed_recovery(self):
        s, p = activated()
        action = p.choose(s)
        self.assertEqual({"type": "wait"}, action.action)
        self.assertEqual("seed: sheltered sungrass recovery", action.reason)
        self.assertEqual("recover", p.seed_plan["stage"])
        self.assertEqual(1, p.seed_plan["waits"])
        self.assertEqual(922, p.seed_plan["heal_progress_at"])

    def test_activation_is_not_inferred_from_missing_plant(self):
        s, p = activated()
        s["hero"]["buffs"] = [{"name": "hungry"}]
        p.update(s)
        self.assertIsNone(seed(p, s, []))
        self.assertIsNone(p.seed_plan)

    def test_same_cell_and_existing_recovery_gates_remain_required(self):
        for scenario in ("moved", "threat", "starving", "poison", "full", "budget", "danger"):
            with self.subTest(scenario=scenario):
                s, p = activated()
                if scenario == "moved":
                    s["hero"]["cell"] = 25
                elif scenario in ("starving", "poison"):
                    s["hero"]["buffs"].append({"name": scenario})
                elif scenario == "full":
                    s["hero"]["hp"] = 30
                elif scenario == "budget":
                    p.seed_plan["waits"] = 80
                elif scenario == "danger":
                    s["danger_cells"] = [24]
                p.update(s)
                if scenario == "threat":
                    p.recent_threats[26] = {"cell": 26, "name": "gnoll scout"}
                self.assertIsNone(seed(p, s, []))

    def test_recovered_handoff_still_stops_on_no_health_progress(self):
        s, p = activated()
        p.update(s)
        self.assertIsNotNone(seed(p, s, []))
        later = copy.deepcopy(s)
        later["evaluation_stats"]["elapsed_turns"] = 929
        self.assertIsNone(seed(p, later, []))
        self.assertIsNone(p.seed_plan)


if __name__ == "__main__":
    unittest.main()
