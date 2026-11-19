import unittest
from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_consumable_tactics import potion
from tools.policy_geometry import distance,neighbors
from tools.puzzle_supplies import demands,prepare_supplies,safe_test_bank
from tools.room_tactics import safe_tile


def pool_room(known=False):
    s,_=arena();s['hero']['cell']=35
    s['map']={'width':11,'height':7,'cells':[]}
    for c in range(77):
        x,y=c%11,c//11
        terrain=4 if x in {0,10} or y in {0,6} else 29 if 4<=x<=8 and 2<=y<=4 else 1
        s['map']['cells'].append({'cell':c,'terrain':terrain,'visible':True,'observed':True})
    s['objects']=[{'name':'giant piranha','cell':38},{'name':'Chest','cell':41}]
    s['inventory'].append(potion('potion of invisibility' if known else 'azure potion'))
    p=verified();p.update(s)
    return s,p


class MirrorPassageTests(unittest.TestCase):
    def test_walking_through_mirror_image_keeps_it_a_projectile_blocker(self):
        s,p=arena();s['objects']=[{'name':'mirror image','cell':41}];p.update(s)
        self.assertIn(41,p.neutral_actor_cells)
        self.assertTrue(p.walkable(41));self.assertIn(42,p.paths(s))
        self.assertFalse(p.shot_clear(s,43))
        self.assertTrue(safe_tile(p,41,'pool',set()))

    def test_mirror_image_does_not_override_traps_effects_or_explicit_occupancy(self):
        s,p=arena();s['objects']=[{'name':'mirror image','cell':41}];p.update(s)
        self.assertFalse(p.walkable(41,occupied={41}))
        p.tiles[41].update(terrain=18,trap='burning trap')
        self.assertFalse(p.walkable(41))
        p.tiles[41].pop('trap');p.tiles[41].update(terrain=1,effects=['A fire is raging here.'])
        self.assertFalse(p.walkable(41))

    def test_other_neutrals_are_not_assumed_swappable(self):
        for name in ('sad ghost','shopkeeper','animated statue','sheep'):
            s,p=arena();s['objects']=[{'name':name,'cell':41}];p.update(s)
            self.assertFalse(p.walkable(41),name)

    def test_mirror_gone_or_moved_does_not_leave_a_permanent_passage_exception(self):
        s,p=arena();s['objects']=[{'name':'mirror image','cell':41}];p.update(s)
        s['objects']=[{'name':'shopkeeper','cell':41}];p.update(s)
        self.assertFalse(p.walkable(41));self.assertFalse(p.friendly_passage_cells)


class PiranhaInvisibilityTests(unittest.TestCase):
    def test_piranha_chest_demands_invisibility_and_tests_only_from_safe_dry_bank(self):
        s,p=pool_room()
        self.assertTrue(any(d.kind=='pool' and d.potion=='potion of invisibility' for d in demands(p,s,distance)))
        self.assertFalse(safe_test_bank(p,s,35,distance,neighbors,allow_dry=True))
        self.assertTrue(safe_test_bank(p,s,35,distance,neighbors,allow_dry=True,pool_bank=True))
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('DRINK',action.action['action']);self.assertEqual('pool',p.room_journey.kind)
        self.assertEqual(41,p.room_journey.route[-1])
        self.assertNotEqual(29,p.tiles[s['hero']['cell']]['terrain'])

    def test_known_invisibility_is_committed_to_actual_buff_backed_round_trip(self):
        s,p=pool_room(True)
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual('potion of invisibility',action.action['id'])
        self.assertEqual('DRINK',action.action['action'])
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))  # No buff: no crossing.
        self.assertIsNone(p.room_journey)

    def test_actual_invisibility_takes_priority_over_generic_exploration(self):
        s,p=pool_room();prepare_supplies(p,s,[],distance,neighbors)
        s['hero']['buffs']=[{'name':'invisible','description':'Turns of invisibility remaining: 20.'}];p.update(s)
        action=p.choose(s)
        self.assertEqual('hazardous-room-escape',action.controller)
        self.assertIn('verified protected route',action.reason)

    def test_testing_in_or_immediately_next_to_water_is_rejected(self):
        s,p=pool_room()
        self.assertFalse(safe_test_bank(p,s,37,distance,neighbors,allow_dry=True,pool_bank=True))
        self.assertFalse(safe_test_bank(p,s,38,distance,neighbors,allow_dry=True,pool_bank=True))

    def test_pool_candidate_is_not_spent_without_an_observed_reward_or_on_suspicious_chest(self):
        for case in ('missing','suspicious'):
            s,p=pool_room()
            if case=='missing':p.loot.clear()
            else:p.loot[41]['description']='This chest feels off. Opening it would be a bad idea.'
            action=prepare_supplies(p,s,[],distance,neighbors)
            self.assertTrue(action is None or action.action.get('action')!='DRINK',case)
            self.assertIsNone(p.room_journey)


if __name__=='__main__':unittest.main()
