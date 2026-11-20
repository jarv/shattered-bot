"""New multi-threat door scouting must honor the accepted-pursuit loss budget."""
import unittest

from tools import multi_enemy_tactics as multi
from tools.pursuit_budget import review_outcome
from tools.test_doorway_and_trickster_commitment import door_room


class ExhaustedDoorwayStagingTests(unittest.TestCase):
    def exhausted(self, p, s):
        # Run 000007, decision 825: four accepted retreats, 11 HP lost,
        # no observed charge gains. These are policy ledger values, not
        # inferred enemy damage or hidden monster identities.
        s["hero"].update(hp=20, max_hp=30)
        p.pursuit_retreat_moves = 4
        p.pursuit_reassessed_move = 0
        p.pursuit_outcome = {"hp_loss":11, "charge_gain":0, "new_sightings":11}
        review_outcome(p, s)
        self.assertTrue(p.pursuit_lure_exhausted)
        self.assertTrue(p.planner.report["pursuit_outcome"]["new_doorway_setups_exhausted"])

    def test_loss_budget_prevents_new_unverified_door_staging(self):
        s, p = door_room()
        self.exhausted(p, s)
        action = multi.doorway_route(p, s, s["objects"], 2)
        self.assertIsNone(action)
        self.assertIsNone(p.multi_door_plan)
        self.assertFalse(p.multi_door_attempts)
        self.assertIsNone(p.doorway_hold)

    def test_unspent_budget_still_allows_observed_door_staging(self):
        s, p = door_room()
        action = multi.doorway_route(p, s, s["objects"], 2)
        self.assertIsNotNone(action)
        self.assertEqual(60, p.multi_door_plan["door"])
        self.assertIsNone(p.doorway_hold)  # Unknown far side is not a hold.

    def test_exhaustion_does_not_cancel_revalidated_existing_route(self):
        s, p = door_room()
        multi.doorway_route(p, s, s["objects"], 2)
        self.exhausted(p, s)
        action = multi.doorway_route(p, s, s["objects"], 2)
        self.assertIsNotNone(action)
        self.assertEqual(60, p.multi_door_plan["door"])

    def test_existing_health_and_hazard_vetoes_still_apply(self):
        for obstruction in ("health", "trap"):
            s, p = door_room()
            multi.doorway_route(p, s, s["objects"], 2)
            self.exhausted(p, s)
            if obstruction == "health":
                s["hero"]["hp"] = 1
            else:
                p.tiles[60]["trap"] = "burning trap"
            self.assertIsNone(multi.doorway_route(p, s, s["objects"], 2))
            self.assertIsNone(p.doorway_hold)


if __name__ == "__main__":
    unittest.main()
