import unittest
from tools.boxed_snake_escape import choose
from tools.policy_decision import Intent,TacticalBlocked
from tools.policy_runtime import Transaction
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy


class BoxedSnakeEscapeTests(unittest.TestCase):
    def encounter(self):
        s=state();s['hero'].update(cell=40,hp=8,max_hp=20,buffs=[])
        floors={40,32,33,24,25,34,35,43,44}
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':1 if c in floors else 4,'visible':True} for c in range(81)]}
        s['objects']=[{'name':'sewer snake','cell':31,'description':'Evasive.'}]
        s['inventory'][0]['status']='0/4'
        p=verified_policy();p.update(s)
        return s,p

    def test_equal_first_exposure_requires_known_bounded_clear_endpoint(self):
        s,p=self.encounter();a=choose(p,s,s['objects'])
        self.assertEqual(Intent.RETREAT,a.intent)
        r=p.planner.report['boxed_snake_escape']
        self.assertEqual(1,r['exposure_before']);self.assertEqual(1,r['exposure_next'])
        self.assertEqual(0,r['endpoint_exposure']);self.assertLessEqual(len(r['route']),4)

    def test_charged_magic_or_healthy_hero_does_not_activate_override(self):
        s,p=self.encounter();s['hero']['hp']=15
        self.assertIsNone(choose(p,s,s['objects']))
        s['hero']['hp']=8;s['inventory'][0]['status']='1/4'
        self.assertIsNone(choose(p,s,s['objects']))

    def test_new_hazard_invalidates_pending_endpoint(self):
        s,p=self.encounter();a=choose(p,s,s['objects'])
        s['hero']['cell']=a.action['cell']
        p.tiles[p.boxed_snake_escape['target']]['plant']='firebloom'
        self.assertIsNone(choose(p,s,s['objects'],resume_only=True))
        self.assertIsNone(p.boxed_snake_escape)

    def test_no_endpoint_never_overrides_revealed_hazard(self):
        s,p=self.encounter()
        for c in (33,24,25,34,35,43,44):p.tiles[c]['plant']='firebloom'
        self.assertIsNone(choose(p,s,s['objects']))

    def test_two_starts_per_floor_and_transaction_rollback(self):
        s,p=self.encounter();tx=Transaction(p);choose(p,s,s['objects']);tx.rollback()
        self.assertEqual(0,p.boxed_snake_escape_uses);self.assertIsNone(p.boxed_snake_escape)
        p.boxed_snake_escape_uses=2
        self.assertIsNone(choose(p,s,s['objects']))
        p.memory.reset_floor(40);self.assertEqual(0,p.boxed_snake_escape_uses)

    def test_critical_recovery_selects_route_before_snake_melee(self):
        s,p=self.encounter();a=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','boxed snake'))
        self.assertEqual(Intent.RETREAT,a.intent)
        self.assertNotEqual(31,a.action.get('cell'))

    def test_combat_modifiers_and_protected_return_are_not_bypassed(self):
        s,p=self.encounter();s['objects'][0]['description']='_Projecting Champion_'
        self.assertIsNone(choose(p,s,s['objects']))
        s['objects'][0]['description']='Evasive.';s['hero']['buffs']=[{'name':'burning'}]
        self.assertIsNone(choose(p,s,s['objects']))
        s['hero']['buffs']=[];p.room_journey=object()
        self.assertIsNone(choose(p,s,s['objects']))
