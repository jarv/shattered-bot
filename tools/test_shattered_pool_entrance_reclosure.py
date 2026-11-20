"""Reduced public door cycle, decisions 3176-3178; selection only, no game."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies


def approach():
    s = state()
    s['depth'] = 7
    s['hero'].update(cell=731, hp=60, max_hp=60, strength=13, buffs=[])
    groups = {
        1: [641,642,643,685,686,729,730,731,773,774,775,817,818,819,
            861,862,863,905,906,907,949,950,992,993,994,995],
        4: [644,688,690,691,692,693,694,738,776,782,820,826,864,870,
            908,914,952,958,996,1001,1002],
        12: [689], 20: [687,951], 5: [732], 14: [733,777,821],
        29: [734,735,736,737,778,779,780,781,822,823,824,825,866,867,
             868,911,912,913,956,957],
        11: [869], 34: [640,728,772,948], 0: [684,816,860,904],
    }
    s['map'] = dict(width=44, height=43, cells=[
        dict(cell=c, terrain=t, observed=True,
             visible=c <= 732 or c in groups[1]+groups[20]+[776])
        for t, cs in groups.items() for c in cs])
    s['objects'] = [dict(cell=869, name='Chest'),
                    dict(cell=824, name='giant piranha', sleeping=True),
                    dict(cell=913, name='giant piranha', sleeping=True)]
    p = verified()
    p.update(s)  # Public no-bag observation, before this fixture's acquisition.
    s['inventory'] += [
        dict(id='bag', name='potion bandolier', identified=True, actions=['DROP','THROW']),
        dict(id='unknown', name='indigo potion', identified=False, quantity=1,
             actions=['DROP','THROW','DRINK']),
    ]
    p.update(s)
    p.loot[869] = dict(cell=869, name='Chest')
    p.piranha_rooms[869] = dict(water=set(groups[29]), collected=False)
    # Reobserve so remembered habitat applies its ordinary movement exclusion.
    p.update(s)
    return s, p


class PoolEntranceReclosureTests(unittest.TestCase):
    def select(self, s, p):
        d = prepare_supplies(p, s, [], distance, neighbors)
        p.last_decision = d
        return d

    def opened(self):
        s, p = approach()
        self.assertEqual({'type':'cell','cell':732}, self.select(s,p).action)
        # Recorded arrival at 3177: standing in the entrance opens it.
        s = copy.deepcopy(s)
        s['hero']['cell'] = 732
        for t in s['map']['cells']:
            if t['cell'] == 732:
                t['terrain'] = 6
            t['visible'] = t['cell'] != 644
        p.update(s)
        self.assertEqual({'type':'cell','cell':731}, self.select(s,p).action)
        return s,p

    def test_observed_opening_survives_normal_reclosure(self):
        s,p = self.opened()
        # Independent selector fixture for 3178, the first changed selection.
        s = copy.deepcopy(s)
        s['hero']['cell'] = 731
        next(t for t in s['map']['cells'] if t['cell']==732)['terrain'] = 5
        p.update(s)
        d = self.select(s,p)
        self.assertEqual('DRINK', d.action.get('action'),
                         'A verified entrance must not require another scouting lap')
        self.assertEqual('pool', p.puzzle_probe['kind'])
        self.assertEqual([731,732,733,778,823,868,869], p.room_journey.route)
        self.assertFalse(p.piranha_rooms[869]['collected'])
        self.assertFalse(p.completed_room_rewards)
        # Unknown remains unknown: without an actual invisibility receipt the
        # journey cancels rather than entering the remembered habitat.
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.piranha_rooms[869]['collected'])

    def test_no_open_receipt_from_unchanged_public_state(self):
        s,p = approach()
        self.select(s,p)
        p.update(s)  # No arrival or open terrain: no success receipt.
        self.assertEqual({'type':'cell','cell':732}, self.select(s,p).action)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)

    def test_new_hazard_still_blocks_the_trip(self):
        s,p = self.opened()
        s = copy.deepcopy(s)
        s['hero']['cell'] = 731
        tile = next(t for t in s['map']['cells'] if t['cell']==732)
        tile.update(terrain=5, trap='shocking trap')
        p.update(s)
        d = self.select(s,p)
        self.assertTrue(d is None or d.action.get('action') != 'DRINK')
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.piranha_rooms[869]['collected'])

    def test_scout_receipt_is_floor_local_and_branch_specific(self):
        s,p = self.opened()
        s = copy.deepcopy(s)
        s['hero']['cell'] = 731
        s['branch'] = 1
        next(t for t in s['map']['cells'] if t['cell']==732)['terrain'] = 5
        p.update(s)
        self.assertEqual({'type':'cell','cell':732}, self.select(s,p).action)
        p.memory.reset_floor(731)
        self.assertFalse(getattr(p,'pool_entrance_receipts',set()))
        self.assertIsNone(getattr(p,'pool_entrance_pending',None))


if __name__ == '__main__':
    unittest.main()
