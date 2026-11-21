"""Run 67 decision 1445: reduced public shot lines, not recovered memory."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.unit_strategies import choose


def fixture():
    s = state()
    s.update(depth=4, branch=0)
    s["hero"].update(cell=791, hp=40, max_hp=40, strength=11)
    terrain = {791: 1, 758: 29, 757: 1, 722: 2, 688: 1,
               653: 1, 619: 18, 584: 18, 550: 18}
    s["map"] = dict(width=34, height=40, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[],
             **({"trap": "burning trap"} if t == 18 else {}))
        for c, t in terrain.items()])
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +3", status="3/7",
        identified=True, curse_known=True, known_cursed=False, equipped=True,
        description="Each bolt deals _5-14 damage_.",
        actions=["ZAP", "IMBUE", "THROW"])]
    s["objects"] = [
        dict(cell=550, name="swarm of flies"),
        dict(cell=758, name="mimic", health_bar=[15, 21])]
    p = verified()
    p.update(s)
    return s, p


class ContactMimicBeforeDistantFlyTests(unittest.TestCase):
    def test_contact_mimic_gets_admitted_magic_before_remote_fly(self):
        s, p = fixture()
        before = copy.deepcopy(s)
        self.assertTrue(p.shot_clear(s, 550))
        self.assertTrue(p.shot_clear(s, 758))
        action = choose(p, s, s["objects"])
        self.assertEqual("ZAP", action.action.get("action"))
        self.assertEqual(758, p.target,
                         "Do not spend remaining bolts on a distant fly while a mimic bites")
        self.assertEqual(before, s)
        self.assertFalse(p.cleared_floors)

    def test_no_physical_fallback_when_magic_unavailable(self):
        s, p = fixture()
        s["inventory"][0].update(status="0/7", actions=["THROW", "IMBUE"])
        action = choose(p, s, s["objects"])
        self.assertFalse(action and action.action.get("action") == "THROW")
        self.assertNotEqual(758, p.planner.report.get("unit_target"))

    def test_contact_fly_retains_existing_priority(self):
        s, p = fixture()
        s["objects"][0]["cell"] = 757
        action = choose(p, s, s["objects"])
        self.assertEqual("ZAP", action.action.get("action"))
        self.assertEqual(757, p.target)

    def test_sleeping_or_distant_mimic_is_not_promoted(self):
        for change in ("sleeping", "distant"):
            s, p = fixture()
            if change == "sleeping":
                s["objects"][1]["sleeping"] = True
            else:
                s["objects"][1]["cell"] = 688
            choose(p, s, s["objects"])
            self.assertEqual(550, p.planner.report["unit_target"])


if __name__ == "__main__":
    unittest.main()
