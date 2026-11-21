"""Reduced public pool route from 000074, decisions 3068-3070; no dispatch."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import neighbors
from tools.policy_decision import TacticalBlocked
from tools.room_tactics import Journey


ROUTE = [1125, 1162, 1198, 1234, 1270, 1307, 1345]
WATER = {1231,1232,1233,1234,1235,1236,1237,
         1268,1269,1270,1271,1272,1273,1274,
         1305,1306,1307,1308,1309,1310,1311,
         1342,1343,1344,1346,1347,1348}


def fixture():
    s = state()
    s['depth'] = 7
    s['hero'].update(cell=1125, hp=54, max_hp=60, strength=13,
                     buffs=[dict(name='invisible', description='Turns of invisibility remaining: 20.')])
    groups = {29: WATER | {1125}, 6: {1162},
              14: set(range(1194,1201)), 11: {1345}}
    s['map'] = dict(width=37, height=39, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for t, cells in groups.items() for c in sorted(cells)])
    s['objects'] = [dict(cell=c, name='giant piranha') for c in (1272,1274)]
    s['objects'].append(dict(cell=1345, name='Chest'))
    p = verified()
    p.update(s)
    p.room_journey = Journey('pool', ROUTE.copy(), 7)
    return s, p


def blocked_snapshot():
    s, p = fixture()
    # Validate the two earlier selected waypoints against the recording.
    for target, duration in ((1162,19), (1198,18)):
        d = p.room_journey.advance(p, s, [], neighbors)
        assert d.action == dict(type='cell', cell=target)
        s = copy.deepcopy(s)
        s['hero']['cell'] = target
        s['hero']['buffs'][0]['description'] = f'Turns of invisibility remaining: {duration}.'
        if target == 1198:
            s['objects'].insert(0, dict(cell=1234, name='giant piranha'))
            next(t for t in s['map']['cells'] if t['cell']==1162)['terrain'] = 5
        p.update(s)
    return s, p


class PoolOccupiedWaypointTests(unittest.TestCase):
    def test_visible_fish_does_not_discard_budgeted_chest_journey(self):
        s, p = blocked_snapshot()
        try:
            d = p.room_journey.advance(p, s, [], neighbors)
        except TacticalBlocked:
            self.fail('A visible, equal-length protected bypass must preserve the chest journey')
        self.assertEqual(dict(type='cell', cell=1235), d.action)
        self.assertEqual([1125,1162,1198,1235,1271,1307,1345], p.room_journey.route)
        self.assertEqual('outbound', p.room_journey.stage)
        self.assertFalse(p.piranha_rooms[1345]['collected'])
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.loot_collection_receipts)
        self.assertIn(1345, p.loot)

    def test_no_fresh_safe_bypass_keeps_original_blocker(self):
        for change in ('hidden', 'trap', 'plant', 'effects', 'blocked', 'occupied'):
            with self.subTest(change=change):
                s, p = blocked_snapshot()
                for cell in (1235,1236):
                    tile = next(t for t in s['map']['cells'] if t['cell']==cell)
                    if change == 'hidden':
                        tile['visible'] = False
                    elif change == 'blocked':
                        p.blocked.add(cell)
                    elif change == 'occupied':
                        s['objects'].append(dict(cell=cell, name='giant piranha'))
                    else:
                        tile[change] = ['cloud of toxic gas'] if change == 'effects' else 'hazard'
                    # Isolated selecting input, not a gameplay replay.
                    p.tiles[cell].update(tile)
                with self.assertRaises(TacticalBlocked):
                    p.room_journey.advance(p, s, [], neighbors)
                self.assertEqual(ROUTE, p.room_journey.route)
                self.assertFalse(p.piranha_rooms[1345]['collected'])

    def test_insufficient_protection_returns_without_bypassing(self):
        s, p = blocked_snapshot()
        s['hero']['buffs'][0]['description'] = 'Turns of invisibility remaining: 6.'
        d = p.room_journey.advance(p, s, [], neighbors)
        self.assertEqual(dict(type='cell', cell=1162), d.action)
        self.assertEqual('return', p.room_journey.stage)
        self.assertEqual(ROUTE, p.room_journey.route)

    def test_non_piranha_occupant_is_not_reinterpreted(self):
        s, p = blocked_snapshot()
        s['objects'][0]['name'] = 'animated statue'
        with self.assertRaises(TacticalBlocked):
            p.room_journey.advance(p, s, [], neighbors)
        self.assertEqual(ROUTE, p.room_journey.route)

    def test_warning_keeps_return_priority(self):
        s, p = blocked_snapshot()
        s['danger_cells'] = [1233]
        d = p.room_journey.advance(p, s, [], neighbors)
        self.assertEqual(dict(type='cell', cell=1162), d.action)
        self.assertEqual('return', p.room_journey.stage)
        self.assertEqual(ROUTE, p.room_journey.route)


if __name__ == '__main__':
    unittest.main()
