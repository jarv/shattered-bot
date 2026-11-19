import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools import test_hidden_doors
from tools.hidden_doors import secret_search_allowed,seek_corridor_end
from tools.ghost_quest import visit_ghost,quest_combat
from tools.ranged_tactics import choose,exposed_wait
from tools.policy_geometry import distance,neighbors
from tools.policy_runtime import Context
from tools import policy_nodes


class BossSearchTests(unittest.TestCase):
    def test_other_boss_floors_never_budget_secret_room_searches(self):
        for depth in (10,15,20,25):
            s,p=arena();s['depth']=depth
            self.assertFalse(secret_search_allowed(s))
            self.assertEqual(0,p.search_limit(s,40,False))
            self.assertEqual(0,p.search_limit(s,6,True))

    def test_goo_preserves_rat_king_and_hidden_door_search_eligibility(self):
        s,p=arena();s['depth']=5
        self.assertTrue(secret_search_allowed(s))
        self.assertGreater(p.search_limit(s,40,False),0)
        self.assertTrue(secret_search_allowed(dict(s,depth=3)))

    def test_corridor_tip_search_does_not_bypass_boss_floor_rule(self):
        s,p=test_hidden_doors.HiddenDoorTests().corridor();s['depth']=10
        self.assertIsNone(seek_corridor_end(p,s,[],distance))
        s['depth']=5
        self.assertIsNotNone(seek_corridor_end(p,s,[],distance))


class TricksterSurvivalTests(unittest.TestCase):
    def test_trickster_keeps_quest_identity_and_gets_ranged_exposure_admission(self):
        s,p=arena();foe=enemy('gnoll trickster',43)
        profile=p.unit_strategies.profile(foe)
        self.assertEqual('quest:gnoll trickster',profile.strategy)
        self.assertIn('poison-darts',profile.capabilities)
        self.assertTrue(exposed_wait(p,s,[foe]))
        action=policy_nodes.ranged_survival(Context(p,s,enemies=[foe],active=[foe]))
        self.assertIsNotNone(action);self.assertNotEqual('wait',action.action['type'])
        self.assertEqual('quest:gnoll trickster',p.planner.report['unit_strategy_selection']['strategy'])

    def test_quest_combat_delegates_to_committed_ranged_controller(self):
        s,p=arena();foe=enemy('gnoll trickster',43)
        with patch('tools.ranged_tactics.choose',return_value='delegated') as delegated:
            self.assertEqual('delegated',quest_combat(p,s,[foe],distance,neighbors))
        delegated.assert_called_once()

    def test_unseen_trickster_cannot_trigger_ghost_reminder_retreat_reversal(self):
        s,p=arena();s['depth']=3;s['hero']['hp']=s['hero']['max_hp']
        p.ghost_quest.update(stage='active',target='gnoll trickster',target_seen=True,
                             last_depth=3,last_cell=43,reminder_queried=False)
        p.recent_threats[60]=enemy('gnoll trickster',60,observations_ago=1)
        self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))
        self.assertEqual(0,p.ghost_quest['travel']);self.assertFalse(p.ghost_quest['reminder_queried'])

    def test_poison_critical_health_and_accepted_escape_preempt_ghost_errands(self):
        for case in ('poison','health','escape'):
            s,p=arena();s['depth']=3;s['objects']=[{'name':'sad ghost','cell':41}]
            p.ghost_quest.update(stage='reward')
            if case=='poison':s['hero']['buffs']=[{'name':'poisoned'}]
            if case=='health':s['hero']['hp']=4
            if case=='escape':p.escape_commitment={'edges':[(40,39)],'age':1}
            self.assertIsNone(visit_ghost(p,s,[],distance,neighbors),case)

    def test_committed_cover_also_prevents_ghost_errands(self):
        s,p=arena();s['depth']=3
        s['objects']=[{'name':'sad ghost','cell':41}]
        p.ghost_quest.update(stage='reward');p.ranged_plan={'name':'gnoll trickster','mode':'cover'}
        self.assertIsNone(visit_ghost(p,s,[],distance,neighbors))

    def test_poison_tick_alone_does_not_invalidate_otherwise_verified_cover(self):
        s,p=arena();s['hero']['buffs']=[{'name':'poisoned'}]
        foe=enemy('gnoll trickster',43)
        p.ranged_plan={'name':'gnoll trickster','mode':'cover','goal':40,'steps':1,'waits':0,
                       'hp':s['hero']['hp']+2,'dot':True}
        with patch.object(p,'enemy_can_see',return_value=False),patch('tools.ranged_tactics.exposure',return_value={'exposure':0}):
            action=choose(p,s,[foe])
        self.assertEqual('wait',action.action['type'])
        self.assertFalse(p.ranged_failed_cover)

    def test_sheltered_poison_can_prioritize_a_known_cleansing_seed(self):
        s,p=arena();s['hero']['buffs']=[{'name':'poisoned'}]
        foe=enemy('gnoll trickster',44)
        s['inventory'].append({'id':'mageroyal','name':'seed of mageroyal','actions':['PLANT']})
        p.ranged_plan={'name':'gnoll trickster','mode':'cover','goal':40,'steps':1,'waits':0,
                       'hp':s['hero']['hp']+1,'dot':True}
        with patch.object(p,'enemy_can_see',return_value=False),patch('tools.ranged_tactics.exposure',return_value={'exposure':0}):
            action=choose(p,s,[foe])
        self.assertEqual('PLANT',action.action['action']);self.assertEqual('mageroyal',action.action['id'])


if __name__=='__main__':unittest.main()
