"""Run 12: an infeasible test bank must not disable all floor potion work."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.policy_decision import Finished
from tools.puzzle_supplies import prepare_supplies


def flight_approach():
    # Public geometry reduction of decision 557. Visibility is NOT expanded
    # when evaluating another bank. Unlisted cells remain unknown.
    s, _ = arena()
    s['depth'] = 2
    s['hero'].update(cell=1391, hp=30, max_hp=30, buffs=[])
    groups = {
        (4, False): [1168,1170,1178,1179,1180,1181,1182,1204,1206,1240,1242,
                     1276,1278,1279,1280,1312,1348,1349,1350,1351,1352,1389,
                     1393,1394,1395,1396,1397,1433,1469,1505,1541,1648],
        (2, False): [1169,1205],
        (4, True): [1173,1177,1209,1213,1245,1249,1281,1285,1321,1353,1357,
                    1390,1392,1425,1461,1497,1533,1569,1577,1605,1613,
                    1641,1642,1643,1644,1645,1646,1647],
        (1, True): [1174,1210,1212,1246,1248,1282,1318,1320,1355,1356],
        (29, True): [1175,1211,1247,1283,1319],
        (20, True): [1176,1354],
        (1, False): [1241,1277,1314,1315,1316],
        (18, True): [1284],
        (19, False): [1313],
        (5, True): [1317],
        (6, True): [1391],
        (14, True): [1426,1500,1502,1536,1538,1606,1612],
        (0, True): [1427,1428,1429,1462,1463,1464,1465,1466,1498,1499,
                    1501,1503,1534,1535,1537,1539,1540,1570,1571,1572,
                    1573,1574,1575,1576,1607,1608,1609,1610,1611],
        (0, False): [1430,1431,1467,1468,1504],
        (14, False): [1432],
    }
    s['map'] = {'width':36, 'height':48, 'cells':[
        {'cell':c, 'terrain':terrain, 'visible':visible, 'observed':True}
        for (terrain,visible), cells in groups.items() for c in cells]}
    s['inventory'] = [
        {'id':str(n), 'name':name, 'quantity':1, 'identified':False,
         'actions':['DROP','THROW','DRINK']}
        for n,name in enumerate(('charcoal potion','azure potion','jade potion'))]
    s['objects'] = [{'cell':c,'name':'Locked chest'} for c in (1500,1502,1536,1538)]
    s['objects'] += [{'cell':c,'name':'golden key','top_item':{'name':'golden key'}}
                     for c in (1432,1606,1612)]
    p = verified()
    p.update(s)
    return s,p


class PotionStashBankTests(unittest.TestCase):
    def test_infeasible_nearest_bank_yields_to_verified_stash_bank(self):
        s,p = flight_approach()
        before = copy.deepcopy(s)
        try:
            d = prepare_supplies(p,s,[],distance,neighbors)
        except Finished as error:
            self.fail('Bank selection reached an unprepared frost-stash veto: '+error.reason)
        self.assertIsNotNone(d)
        self.assertEqual({'type':'cell','cell':1355}, d.action)
        self.assertIsNone(p.potion_stash)  # Staging is not a drop receipt.
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.deferred_room_controllers)
        self.assertEqual(before,s)  # No manufactured visibility or identity.

    def test_no_stash_bank_declines_without_drinking_or_global_deferral(self):
        s,p = flight_approach()
        # No DROP support is a real preflight veto, not permission to drink.
        for item in s['inventory']:
            item['actions'].remove('DROP')
        try:
            d = prepare_supplies(p,s,[],distance,neighbors)
        except Finished as error:
            self.fail('Unstarted stash must be declined locally: '+error.reason)
        self.assertIsNone(d)
        self.assertIsNone(p.potion_stash)
        self.assertFalse(p.puzzle_drinks)
        self.assertFalse(p.deferred_room_controllers)


if __name__ == '__main__':
    unittest.main()
