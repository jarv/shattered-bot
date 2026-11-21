"""Run 72: closed ordinary transit doors hid observed crystal-room rewards.

Reduced public geometry, not original runtime memory or gameplay replay.
"""
import unittest

from tools.policy_geometry import neighbors
from tools.room_tactics import crystal_choice
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["hero"].update(cell=400, hp=25, max_hp=25)
    # Recorded ordinary entrance 403, crystal locks 444/520 and potion lane.
    terrain = {400:29, 401:1, 402:1, 403:5, 404:1, 405:1,
               442:1, 443:1, 444:31, 445:14, 446:14, 447:14,
               448:14, 449:14, 480:1, 481:1, 518:1, 519:1,
               520:31, 521:14}
    s["map"] = dict(width=38, height=37, cells=[
        dict(cell=c, terrain=t, visible=False, observed=True)
        for c,t in terrain.items()])
    s["keys"] = [dict(name="Crystal key", depth=1, quantity=1)]
    s["objects"] = [dict(cell=448, name="potion of liquid flame",
                        top_item=dict(name="potion of liquid flame",
                                      identified=True, quantity=1))]
    p = verified()
    p.update(s)
    return s,p


class RemoteCrystalChoiceTests(unittest.TestCase):
    def test_closed_transit_door_does_not_erase_observed_branch_value(self):
        s,p = fixture()
        d = crystal_choice(p,s,[],neighbors)
        self.assertIsNotNone(d, "Ordinary closed transit must not hide known rewards")
        self.assertEqual(dict(type="cell",cell=401), d.action)
        self.assertIn(444,p.crystal_spend_plans)
        self.assertEqual(1,p.keys["crystal"])
        self.assertIn(448,p.loot)
        self.assertFalse(p.resolved_crystal_alternatives)
        self.assertFalse(p.strength_identified)

    def test_hazard_or_unobserved_reward_does_not_authorize_choice(self):
        for kind in ("trap","effect","blocked","no-reward","threat"):
            with self.subTest(kind=kind):
                s,p = fixture()
                if kind=="trap": p.tiles[403]["trap"]="poison dart trap"
                elif kind=="effect": p.tiles[403]["effects"]=["magical fire"]
                elif kind=="blocked": p.blocked.add(403)
                elif kind=="no-reward": p.loot.clear()
                else: p.recent_threats[402]=dict(cell=402,name="rat")
                self.assertIsNone(crystal_choice(p,s,[],neighbors))
                self.assertFalse(p.crystal_spend_plans)
                self.assertEqual(1,p.keys["crystal"])


if __name__ == "__main__":
    unittest.main()
