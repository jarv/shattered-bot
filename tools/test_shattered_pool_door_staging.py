"""Reduced public geometry: a closed entrance is the only budgeted pool bank."""
import unittest
from tools.test_challenge_systems import ready, item
from tools.puzzle_supplies import stage_known_pool, Demand
from tools.policy_geometry import distance, neighbors


class PoolDoorStagingTests(unittest.TestCase):
    def fixture(self):
        s,p=ready()
        s['map'].update(width=45,height=38)
        s['hero'].update(cell=1242,hp=25,max_hp=25)
        potion=item('potion of invisibility','DRINK')
        potion['identified']=True
        s['inventory'].append(potion)
        # Recorded entrance 1287, dry far bank 1331, water corridor,
        # and chest 1601. Two ordinary retreat directions outside the door.
        cells={1242:1,1243:1,1287:5,1331:14,1375:29,1419:29,
               1463:29,1509:29,1555:29,1601:11}
        area={n for c in cells for n in neighbors(c,45,38)}|cells.keys()
        s['map']['cells']=[dict(cell=c,terrain=cells.get(c,4),visible=True,
                               observed=True,name='Floor') for c in area]
        s['objects']=[dict(cell=1601,name='Chest')]
        p.update(s)
        p.piranha_rooms={1601:dict(water={1375,1419,1463,1509,1555},collected=False)}
        p.room_blocked={1331,1375,1419,1463,1509,1555,1601}
        p.room_skipped=set(p.room_blocked)
        return s,p,potion

    def stage(self,s,p,potion):
        return stage_known_pool(p,s,Demand('pool','potion of invisibility',1601),
                                potion,distance,neighbors)

    def test_open_budgeted_entrance_before_spending_known_invisibility(self):
        s,p,potion=self.fixture()
        d=self.stage(s,p,potion)
        self.assertIsNotNone(d)
        self.assertEqual({'type':'cell','cell':1287},d.action)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.piranha_rooms[1601]['collected'])

    def test_unknown_or_hazardous_door_is_not_a_known_potion_bank(self):
        for change in ('unknown','trap','blocked'):
            with self.subTest(change=change):
                s,p,potion=self.fixture()
                if change=='unknown':potion['identified']=False
                elif change=='trap':p.tiles[1287]['trap']={'name':'trap'}
                else:p.room_blocked.add(1287)
                self.assertIsNone(self.stage(s,p,potion))

    def test_open_door_can_stage_known_invisibility_with_same_budget(self):
        s,p,potion=self.fixture()
        p.tiles[1287]['terrain']=6
        d=self.stage(s,p,potion)
        self.assertIsNotNone(d)
        self.assertEqual({'type':'cell','cell':1287},d.action)
        self.assertIsNone(p.room_journey)
        s['hero']['cell']=1287
        d=self.stage(s,p,potion)
        self.assertEqual('DRINK',d.action.get('action'))
        self.assertEqual(1601,p.room_journey.route[-1])
        self.assertFalse(p.piranha_rooms[1601]['collected'])

    def test_door_requires_retreat_and_full_trip_budget(self):
        for change in ('retreat','budget'):
            with self.subTest(change=change):
                s,p,potion=self.fixture()
                if change=='retreat':p.blocked.add(1243)
                else:
                    p.loot={1646:dict(cell=1646,name='Chest')}
                    p.tiles[1646]=dict(cell=1646,terrain=11,visible=True,observed=True)
                    p.piranha_rooms={1646:dict(water={1375,1419,1463,1509,1555,1601},
                                              collected=False)}
                    p.room_blocked.add(1646)
                self.assertIsNone(self.stage(s,p,potion))


if __name__=='__main__':unittest.main()
