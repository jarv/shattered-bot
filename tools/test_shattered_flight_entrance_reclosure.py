"""Condensed public inputs 654–657 from run 000033, not runtime memory.

The synthetic initial memory reproduces the earlier selected helper inputs.
Stop at 657, the first changed decision; nothing is dispatched or replayed.
"""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies
from tools.room_tactics import plan_journey


def entrance(opened=True):
    s = state()
    s['depth'] = 3
    s['hero'].update(cell=977 if opened else 978, hp=25, max_hp=25,
                     strength=10, buffs=[])
    # Public neighborhood of the door and reward, with unrelated floor omitted.
    groups = {
        (4, False): [676,677,678,679,680,719,805,848,891,1025,1063,1106,
                     1142,1149,1185,1190,1191,1192,1193,1194,1195,1228],
        (1, False): [720,721,722,723,763,849,1107,1151,1186,1229,1230,
                     1231,1232,1234,1239,1240],
        (5, False): [762,1143,1233], (29, False): [764,765,807,1235,1236,1237],
        (20, False): [806,1150,1238], (2, False): [808],
        (4, True): [843,844,845,846,886,895,929,934,938,972,981,1015,1020,
                    1024,1058,1101,1144,1145,1146,1196],
        (29, True): [850,893,936,979,1016,1022,1065,1108,1109,1110,1111],
        (15, True): [851,894],
        (0, True): [887,888,889,890,930,931,932,933,973,974,975,976,
                    1017,1018,1019,1059,1060,1061,1062,1102,1103,1104],
        (1, True): [892,935,937,978,980,1021,1023,1064,1066,1067,1068,1152,1153,1154],
        (6, True): [977], (0, False): [1187,1188,1189], (5, True): [1197],
    }
    closed_visible = {
        676,677,678,679,680,719,720,721,722,723,762,763,764,765,805,806,807,
        808,848,849,850,851,891,892,893,894,895,934,935,936,937,938,977,978,
        979,980,981,1020,1021,1022,1023,1024,1063,1064,1065,1066,1067,1068,
        1106,1107,1108,1109,1110,1111,1149,1150,1151,1152,1153,1154,
        1192,1193,1194,1195,1196,1197,
    }
    s['map'] = dict(width=43, height=48, cells=[
        dict(cell=c, terrain=5 if c == 977 and not opened else t,
             visible=v if opened else c in closed_visible, observed=True)
        for (t,v), cells in groups.items() for c in cells])
    s['objects'] = [dict(cell=1016, name='Chest')] if opened else []
    s['inventory'] += [
        dict(id=str(i), name=name, quantity=1, identified=name.startswith('potion of'),
             actions=['DROP','THROW','DRINK'])
        for i,name in enumerate(('ivory potion','turquoise potion','amber potion',
                                 'potion of liquid flame','indigo potion'))]
    return s


class FlightEntranceReclosureTests(unittest.TestCase):
    def select(self, p, s):
        d = prepare_supplies(p, s, [], distance, neighbors)
        p.last_decision = d
        return d

    def scouted(self):
        p = verified()
        # Validate the three earlier helper selections against the recording.
        for opened, target in ((True,978), (False,977), (True,978)):
            s = entrance(opened)
            p.update(s)
            self.assertEqual(dict(type='cell', cell=target), self.select(p,s).action)
        s = entrance(False)
        p.update(s)
        return p,s

    def test_reclosure_proceeds_to_inventory_protection_not_another_scout(self):
        p,s = self.scouted()
        d = self.select(p,s)  # First changed selection: decision 657.
        self.assertIsNotNone(p.potion_stash,
                             'A visibly entered flight entrance must not restart scouting')
        self.assertEqual('drop', p.potion_stash['phase'])
        self.assertNotEqual(dict(type='cell', cell=977), d.action)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertIn(1016, p.loot)
        self.assertFalse(p.completed_room_rewards)

    def test_receipt_is_not_levitation_or_collection(self):
        p,s = self.scouted()
        # Isolated alternative on copies: only one potion needs no stash.
        p = copy.deepcopy(p)
        s = copy.deepcopy(s)
        s['inventory'] = [s['inventory'][0], s['inventory'][1]]
        d = self.select(p,s)
        self.assertEqual('DRINK', d.action.get('action'))
        self.assertEqual('flight', p.room_journey.kind)
        self.assertEqual(1016, p.room_journey.route[-1])
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)
        self.assertIn(1016, p.loot)
        self.assertFalse(p.completed_room_rewards)

    def test_unexecuted_opening_does_not_supply_receipt(self):
        p = verified()
        p.update(entrance(True))
        s = entrance(False)
        p.update(s)
        self.assertEqual(dict(type='cell', cell=977), self.select(p,s).action)
        p.update(s)  # No arrival, no open terrain.
        self.assertEqual(dict(type='cell', cell=977), self.select(p,s).action)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)

    def test_receipt_is_floor_local_and_branch_specific(self):
        p,s = self.scouted()
        s['branch'] = 1
        p.update(s)
        self.assertEqual(dict(type='cell', cell=977), self.select(p,s).action)
        p.memory.reset_floor(978)
        self.assertFalse(getattr(p, 'flight_entrance_receipts', set()))
        self.assertIsNone(getattr(p, 'flight_entrance_pending', None))

    def test_new_door_hazard_does_not_become_admitted_by_receipt(self):
        p,s = self.scouted()
        next(t for t in s['map']['cells'] if t['cell'] == 977)['trap'] = 'shocking trap'
        p.update(s)
        self.assertIsNone(plan_journey(p,s,[],neighbors,probe_kind='flight',plan_only=True))
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)


if __name__ == '__main__':
    unittest.main()
