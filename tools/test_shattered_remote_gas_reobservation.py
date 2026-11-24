"""Observation-only gas approach from public run 223 terminal geometry."""
import copy
import unittest
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.puzzle_supplies import Demand, revisit_flight_room, prepare_supplies
from tools.policy_geometry import distance, neighbors


def fixture():
    s = state()
    s["hero"].update(cell=474, hp=25, max_hp=25)
    # The previously admitted bank and gas reward route. The hero has since
    # left sight of it; no invisibility, purity, identity or pickup is inferred.
    terrain = {474:29, 473:14, 475:14, 436:14, 437:14, 438:14,
               510:14, 511:14, 512:14, 402:14, 365:6,
               327:20, 290:19, 254:1, 218:1}
    # Ordinary remote corridor; each next step is publicly visible.
    terrain.update({c:14 for c in (513,514,515,516,517)})
    s["hero"]["cell"] = 517
    s["inventory"].extend([
        dict(id="bistre",name="bistre potion",quantity=1,identified=False,
             actions=["DRINK","DROP","THROW"]),
        dict(id="golden",name="golden potion",quantity=1,identified=False,
             actions=["DRINK","DROP","THROW"])])
    s["map"] = dict(width=37,height=35,cells=[
        dict(cell=c,terrain=t,observed=True,visible=c>=513,
             effects=["A greenish cloud of toxic gas is swirling here."] if c in {327,290,254,218} else [])
        for c,t in terrain.items()])
    p = verified()
    p.update(s)
    p.loot[218] = dict(cell=218,name="Chest")
    return p,s


class RemoteGasReobservationTests(unittest.TestCase):
    def test_supply_controller_hands_off_to_reobservation_not_exhaustion(self):
        p,s=fixture()
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(d)
        self.assertEqual(474,d.navigation_route[-1])
        self.assertEqual("gas",p.planner.report["puzzle_revisit"]["kind"])
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)

    def test_unknown_gas_supply_has_observation_only_return(self):
        p,s=fixture()
        before=copy.deepcopy(s)
        d=revisit_flight_room(p,s,Demand("gas","potion of purity",327),distance)
        self.assertIsNotNone(d, "A remote gas reward must not lose its ordinary approach")
        self.assertEqual("cell",d.action["type"])
        self.assertNotIn(d.action["cell"],{327,290,254,218})
        self.assertEqual(474,d.navigation_route[-1])
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.completed_room_rewards)
        self.assertEqual(before,s)

    def test_threats_and_exhausted_observation_budget_still_decline(self):
        for threat in (True,False):
            p,s=fixture()
            if threat:p.recent_threats[516]={"name":"marsupial rat","cell":516}
            else:p.puzzle_revisit_steps["gas"]=48
            self.assertIsNone(revisit_flight_room(p,s,Demand("gas","potion of purity",327),distance))

    def test_other_hazards_do_not_become_gas_approaches(self):
        p,s=fixture()
        p.tiles[512]["effects"]=["Fire"]
        self.assertIsNone(revisit_flight_room(p,s,Demand("gas","potion of purity",327),distance))


if __name__ == "__main__":
    unittest.main()
