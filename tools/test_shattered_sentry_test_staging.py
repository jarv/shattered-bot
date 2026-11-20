"""Public sentry geometry from run 000005, decisions 640–642 (reduced fixture)."""
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.test_consumable_tactics import potion
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies, safe_test_bank, stage_sentry


def sentry_entrance(known=False):
    s = state()
    s['depth'] = 2
    s['hero'].update(cell=1404, hp=30, max_hp=30, strength=10, buffs=[])
    cells = []
    for y in range(32, 41):
        for x in range(22, 31):
            c = y*43+x
            terrain = 4 if x in {22, 30} or y in {32, 40} else 14
            if y == 33 or y == 34 and x <= 26:
                if 23 <= x <= 29:
                    terrain = 1
            if c == 1404:
                terrain = 6
            if c in {1443, 1703}:
                terrain = 11
            if c == 1445:
                terrain = 25
            if c in {1488, 1531, 1574, 1617}:
                terrain = 26
            cells.append(dict(cell=c, terrain=terrain, visible=True, observed=True))
    s['map'] = dict(width=43, height=52, cells=cells)
    s['objects'] = [
        dict(cell=1443, name='Chest'),
        dict(cell=1703, name='red sentry'),
    ]
    s['inventory'].append(potion('potion of haste' if known else 'bistre potion'))
    p = verified()
    p.update(s)
    return s, p


class SentryTestStagingTests(unittest.TestCase):
    def test_unknown_supply_does_not_stage_at_an_inadmissible_test_bank(self):
        s, p = sentry_entrance()
        self.assertEqual(6, distance(1446, 1703, 43))
        self.assertFalse(safe_test_bank(
            p, s, 1446, distance, neighbors, allow_dry=True, sentry_bank=True))
        self.assertIsNone(prepare_supplies(p, s, [], distance, neighbors))
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.puzzle_probe)
        self.assertIsNone(p.room_journey)
        self.assertIn(1443, p.loot)
        self.assertFalse(p.completed_room_rewards)
        self.assertEqual(0, p.puzzle_revisit_steps['sentry'])

    def test_known_haste_keeps_verified_round_trip_staging(self):
        s, p = sentry_entrance(known=True)
        decision = prepare_supplies(p, s, [], distance, neighbors)
        self.assertEqual(dict(type='cell', cell=1446), decision.action)
        self.assertIsNone(p.room_journey)  # Movement is not protection.

    def test_arrival_does_not_grant_unknown_potion_protection(self):
        s, p = sentry_entrance()
        s['hero']['cell'] = 1446
        p.update(s)
        self.assertIsNone(stage_sentry(p, s, neighbors))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)


if __name__ == '__main__':
    unittest.main()
