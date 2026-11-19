import unittest
from tools.region_navigation import choose
from tools import test_strict_loot
from tools.test_challenge_systems import item
from tools.policy_decision import Intent


class StairLootTests(unittest.TestCase):
    def encounter(self,visible=True):
        s,p=test_strict_loot.StrictLootTests().encounter()
        p.tiles[25].update(terrain=7,visible=visible)
        obj={'cell':25,'name':'gold x109','top_item':item('gold x109','THROW')}
        p.loot[25]=obj;s['objects']=[obj] if visible else []
        return s,p

    def test_visible_adjacent_pile_is_pickup_destination(self):
        s,p=self.encounter();a=choose(p,s,p.paths(s),set())
        self.assertEqual(25,a.action['cell']);self.assertIn('freshly visible pile',a.reason)

    def test_remembered_stair_pile_is_never_clicked(self):
        s,p=self.encounter(False);a=choose(p,s,p.paths(s),set())
        self.assertTrue(a is None or a.action.get('cell')!=25)

    def test_distant_remembered_stair_pile_gets_adjacent_reobservation(self):
        s,p=self.encounter(False);s['hero']['cell']=0
        a=choose(p,s,p.paths(s),set())
        self.assertIsNotNone(a);self.assertIn('reobserve stair pile',a.reason)
        self.assertNotEqual(25,a.action['cell'])

    def test_empty_stair_is_not_pickup(self):
        s,p=self.encounter();p.loot={};s['objects']=[]
        a=choose(p,s,p.paths(s),set())
        self.assertTrue(a is None or 'freshly visible pile' not in a.reason)

    def test_stair_is_not_used_as_transit_by_original_paths(self):
        s,p=self.encounter();p.tiles={24:p.tiles[24],25:p.tiles[25],26:p.tiles[26]}
        self.assertNotIn(26,p.paths(s))

    def test_fresh_pile_does_not_relax_exploration_barrier(self):
        s,p=self.encounter()
        self.assertIn(25,p.navigation_barriers(s,Intent.EXPLORE))
        self.assertNotIn(25,p.navigation_barriers(s,Intent.LOOT))

    def test_threat_or_sale_keeps_stair_barrier(self):
        for case in ('threat','sale','distant','missing'):
            s,p=self.encounter()
            if case=='threat':p.recent_threats[23]={'cell':23,'name':'rat'}
            if case=='sale':s['objects'][0]['for_sale']=True
            if case=='distant':s['hero']['cell']=0
            if case=='missing':s['objects']=[]
            self.assertIn(25,p.navigation_barriers(s,Intent.LOOT),case)
