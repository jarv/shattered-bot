import unittest
from unittest.mock import patch

from tools.test_seed_strategy_evaluation import corridor
from tools.policy_runtime import Context
from tools.policy_nodes import critical_transport
from tools.runestone_tactics import blink_escape
from tools.policy_geometry import distance,neighbors


class CriticalBlinkTests(unittest.TestCase):
    def setup_case(self,hp=4):
        s,p=corridor('earthroot',gap=1)
        s['hero'].update(cell=37,hp=hp)
        s['objects'][0]['cell']=36
        s['inventory'].append({'id':'blink','name':'stone of blink','actions':['THROW']})
        p.update(s)
        return s,p

    def test_blink_precedes_multi_enemy_walking_at_critical_health(self):
        s,p=self.setup_case()
        s['objects'].append(dict(s['objects'][0],cell=35))
        p.update(s)
        a=p.choose(s)
        self.assertEqual('critical-transport',a.controller)
        self.assertEqual({'type':'item','id':'blink','action':'THROW'},a.action)

    def test_known_healing_precedes_blink(self):
        s,p=self.setup_case()
        s['inventory'].append({'id':'heal','name':'potion of healing','actions':['DRINK']})
        self.assertEqual('emergency-healing',p.choose(s).controller)

    def test_no_blink_for_healthy_or_peaceful_hero_or_dedicated_boss(self):
        for hp,active,boss in ((16,True,None),(4,False,None),(4,True,object())):
            s,p=self.setup_case(hp)
            with patch.object(p,'emergency_transport') as transport:
                self.assertIsNone(critical_transport(Context(p,s,enemies=s['objects'],
                    active=s['objects'] if active else [],boss=boss)))
                transport.assert_not_called()

    def test_exhausted_hurt_withdrawal_checks_transport_before_more_walking(self):
        s,p=self.setup_case(8)
        s['inventory'][0]['actions']=['IMBUE']
        p.critical_retreats=3
        with patch.object(p,'charged_magic',return_value=False):
            self.assertEqual('blink',critical_transport(Context(p,s,enemies=s['objects'],active=s['objects'])).action['id'])

    def test_no_eligible_landing_declines_and_preserves_stone(self):
        s,p=self.setup_case()
        for tile in p.tiles.values():tile['visible']=False
        self.assertIsNone(blink_escape(p,s,s['objects'],distance,neighbors))
        self.assertIsNone(p.target)

    def test_known_trap_landings_are_never_selected(self):
        s,p=self.setup_case()
        for tile in p.tiles.values():tile['trap']='poison dart trap'
        self.assertIsNone(blink_escape(p,s,s['objects'],distance,neighbors))


if __name__=='__main__':unittest.main()
