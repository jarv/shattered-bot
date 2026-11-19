import unittest

from tools.test_challenge_systems import ready,item
from tools.retreat_geometry import onward_runway


class FunnelRunwayTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['hero']['cell']=40
        floors={40,31,22,49,50}
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':1 if c in floors else 4,
                                              'visible':True} for c in range(81)]}
        s['objects']=[{'name':'swarm of flies','cell':49},{'name':'gnoll scout','cell':50}]
        p.update(s);return s,p

    def test_single_onward_square_that_is_itself_dead_end_is_rejected(self):
        s,p=self.encounter();occupied={49,50}
        self.assertTrue(p.walkable(22,occupied))
        self.assertFalse(onward_runway(p,s,31,40,occupied,s['objects']))
        self.assertIsNone(p.single_enemy_position(s,s['objects']))

    def test_connected_second_onward_step_keeps_safe_funnel_admission(self):
        s,p=self.encounter();p.tiles[13]['terrain']=1
        self.assertTrue(onward_runway(p,s,31,40,{49,50},s['objects']))
        self.assertEqual(31,p.single_enemy_position(s,s['objects']).action['cell'])

    def test_observed_extended_reach_is_not_treated_as_normal_melee(self):
        s,p=self.encounter();p.tiles[13]['terrain']=1
        s['objects'][0]['description']='_Projecting Champion_'
        self.assertFalse(onward_runway(p,s,31,40,{49,50},s['objects']))

    def test_loot_and_hazards_cannot_supply_the_only_second_step(self):
        for mode in ('loot','plant','danger'):
            s,p=self.encounter();p.tiles[13]['terrain']=1
            if mode=='loot':p.loot[13]={'name':'seed','top_item':item('seed','THROW')}
            elif mode=='plant':p.tiles[13]['plant']='firebloom'
            else:s['danger_cells']=[13]
            self.assertFalse(onward_runway(p,s,31,40,{49,50},s['objects']))


if __name__=='__main__':unittest.main()
