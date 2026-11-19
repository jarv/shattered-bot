import unittest

from tools import test_challenge_systems as fixtures
from tools.policy_geometry import distance,neighbors
from tools.combat_positioning import rinse_ooze
from tools.policy_decision import Decision,Intent,Finished
from tools.policy_runtime import Transaction
from tools.pursuit_budget import observe_accepted,review_outcome
from tools.escape_commitment import reverses
from tools.alchemy_tactics import plan_brew,alchemy_menu,Brew


class DepthStrategiesTests(unittest.TestCase):
    def burning(self):
        s,p=fixtures.ready()
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':1,'visible':True} for c in range(81)]}
        s['hero'].update(cell=40,hp=12,max_hp=20,buffs=[{'name':'burning'}])
        p.update(s)
        return s,p

    def test_critical_known_frost_precedes_water_rejection(self):
        s,p=self.burning();s['hero']['hp']=1;p.tiles[4]['terrain']=29
        s['inventory'].append(fixtures.item('potion of frost','THROW'))
        a=rinse_ooze(p,s,[],distance,neighbors)
        self.assertEqual('THROW',a.action['action']);self.assertEqual(40,p.target)
        self.assertIn('self-splash',a.reason)

    def test_unknown_potion_never_assumed_frost(self):
        s,p=self.burning();s['hero']['hp']=1;p.tiles[4]['terrain']=29
        s['inventory'].append(fixtures.item('azure potion','THROW'))
        with self.assertRaises(Finished):rinse_ooze(p,s,[],distance,neighbors)

    def test_adjacent_water_preserves_frost(self):
        s,p=self.burning();p.tiles[41]['terrain']=29
        s['inventory'].append(fixtures.item('potion of frost','THROW'))
        self.assertEqual(41,rinse_ooze(p,s,[],distance,neighbors).action['cell'])

    def test_farther_water_is_committed_not_loot_fallthrough(self):
        s,p=self.burning();s['hero']['cell']=0;p.tiles[80]['terrain']=29
        a=rinse_ooze(p,s,[],distance,neighbors)
        self.assertEqual(Intent.RETREAT,a.intent);self.assertEqual(80,p.burning_water_plan['cell'])
        p.burning_water_plan['steps']=24
        with self.assertRaises(Finished):rinse_ooze(p,s,[],distance,neighbors)

    def test_no_water_no_frost_never_generic_wait(self):
        s,p=self.burning()
        with self.assertRaises(Finished):rinse_ooze(p,s,[],distance,neighbors)

    def test_noncritical_burning_can_open_known_ordinary_door_on_water_route(self):
        s,p=self.burning();s['hero']['cell']=0
        p.tiles={c:{'cell':c,'terrain':5 if c==3 else 29 if c==7 else 1,'visible':True} for c in range(8)}
        self.assertEqual(1,rinse_ooze(p,s,[],distance,neighbors).action['cell'])

    def test_airborne_burning_requires_splash_not_water(self):
        s,p=self.burning();s['hero']['buffs'].append({'name':'levitation'});p.tiles[41]['terrain']=29
        with self.assertRaises(Finished):rinse_ooze(p,s,[],distance,neighbors)

    def test_water_plan_rejected_action_rolls_back(self):
        s,p=self.burning();p.tiles[4]['terrain']=29;tx=Transaction(p)
        rinse_ooze(p,s,[],distance,neighbors);tx.rollback()
        self.assertIsNone(p.burning_water_plan)

    def transition(self,p,s,origin,cell,intent=Intent.RETREAT):
        before=dict(s,hero=dict(s['hero'],cell=origin),objects=[{'name':'marsupial rat','cell':10}])
        after=dict(before,hero=dict(before['hero'],cell=cell))
        observe_accepted(p,before,Decision({'type':'cell','cell':cell},'test',intent),after)
        return after

    def test_escape_survives_controller_change_but_recharge_releases(self):
        s,p=self.burning();after=self.transition(p,s,40,41)
        self.assertTrue(reverses(p,after,40))
        after=dict(after,inventory=[fixtures.item('staff of magic missile','ZAP',status='9/9')])
        observe_accepted(p,dict(after,inventory=[]),Decision({'type':'wait'},'recharge'),after)
        self.assertFalse(reverses(p,after,40))

    def test_escape_commitment_expires_and_floor_resets(self):
        s,p=self.burning();after=self.transition(p,s,40,41)
        for _ in range(12):
            observe_accepted(p,after,Decision({'type':'wait'},'test'),after)
        self.assertIsNone(p.escape_commitment)

    def test_free_inspection_does_not_expire_escape_and_transaction_rolls_back(self):
        s,p=self.burning();after=self.transition(p,s,40,41)
        for _ in range(20):observe_accepted(p,after,Decision({'type':'inspect','cell':10},'inspect'),after)
        self.assertTrue(reverses(p,after,40))
        tx=Transaction(p);self.transition(p,s,41,42);tx.rollback()
        self.assertNotIn((41,42),p.escape_commitment['edges'])
        self.transition(p,s,40,41);p.memory.reset_floor(40)
        self.assertIsNone(p.escape_commitment)

    def test_prolonged_review_survives_exhausted_cast_interventions(self):
        s,p=self.burning();p.pursuit_interventions=2
        for i in range(12):self.transition(p,s,40+i%2,41-i%2)
        review_outcome(p,s)
        self.assertTrue(p.pursuit_lure_exhausted)
        self.assertIn('pursuit_outcome',p.planner.report)
        self.assertEqual(2,p.pursuit_interventions)

    def test_snakes_and_crabs_release_reserve_not_unknown_charge_claims(self):
        s,p=fixtures.ready()
        for name in ('sewer snake','sewer crab'):
            enemy={'name':name,'cell':25};s['objects']=[enemy]
            a=p.best_attack(s,enemy,reserve=True,reserve_magic=True)
            self.assertEqual('ZAP',a.action.get('action'))

    def test_scarce_magic_is_reserved_only_for_healthy_single_rat(self):
        s,p=fixtures.ready();s['hero']['hp']=14;s['hero']['max_hp']=20
        s['inventory'][0]['status']='1/4';enemy={'name':'marsupial rat','cell':25};s['objects']=[enemy]
        a=p.best_attack(s,enemy)
        self.assertNotEqual('ZAP',a.action.get('action'))
        self.assertIn('dangerous_enemy_reserve',p.planner.report)
        s['hero']['hp']=5
        self.assertEqual('ZAP',p.best_attack(s,enemy).action.get('action'))

    def test_raw_meat_precedes_optional_recipes_while_not_starving(self):
        s,p=fixtures.ready();s['inventory'] += [fixtures.item('mystery meat','EAT'),
            fixtures.item('scroll of identify','READ'),fixtures.item('azure potion','THROW',quantity=3)]
        self.assertEqual('stewed meat',plan_brew(s).output)

    def test_meat_ingredient_selector_uses_backpack(self):
        s,p=fixtures.ready();p.alchemy_plan={'brew':Brew(('mystery meat',),'stewed meat','test'),
            'stage':'bag','index':0,'steps':0}
        s['ui']['buttons']=[{'id':'pack','label':'Backpack'},{'id':'pots','label':'Potion bandolier'}]
        self.assertEqual('pack',alchemy_menu(p,s).action['id'])


if __name__=='__main__':unittest.main()
