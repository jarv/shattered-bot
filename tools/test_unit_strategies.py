"""Unit dispatch uses public species, admitted actions and accepted transitions."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.unit_profiles import StrategyBook,OVERRIDE_STRATEGIES
from tools import unit_strategies as tactics
from tools.survival_policy import ENEMIES,SurvivalPolicy
from tools.mage_policy import MagePolicy
from tools.nine_challenge import NineChallengePolicy
from tools.policy_runtime import Transaction,Context
from tools.policy_decision import Decision,Intent,NoSafeAction
from tools.policy_runner import run
from tools.policy_geometry import distance,neighbors,line_clear
from tools.survival_bot import configured_policy
from tools.challenge_combat import enemy_line
from tools.garden_tactics import GARDEN_DESCRIPTION
from tools.test_regular_feedback import arena


def enemy(name,cell=42,**fields):
    return dict(name=name,cell=cell,**fields)


class UnitProfileTests(unittest.TestCase):
    def test_all_recognized_units_have_explicit_profiles(self):
        book=StrategyBook()
        for name in ENEMIES:
            with self.subTest(name=name):
                profile=book.profile(enemy(name))
                self.assertNotEqual('unknown',profile.strategy)
                self.assertEqual(name,profile.name)

    def test_bosses_and_ghost_units_have_individual_strategies(self):
        book=StrategyBook()
        for name in ('goo','tengu','dm-300','king of dwarves','yog-dzewa'):
            self.assertEqual('boss:'+name,book.profile(enemy(name)).strategy)
        for name in ('fetid rat','gnoll trickster','great crab'):
            self.assertEqual('quest:'+name,book.profile(enemy(name)).strategy)
        self.assertEqual('boss:yog-dzewa',book.profile(enemy('bright fist')).strategy)

    def test_flight_and_ground_capabilities_do_not_depend_on_overrides(self):
        book=StrategyBook({'vampire bat':'melee','gnoll scout':'flying-melee'})
        for name in ('vampire bat','golden bee','swarm of flies','wraith','evil eye','fire elemental','crystal wisp'):
            self.assertFalse(book.profile(enemy(name)).triggers_ground_plants,name)
        self.assertTrue(book.profile(enemy('gnoll scout')).triggers_ground_plants)
        self.assertEqual('stationary',book.profile(enemy('dm-201')).movement)

    def test_unknown_species_are_not_invented_ground_units(self):
        p=StrategyBook().describe(enemy('unrecognized foe'))
        self.assertEqual('unknown',p['strategy']);self.assertEqual('unknown',p['movement'])
        self.assertFalse(p['triggers_ground_plants'])
        self.assertIn('not hidden',p['evidence'])

    def test_overrides_are_copied_and_frozen_for_transactions(self):
        overrides={'sewer crab':'melee'};book=StrategyBook(overrides);overrides.clear()
        self.assertEqual('melee',book.profile(enemy('sewer crab')).strategy)
        self.assertIs(book,copy.deepcopy(book))
        with self.assertRaises(TypeError):book.overrides['sewer crab']='thief'
        with self.assertRaises(FrozenInstanceError):book.profile(enemy('sewer crab')).movement='flying'

    def test_invalid_and_protected_overrides_are_rejected(self):
        for overrides in ([],{'no such mob':'melee'},{'gnoll scout':'execute'},
                          {'gnoll scout':[]},{'gnoll scout':None}):
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):StrategyBook(overrides)
        book=StrategyBook()
        for name in ENEMIES:
            if book.profile(enemy(name)).protected:
                with self.subTest(name=name),self.assertRaises(ValueError):StrategyBook({name:'melee'})

    def test_all_exposed_ordinary_groups_can_be_selected(self):
        for strategy in OVERRIDE_STRATEGIES:
            self.assertEqual(strategy,StrategyBook({'gnoll scout':strategy}).profile(enemy('gnoll scout')).strategy)

    def test_thieves_ranged_and_stationary_units_do_not_get_melee_funnels(self):
        book=StrategyBook()
        for name in ('crazy thief','crystal mimic','dm-100','demon spawner','great crab'):
            self.assertFalse(book.allows_funnel([enemy(name)]))
        self.assertTrue(book.allows_funnel([enemy('gnoll scout'),enemy('vampire bat')]))


class UnitAttackTests(unittest.TestCase):
    def test_ranged_filter_excludes_high_damage_melee_without_disabling_it(self):
        s,p=arena();target=enemy('sewer crab',41)
        s['inventory'].append({'id':'sword','name':'greatsword','equipped':True,
            'actions':[],'description':'This melee weapon deals 100-200 damage and requires 10 strength'})
        for policy in (p,SurvivalPolicy()):
            policy.update(s)
            self.assertEqual('cell',policy.best_attack(s,target).action['type'])
            action=policy.best_attack(s,target,allowed_kinds={'magic','thrown'})
            self.assertEqual('ZAP',action.action['action'])
            self.assertIsNone(policy.best_attack(s,target,allowed_kinds=set()))

    def test_filter_does_not_override_attack_admission(self):
        s,p=arena();target=enemy('sewer crab',41)
        with patch.object(p,'attack_kind_allowed',return_value=False):
            self.assertIsNone(p.best_attack(s,target,allowed_kinds={'magic','thrown'}))
        with patch.object(p,'target_allowed',return_value=False):
            self.assertIsNone(p.best_attack(s,target,allowed_kinds={'magic','thrown'}))
        with patch.object(p,'shot_clear',return_value=False):
            self.assertIsNone(p.best_attack(s,target,allowed_kinds={'magic','thrown'}))

    def test_challenge_magic_immunity_remains_enforced(self):
        from tools.challenge_rules import ChallengeRules
        s,_=arena();p=MagePolicy(rules=ChallengeRules(hostile_champions=True));p.update(s)
        target=enemy('gnoll scout',41,description='An antimagic champion')
        self.assertIsNone(p.best_attack(s,target,allowed_kinds={'magic'}))

    def test_garden_does_not_hide_hero_but_smoke_does(self):
        s,p=arena();foe=enemy('dm-100',43);pos=s['hero']['cell']
        p.tiles[pos]['effects']=[GARDEN_DESCRIPTION]
        self.assertTrue(enemy_line(p,foe,pos,9,line_clear))
        p.tiles[pos]['effects']=['A cloud of thick black smoke is swirling here.']
        self.assertFalse(enemy_line(p,foe,pos,9,line_clear))

    def test_regular_smoke_geometry_refreshes_without_enabling_challenge_pressure(self):
        s,p=arena();foe=enemy('dm-100',43)
        tile=next(t for t in s['map']['cells'] if t['cell']==41)
        tile['effects']=['A cloud of thick black smoke is swirling here.'];p.update(s)
        self.assertFalse(p.enemy_can_see(s,foe,40))
        self.assertEqual(0,p.challenge_combat.sight_inputs)
        tile['effects']=[GARDEN_DESCRIPTION];p.update(s)
        self.assertTrue(p.enemy_can_see(s,foe,40))

    def test_ground_plant_lure_is_not_used_for_a_flyer(self):
        from tools.seed_tactics import choose_seed
        for name,expected in (('gnoll scout',True),('vampire bat',False)):
            s,p=arena();foe=enemy(name,43)
            s['inventory']=[{'id':'seed','name':'seed of sorrowmoss','actions':['PLANT','THROW']}]
            with patch.object(p,'walkable',side_effect=lambda cell,*args:cell in {40,41,42}):
                action=choose_seed(p,s,[foe],distance,neighbors)
            self.assertEqual(expected,action is not None)

    def test_fast_melee_prefers_admitted_range_and_flyers_can_still_take_melee(self):
        s,p=arena();foe=enemy('sewer crab',41)
        self.assertEqual('ZAP',tactics.choose(p,s,[foe]).action['action'])
        self.assertEqual('ranged-first',p.planner.report['unit_strategy_selection']['strategy'])
        s['inventory']=[]
        self.assertEqual('cell',p.best_attack(s,enemy('vampire bat',41)).action['type'])

    def test_selected_target_is_used_by_shared_combat_fallback(self):
        from tools import policy_nodes
        s,p=arena();foes=[enemy('gnoll scout',41),enemy('sewer crab',49)]
        c=Context(p,s,enemies=foes,active=foes,engage=foes)
        p.planner.report['unit_target']=49
        with patch.object(p,'best_attack',return_value=Decision({'type':'wait'},'test')) as attack:
            policy_nodes.ordinary_combat(c)
        self.assertEqual(49,attack.call_args.args[1]['cell'])

    def test_mixed_targets_prefer_observed_damage_before_group_urgency(self):
        s,p=arena();rat=enemy('marsupial rat',41);crab=enemy('sewer crab',49)
        p.incoming_damage_samples[('marsupial rat',None)]={'count':2,'hp_loss':20}
        p.incoming_damage_samples[('sewer crab',None)]={'count':2,'hp_loss':2}
        with patch.object(tactics,'dedicated',return_value=Decision({'type':'wait'},'test')):
            tactics.choose(p,s,[crab,rat])
        self.assertEqual(41,p.planner.report['unit_target'])


class UnitPursuitTests(unittest.TestCase):
    def fixture(self):
        s,p=arena();s['inventory']=[]
        foe=enemy('crazy thief',43);s['objects']=[foe]
        return s,p,foe

    def test_visible_lone_thief_interception_is_bounded_and_counts_only_acceptance(self):
        s,p,foe=self.fixture()
        for _ in range(4):
            action=tactics.thief(p,s,[foe],foe)
            self.assertEqual(Intent.APPROACH,action.intent)
            count=p.unit_pursuit_moves['crazy thief']
            after=copy.deepcopy(s);after['hero']['cell']=action.action['cell']
            receipt=tactics.observe_accepted(p,s,action,after)
            self.assertEqual(count+1,receipt['accepted_movements'])
            self.assertIsNone(tactics.observe_accepted(p,s,action,after))
        self.assertIsNone(tactics.thief(p,s,[foe],foe))
        self.assertNotIn('id',receipt)

    def test_failed_or_unrelated_moves_do_not_consume_budget(self):
        for case in ('unchanged','depth','branch','intent','action'):
            s,p,foe=self.fixture();action=tactics.thief(p,s,[foe],foe)
            after=copy.deepcopy(s);after['hero']['cell']=action.action['cell']
            if case=='unchanged':after['hero']['cell']=s['hero']['cell']
            if case=='depth':after['depth']+=1
            if case=='branch':after['branch']=1
            if case=='intent':action.intent=Intent.LOOT
            if case=='action':action.action={'type':'wait'}
            self.assertIsNone(tactics.observe_accepted(p,s,action,after),case)
            self.assertEqual(0,p.unit_pursuit_moves['crazy thief'])

    def test_rejection_transaction_restores_pending_movement_and_budgets(self):
        s,p,foe=self.fixture();transaction=Transaction(p,p.planner)
        action=tactics.thief(p,s,[foe],foe)
        self.assertIsNotNone(p.unit_pending_movement)
        transaction.rollback()
        self.assertIsNone(p.unit_pending_movement)
        self.assertEqual(0,p.unit_pursuit_moves['crazy thief'])
        self.assertIsNotNone(tactics.thief(p,s,[foe],foe))

    def test_floor_reset_releases_only_floor_local_budgets(self):
        s,p,foe=self.fixture();p.unit_pursuit_moves['crazy thief']=4;p.unit_cover_moves['dm-100']=4
        p.memory.reset_floor(s['hero']['cell'])
        self.assertFalse(p.unit_pursuit_moves);self.assertFalse(p.unit_cover_moves)
        self.assertEqual('thief',p.unit_strategies.profile(foe).strategy)

    def test_no_chase_when_wounded_crowded_or_without_a_route(self):
        for case in ('wounded','crowded','blocked'):
            s,p,foe=self.fixture();foes=[foe]
            if case=='wounded':s['hero']['hp']=1
            if case=='crowded':foes.append(enemy('gnoll scout',42))
            if case=='blocked':p.tiles={s['hero']['cell']:p.tiles[s['hero']['cell']]}
            self.assertIsNone(tactics.thief(p,s,foes,foe),case)

    def test_pursuit_exhaustion_is_typed_for_best_effort_continuation(self):
        s,p,foe=self.fixture();p.unit_pursuit_moves['crazy thief']=4
        with self.assertRaises(NoSafeAction):tactics.choose(p,s,[foe])
        self.assertFalse(p.stop_on_no_safe_action)

    def test_ranged_interception_is_preferred_to_chase(self):
        s,p=arena();foe=enemy('crazy thief',43)
        action=tactics.thief(p,s,[foe],foe)
        self.assertEqual('ZAP',action.action['action']);self.assertIsNone(p.unit_pending_movement)

    def test_ranged_cover_commits_a_separate_plan_not_a_thief_chase(self):
        s,p=arena();foe=enemy('gnoll shaman',43)
        with patch.object(p,'enemy_can_see',side_effect=lambda state,target,cell:cell==40), \
                patch('tools.ranged_tactics.exposure',return_value={'exposure':0}):
            action=tactics.ranged(p,s,[foe],foe)
        self.assertEqual(Intent.RETREAT,action.intent)
        self.assertEqual('cover',p.ranged_plan['mode'])
        self.assertFalse(p.unit_pursuit_moves);self.assertIsNone(p.unit_pending_movement)

    def test_cover_budget_and_exposed_first_steps_do_not_create_endless_lures(self):
        s,p=arena();foe=enemy('dm-100',43)
        p.unit_cover_moves['dm-100']=4
        with patch.object(p,'enemy_can_see',side_effect=lambda state,target,cell:cell==40):
            action=tactics.ranged(p,s,[foe],foe)
        self.assertEqual('ZAP',action.action['action']);self.assertIsNone(p.unit_pending_movement)


class UnitIntegrationTests(unittest.TestCase):
    def test_regular_combat_selects_registry_leaf_and_public_strategy(self):
        s,p=arena();s['objects']=[enemy('sewer crab',41)]
        action=p.choose(s)
        self.assertEqual('unit-engagement',action.controller)
        self.assertEqual('ranged-first',p.planner.report['unit_strategy_selection']['strategy'])
        self.assertEqual(41,p.target)

    def test_admitted_sleeper_still_has_a_reported_strategy(self):
        s,p=arena();s['objects']=[enemy('gnoll scout',41,sleeping=True)]
        action=p.choose(s)
        self.assertIn('gnoll scout',str(p.planner.report['unit_engagements']))
        self.assertEqual('melee',p.planner.report['unit_strategy_selection']['strategy'])

    def test_safety_preempts_dispatch_and_reports_all_observed_profiles(self):
        s,p=arena();s['objects']=[enemy('crazy thief',43),enemy('swarm of flies',49)]
        s['danger_cells']=[40]
        with patch.object(tactics,'choose',side_effect=AssertionError('must not dispatch during warning')):
            action=p.choose(s)
        self.assertEqual('warning-escape',action.controller)
        self.assertEqual({'thief','fly-swarm'},{e['strategy'] for e in p.planner.report['unit_engagements']})
        self.assertIn('preempt',p.planner.report['unit_strategy_selection']['status'])

    def test_healing_preempts_unit_interception(self):
        s,p=arena();s['hero']['hp']=2;s['objects']=[enemy('crazy thief',43)]
        s['inventory'].append({'id':'heal','name':'potion of healing','actions':['DRINK']})
        with patch.object(tactics,'choose',side_effect=AssertionError('heal first')):
            action=p.choose(s)
        self.assertEqual('heal',action.action['id'])

    def test_bosses_delegate_without_ordinary_override_execution(self):
        s,p=arena()
        with patch.object(tactics,'dedicated',side_effect=AssertionError('boss owns combat')):
            self.assertIsNone(tactics.choose(p,s,[enemy('goo')]))
        self.assertEqual('boss:goo',p.planner.report['unit_strategy_selection']['strategy'])

    def test_quest_controller_runs_once_not_also_in_legacy_override(self):
        s,p=arena();foe=enemy('fetid rat',43)
        with patch.object(tactics,'quest_combat',return_value=Decision({'type':'wait'},'quest')) as quest:
            self.assertIsNone(p.combat_override(s,[foe]))
            tactics.choose(p,s,[foe])
        quest.assert_called_once()

    def test_specialized_dispatch_delegates_each_protected_group(self):
        s,p=arena()
        for name,handler in (('sewer snake','snake_combat'),('wraith','wraith_combat')):
            with patch.object(p,handler,return_value=Decision({'type':'wait'},'special')) as special:
                tactics.choose(p,s,[enemy(name)])
                special.assert_called_once()
        for name,handler in (('necromancer','choose_necromancer'),('crystal mimic','crystal_mimic'),
                             ('mimic','fight_mimic'),('swarm of flies','fly_escape')):
            with patch.object(tactics,handler,return_value=Decision({'type':'wait'},'special')) as special:
                tactics.choose(p,s,[enemy(name)])
                special.assert_called_once()

    def test_legacy_preset_and_primitive_policy_keep_old_dispatch(self):
        self.assertFalse(NineChallengePolicy().unit_strategies_enabled)
        self.assertFalse(getattr(SurvivalPolicy(),'unit_strategies_enabled',False))

    def test_cli_loads_validated_json_without_game_side_effects(self):
        args=SimpleNamespace(challenge_preset=None,challenge=[],disable_challenge=[],without_on_a_diet=False,
                             goal='survival',engine='legacy',seed=None)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'strategies.json';args.unit_strategies=str(path)
            for data in ('{bad',json.dumps({'goo':'melee'}),json.dumps({'gnoll scout':[]})):
                path.write_text(data)
                with self.assertRaises(ValueError):configured_policy(args)
            path.write_text(json.dumps({'sewer crab':'melee'}))
            p=configured_policy(args)
            self.assertEqual('melee',p.unit_strategies.profile(enemy('sewer crab')).strategy)
            self.assertFalse(p.rules.enabled_challenges)

    def test_runner_logs_only_confirmed_thief_movements_and_configuration(self):
        s,p=arena();s['inventory']=[];s['objects']=[enemy('crazy thief',43)]
        class API:
            observation=s
            def step(self,action):
                after=copy.deepcopy(self.observation);after['hero']['cell']=action['cell']
                self.observation=after;return after
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'log.jsonl';result=run(API(),p,1,0,path,bounded=True);records=path.read_text()
        self.assertIn('observed_unit_movement',records)
        self.assertIn('unit_strategy_selection',records)
        self.assertEqual(1,p.unit_pursuit_moves['crazy thief'])
        self.assertTrue(result['unit_strategies']['enabled'])


if __name__=='__main__':unittest.main()
