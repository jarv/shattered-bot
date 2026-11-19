import unittest
from tools.retreat_geometry import onward_exit
from tools.policy_geometry import distance,neighbors,line_clear
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy
from tools.policy_decision import TacticalBlocked


class RetreatGeometryTests(unittest.TestCase):
    def encounter(self):
        s=state();s['hero'].update(cell=40,hp=8,max_hp=20,buffs=[])
        floors={39,40,41,42,43,50,51,52}
        s['map']={'width':9,'height':9,'cells':[{'cell':c,'terrain':1 if c in floors else 4,'visible':True} for c in range(81)]}
        s['objects']=[{'name':'swarm of flies','cell':52}]
        p=verified_policy();p.update(s)
        return s,p

    def test_known_pocket_has_no_onward_exit_other_than_origin(self):
        s,p=self.encounter()
        self.assertFalse(onward_exit(p,s,39,40,{52}))
        self.assertTrue(onward_exit(p,s,41,40,{52}))

    def test_ordinary_retreat_does_not_enter_one_exit_pocket(self):
        s,p=self.encounter();a=p.retreat(s,s['objects'])
        self.assertTrue(a is None or a.action['cell']!=39)

    def test_soft_recovery_cannot_bypass_onward_exit_guard(self):
        s,p=self.encounter()
        a=p.recover_tactical_block(s,TacticalBlocked('critical-pressure','observed pursuer'))
        self.assertNotEqual(39,a.action.get('cell'))

    def test_challenge_route_does_not_choose_dead_end_first_step(self):
        s,p=self.encounter();p.challenge_combat.sight_inputs=5
        a=p.challenge_combat.choose(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertTrue(a is None or a.action.get('cell')!=39)

    def test_forced_telegraph_evasion_keeps_existing_immediate_escape(self):
        s,p=self.encounter()
        for c in (41,42,43,50,51,52):p.tiles[c]['terrain']=4
        a=p.retreat(s,s['objects'],danger={40})
        self.assertEqual(39,a.action['cell'])

    def test_rinsing_is_not_blocked_by_ordinary_retreat_geometry(self):
        s,p=self.encounter()
        p.tiles[39]['terrain']=29
        a=p.retreat(s,s['objects'],rinse=True)
        self.assertEqual(39,a.action['cell'])

    def test_hazardous_or_enemy_occupied_onward_tile_does_not_count(self):
        s,p=self.encounter()
        for c in (42,43,50,51,52):p.tiles[c]['plant']='firebloom'
        self.assertFalse(onward_exit(p,s,41,40,{52}))

    def test_only_onward_square_in_observed_reach_is_not_an_escape(self):
        s,p=self.encounter()
        p.tiles={c:{'cell':c,'terrain':1,'visible':True} for c in (38,40,48,49)}
        enemies=[{'name':'slime','cell':38}]
        self.assertTrue(onward_exit(p,s,49,40,{38}))
        self.assertFalse(onward_exit(p,s,49,40,{38},enemies))

    def test_additional_unexposed_onward_square_restores_admission(self):
        s,p=self.encounter()
        p.tiles={c:{'cell':c,'terrain':1,'visible':True} for c in (38,40,48,49,50)}
        self.assertTrue(onward_exit(p,s,49,40,{38},[{'name':'slime','cell':38}]))

    def fly_pocket(self):
        s,p=self.encounter()
        p.tiles={c:{'cell':c,'terrain':1,'visible':True} for c in (38,40,48,49,57)}
        return s,p

    def test_near_fly_cannot_seal_every_nominal_onward_exit(self):
        s,p=self.fly_pocket();fly={'name':'swarm of flies','cell':38}
        self.assertFalse(onward_exit(p,s,49,40,{38},[fly]))
        # Preserve the older non-fly, multi-exit admission rather than adding
        # a blanket zero-exposure constraint to all ordinary retreat types.
        self.assertTrue(onward_exit(p,s,49,40,{38},[dict(fly,name='slime')]))

    def test_fly_margin_accepts_a_genuinely_farther_onward_square(self):
        s,p=self.fly_pocket();p.tiles[50]={'cell':50,'terrain':1,'visible':True}
        self.assertTrue(onward_exit(p,s,49,40,{38},[{'name':'swarm of flies','cell':38}]))

    def test_far_or_sleeping_fly_does_not_trigger_close_pursuit_guard(self):
        s,p=self.fly_pocket()
        self.assertTrue(onward_exit(p,s,49,40,{38},[{'name':'swarm of flies','cell':38,'sleeping':True}]))
        self.assertTrue(onward_exit(p,s,49,40,{2},[{'name':'swarm of flies','cell':2}]))
