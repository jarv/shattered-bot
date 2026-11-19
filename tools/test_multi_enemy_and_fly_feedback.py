import copy
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state,fully_known
from tools.test_unit_strategies import enemy
from tools.policy_decision import Decision,Intent,TacticalBlocked
from tools.policy_runtime import Transaction
from tools.policy_geometry import distance,neighbors,line_clear
from tools import multi_enemy_tactics as multi
from tools.fly_tactics import desperate_attack,observe_fallback
from tools.tactical_recovery import recover


def choke(flying=False):
    s=fully_known(state());s['hero']['cell']=24
    for t in s['map']['cells']:
        t['terrain']={16:1,17:1,18:1,23:0,24:6,25:0,31:1,38:1}.get(t['cell'],4)
    name='swarm of flies' if flying else 'gnoll scout'
    foes=[enemy(name,16),enemy(name,18)];s['objects']=foes
    p=verified();p.update(s)
    return s,p,foes


def boxed_flies():
    s,p=arena();foes=[enemy('swarm of flies',41,health_bar=[1,43]),enemy('swarm of flies',49,health_bar=[2,43])]
    s['objects']=foes
    staff=s['inventory'][0];staff['status']='0/3';staff['actions']=['DROP','THROW','IMBUE']
    for c,t in p.tiles.items():t['terrain']=1 if c in {40,41,49} else 4
    return s,p,foes


class MultiEnemyRetreatTests(unittest.TestCase):
    def test_two_current_attackers_retreat_before_preparation_or_attacking(self):
        s,p,foes=choke()
        action=p.choose(s)
        self.assertEqual('multi-threat-retreat',action.controller)
        self.assertEqual(Intent.RETREAT,action.intent)
        report=p.planner.report['multi_enemy_retreat']
        self.assertEqual(2,report['attackers_before'])
        self.assertLessEqual(report['endpoint_attackers'],1)
        self.assertLessEqual(report['endpoint_approach_slots'],1)

    def test_ground_queue_shares_one_gate_but_flyers_can_use_pit_flanks(self):
        s,p,foes=choke()
        self.assertEqual(1,multi.approach_pressure(p,s,foes,31))
        self.assertTrue(multi.single_file(p,s,foes,31))
        s,p,foes=choke(True)
        self.assertEqual(2,multi.approach_pressure(p,s,foes,31))
        self.assertFalse(multi.single_file(p,s,foes,31))
        self.assertTrue(multi.footable(p,foes[0],23))

    def test_flight_is_not_a_blanket_speed_bonus_and_traps_are_not_walls(self):
        s,p,foes=choke(True)
        self.assertNotIn('fast-movement',p.unit_strategies.profile(foes[0]).capabilities)
        self.assertIn('fast-movement',p.unit_strategies.profile(enemy('vampire bat')).capabilities)
        self.assertNotIn('fast-movement',p.unit_strategies.profile(enemy('hermit crab')).capabilities)
        p.tiles[23]['terrain']=18
        self.assertTrue(multi.footable(p,enemy('gnoll scout'),23))
        self.assertTrue(multi.footable(p,foes[0],23))

    def test_one_attacker_does_not_preempt_combat(self):
        s,p,foes=choke()
        self.assertIsNone(multi.choose(p,s,foes[:1]))

    def test_no_single_attacker_square_logs_and_defers_to_best_effort(self):
        s,p,foes=boxed_flies()
        self.assertIsNone(multi.choose(p,s,foes))
        self.assertEqual('no-single-attacker-retreat',p.continuation_errors[-1]['kind'])

    def test_only_confirmed_retreat_movement_consumes_edge_budget(self):
        s,p,foes=choke();action=multi.choose(p,s,foes);action.controller='multi-threat-retreat'
        after=copy.deepcopy(s)
        self.assertIsNone(multi.observe_accepted(p,s,action,after))
        self.assertFalse(any(p.multi_retreat_edges.values()))
        action=multi.choose(p,s,foes);action.controller='multi-threat-retreat';after['hero']['cell']=action.action['cell']
        self.assertEqual(1,multi.observe_accepted(p,s,action,after)['accepted_edge_traversals'])
        self.assertIsNone(multi.observe_accepted(p,s,action,after))

    def test_rejection_rolls_back_retreat_and_flight_memory_is_floor_local(self):
        s,p,foes=choke();transaction=Transaction(p,p.planner)
        multi.choose(p,s,foes);transaction.rollback()
        self.assertIsNone(p.multi_retreat_pending)
        p.multi_retreat_edges[(24,31)]=2;p.memory.reset_floor(24)
        self.assertFalse(p.multi_retreat_edges)


class BoxedFlyFallbackTests(unittest.TestCase):
    def test_boxed_visible_weak_fragment_is_struck_not_silently_waited_on(self):
        s,p,foes=boxed_flies()
        self.assertFalse(p.attack_kind_allowed(s,foes[0],'melee'))
        action=desperate_attack(p,s,foes)
        self.assertEqual({'type':'cell','cell':41},action.action)
        self.assertIsNone(p.fly_attack_override)
        self.assertFalse(p.attack_kind_allowed(s,foes[0],'melee'))
        self.assertFalse(any(p.fly_fallback_attempts.values()))

    def test_usable_magic_still_prevents_splitting_melee(self):
        s,p,foes=boxed_flies();s['inventory'][0].update(status='1/3',curse_known=True,known_cursed=False)
        s['inventory'][0]['actions'].append('ZAP')
        action=desperate_attack(p,s,foes)
        self.assertEqual('ZAP',action.action['action']);self.assertIsNone(p.fly_fallback_pending)

    def test_accepted_attempts_are_counted_without_claiming_hits_or_kills(self):
        s,p,foes=boxed_flies();action=desperate_attack(p,s,foes)
        receipt=observe_fallback(p,s,action,copy.deepcopy(s))
        self.assertEqual(1,receipt['accepted_attempts'])
        self.assertIn('no kill or damage inferred',receipt['evidence'])
        self.assertIsNone(observe_fallback(p,s,action,copy.deepcopy(s)))

    def test_failed_context_and_rejected_proposals_do_not_consume_attempt_budget(self):
        s,p,foes=boxed_flies();transaction=Transaction(p,p.planner)
        desperate_attack(p,s,foes);transaction.rollback()
        self.assertFalse(p.fly_fallback_attempts);self.assertIsNone(p.fly_fallback_pending)
        action=desperate_attack(p,s,foes);after=copy.deepcopy(s);after['hero']['cell']=41
        self.assertIsNone(observe_fallback(p,s,action,after))
        self.assertFalse(any(p.fly_fallback_attempts.values()))

    def test_tactical_decline_does_not_force_a_passive_swarm_recharge_wait(self):
        s,p,foes=boxed_flies()
        action=recover(p,s,foes,TacticalBlocked('attack-position','fly pressure'),distance,neighbors,line_clear)
        self.assertEqual('cell',action.action['type']);self.assertIn('last-resort strike',action.reason)

    def test_unchanged_bar_context_is_bounded_and_strict_mode_retains_admission(self):
        s,p,foes=boxed_flies()
        for foe in foes:p.fly_fallback_attempts[(40,foe['cell'],tuple(foe['health_bar']))]=3
        self.assertIsNone(desperate_attack(p,s,foes))
        p.fly_fallback_attempts.clear();p.stop_on_no_safe_action=True
        self.assertIsNone(desperate_attack(p,s,foes))


if __name__=='__main__':unittest.main()
