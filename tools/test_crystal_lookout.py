import unittest

from tools.test_challenge_systems import ready
from tools.policy_geometry import distance
from tools.room_tactics import investigate_suspect_container


class CrystalLookoutTests(unittest.TestCase):
    def encounter(self):
        s,p=ready();s['hero']['cell']=60;s['inventory'][0]['status']='4/4'
        floors={y*9+x for y in range(5,8) for x in range(2,7)}|{13,22,31,40}
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':5 if c==40 else 1 if c in floors else 4,
                                              'visible':True} for c in range(81)]}
        s['objects']=[];p.update(s)
        p.loot[58]={'cell':58,'name':'Crystal chest','description':'It feels off; opening is a bad idea.'}
        return s,p

    def test_outward_observed_lines_precede_closer_enclosed_bank(self):
        s,p=self.encounter();a=investigate_suspect_container(p,s,[],distance)
        self.assertNotEqual('ZAP',a.action.get('action'))
        self.assertEqual(40,p.suspect_probe_plan['bank'])
        self.assertGreater(p.planner.report['suspect_staging']['outward_line_score'],0)
        self.assertEqual(2,distance(40,58,9))

    def test_opened_lookout_keeps_range_two_and_existing_charge_checks(self):
        s,p=self.encounter();investigate_suspect_container(p,s,[],distance)
        p.tiles[40]['terrain']=6;s['hero']['cell']=40
        a=investigate_suspect_container(p,s,[],distance)
        self.assertEqual('ZAP',a.action.get('action'));self.assertEqual(58,p.target)
        self.assertIn((s['depth'],'suspect-container',58),p.room_attempts)

    def test_known_hazardous_lookout_is_not_admitted_for_better_view(self):
        s,p=self.encounter();p.tiles[40]['plant']='firebloom'
        a=investigate_suspect_container(p,s,[],distance)
        self.assertNotEqual(40,a.action.get('cell'))
        self.assertNotEqual(40,(p.suspect_probe_plan or {}).get('bank'))

    def test_no_outward_lookout_preserves_existing_safe_bank_fallback(self):
        s,p=self.encounter();p.tiles[40]['terrain']=4
        a=investigate_suspect_container(p,s,[],distance)
        self.assertIsNotNone(a)
        self.assertEqual('ZAP',a.action.get('action'))


if __name__=='__main__':unittest.main()
