"""Normal defaults, independent challenge toggles, and verified startup masks."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tools.challenge_rules import ChallengeRules,CHALLENGES,CHALLENGE_OPTIONS,configured_rules
from tools.mage_policy import MagePolicy
from tools.nine_challenge import NineChallengePolicy
from tools.survival_bot import configured_policy
from tools.survival_policy import SurvivalPolicy
from tools.policy_decision import Decision,Finished,Intent
from tools.policy_geometry import distance,neighbors
from tools.policy_runner import run
from tools.seed_tactics import choose_seed
from tools.consumable_tactics import choose_consumable
from tools.drop_tactics import recover_drop
from tools.shop_tactics import priority
from tools.test_nine_challenge import selected_mage
from tools.test_survival_bot import state,fully_known


def verified(rules=None):
    p=MagePolicy(rules=rules)
    p.choose(selected_mage())
    panel=selected_mage();panel['modal']=True
    panel['ui']['buttons']=[{'id':str(i),'label':name,'checked':name in p.enabled_challenges}
                            for i,name in enumerate(CHALLENGES)]
    assert p.choose(panel).action['type']=='back'
    return p


class ChallengeRuleConfigTests(unittest.TestCase):
    def test_default_has_no_challenges_or_special_rule_flags(self):
        p=MagePolicy()
        self.assertEqual('regular',p.rules.mode)
        self.assertFalse(p.enabled_challenges)
        self.assertFalse(any(p.rules.as_dict().values()))
        for field in p.rules.as_dict():self.assertFalse(getattr(p,field))

    def test_each_flag_enables_exactly_one_challenge(self):
        for option,label in zip(CHALLENGE_OPTIONS,CHALLENGES):
            rules=configured_rules(enable=[option])
            self.assertEqual((label,),rules.enabled_challenges)
            self.assertEqual(1,sum(rules.as_dict().values()))

    def test_preset_can_disable_one_rule_without_implicit_dependencies(self):
        rules=configured_rules('all-nine',disable=['on-diet'])
        self.assertEqual('eight-without-on-diet',rules.mode)
        self.assertFalse(rules.on_diet)
        self.assertEqual(8,len(rules.enabled_challenges))
        self.assertFalse(configured_rules(enable=['badder-bosses']).combat_pressure)

    def test_validation_and_immutability(self):
        with self.assertRaises(ValueError):ChallengeRules(pharmacophobia=1)
        with self.assertRaises(ValueError):configured_rules(enable=['unknown'])
        with self.assertRaises(ValueError):configured_rules(enable=['on-diet'],disable=['on-diet'])
        with self.assertRaises(ValueError):ChallengeRules.preset('unknown')
        with self.assertRaises(FrozenInstanceError):ChallengeRules().on_diet=True
        with self.assertRaises(AttributeError):MagePolicy().barren_land=True

    def test_legacy_policy_is_an_explicit_compatibility_preset(self):
        self.assertEqual('all-nine',NineChallengePolicy().rules.mode)
        self.assertEqual('eight-without-on-diet',NineChallengePolicy(on_diet=False).rules.mode)


class ConfiguredStartupTests(unittest.TestCase):
    def test_regular_start_turns_saved_challenge_setting_off(self):
        p=MagePolicy();p.choose(selected_mage());s=selected_mage();s['modal']=True
        s['ui']['buttons']=[{'id':str(i),'label':n,'checked':True} for i,n in enumerate(CHALLENGES)]
        for i in range(9):
            a=p.choose(s);self.assertEqual(str(i),a.action['id'])
            self.assertFalse(p.challenges_verified)
            s['ui']['buttons'][i]['checked']=False
        self.assertEqual('back',p.choose(s).action['type'])
        self.assertTrue(p.challenges_verified);self.assertEqual((),p.verified_challenges)
        self.assertEqual('start',p.choose(selected_mage()).action['id'])

    def test_single_challenge_start_verifies_exact_requested_mask(self):
        p=verified(ChallengeRules(barren_land=True))
        self.assertEqual(('barren land',),p.verified_challenges)
        self.assertFalse(p.pharmacophobia)
        self.assertEqual('start',p.choose(selected_mage()).action['id'])

    def test_even_regular_game_requires_visible_ui_verification(self):
        with self.assertRaises(Finished):MagePolicy().choose(state())
        p=MagePolicy();p.choose(selected_mage());s=selected_mage();s['modal']=True
        s['ui']['buttons']=[{'id':'0','label':CHALLENGES[0],'checked':False}]
        with self.assertRaises(Finished):p.choose(s)

    def test_custom_and_all_nine_cannot_claim_a_different_verified_set(self):
        for rules in (ChallengeRules.preset('all-nine'),ChallengeRules(on_diet=True)):
            p=MagePolicy(rules=rules);p.challenges_verified=True
            with self.assertRaises(Finished):p.choose(state())


class ConfiguredRuleAdmissionTests(unittest.TestCase):
    def encounter(self,rules=None):
        p=verified(rules);s=fully_known(state());p.update(s)
        return s,p

    def test_healing_and_planting_are_normal_by_default_and_independently_gated(self):
        heal={'name':'potion of healing','actions':['DRINK']}
        seed={'name':'seed of sungrass','actions':['PLANT','THROW']}
        for rules,can_heal,can_plant in ((ChallengeRules(),True,True),
                (ChallengeRules(pharmacophobia=True),False,True),
                (ChallengeRules(barren_land=True),True,False)):
            p=MagePolicy(rules=rules)
            self.assertEqual(can_heal,p.item_action_allowed(heal,'DRINK'))
            self.assertEqual(can_plant,p.item_action_allowed(seed,'PLANT'))
            self.assertEqual(can_plant,p.item_action_allowed(seed,'THROW'))

    def test_regular_game_actually_drinks_known_healing(self):
        s,p=self.encounter();s['hero']['hp']=3
        s['inventory'].append({'id':'heal','name':'potion of healing','actions':['DRINK']})
        action=p.choose(s)
        self.assertEqual('heal',action.action.get('id'))
        self.assertEqual('DRINK',action.action.get('action'))

    def test_regular_game_can_plant_sungrass(self):
        s,p=self.encounter();s['hero']['hp']=8
        s['inventory'].append({'id':'seed','name':'seed of sungrass','actions':['PLANT']})
        self.assertEqual('PLANT',choose_seed(p,s,[],distance,neighbors).action['action'])

    def test_normal_unknown_potion_discovery_is_not_vetoed_by_pharmacophobia_rules(self):
        s,p=self.encounter();s['hero']['strength']=10
        p.visits.update(p.tiles.keys());p.exhausted.update(p.tiles)
        potion={'id':'unknown','name':'bistre potion','actions':['DRINK']}
        s['inventory'].append(potion)
        self.assertTrue(p.item_action_allowed(potion,'DRINK'))
        action=choose_consumable(p,s,[],distance,neighbors)
        self.assertIsNone(action)  # Normal discovery now waits for admitted descent.
        next(t for t in s['map']['cells'] if t['cell']==s['hero']['cell'])['terrain']=29
        p.update(s)
        from tools.descent_potions import begin
        action=begin(p,s)
        self.assertEqual('DRINK',action.action['action'])
        self.assertEqual('unknown',action.action['id'])
        challenged=MagePolicy(rules=ChallengeRules(pharmacophobia=True))
        self.assertFalse(challenged.item_action_allowed(potion,'DRINK'))
        challenged.potion_probe_permit=('unknown','bistre potion')
        self.assertTrue(challenged.item_action_allowed(potion,'DRINK'))

    def test_ordinary_drop_recovery_can_use_a_known_cleansing_seed(self):
        s,p=self.encounter();s['depth']=2;s['hero']['buffs']=[{'name':'bleeding'}]
        s['inventory'].append({'id':'seed','name':'seed of mageroyal','actions':['PLANT']})
        p.update(s);p.drop_plan={'depth':1,'steps':0}
        self.assertEqual('PLANT',recover_drop(p,s,[],distance,neighbors).action['action'])

    def test_challenge_combat_is_not_entered_in_regular_mode(self):
        s,p=self.encounter()
        with patch.object(p.challenge_combat,'choose',side_effect=AssertionError('challenge combat disabled')):
            self.assertIsNone(p.challenge_withdrawal(s,[{'name':'marsupial rat','cell':25}]))
        with patch.object(p.challenge_combat,'observe',side_effect=AssertionError('challenge tracking disabled')):
            p.update(s)

    def test_champions_alone_do_not_enable_ordinary_swarm_withdrawal(self):
        s,p=self.encounter(ChallengeRules(hostile_champions=True))
        with patch.object(p.challenge_combat,'choose',side_effect=AssertionError('ordinary swarm logic disabled')):
            self.assertIsNone(p.challenge_withdrawal(s,[{'name':'marsupial rat','cell':25}]))

    def test_swarm_flag_explicitly_enters_pressure_controller(self):
        s,p=self.encounter(ChallengeRules(swarm_intelligence=True))
        with patch.object(p.challenge_combat,'choose',return_value=None) as choose:
            p.challenge_withdrawal(s,[{'name':'marsupial rat','cell':25}])
            choose.assert_called_once()

    def test_darkness_torch_logic_is_independent_of_healing_restriction(self):
        for rules,lights in ((ChallengeRules(),False),(ChallengeRules(pharmacophobia=True),False),
                             (ChallengeRules(into_darkness=True),True)):
            s,p=self.encounter(rules)
            s['inventory'].append({'id':'torch','name':'torch','actions':['LIGHT']})
            a=p.preparation(s,[])
            self.assertEqual(lights,bool(a and a.action.get('action')=='LIGHT'))
        self.assertIsNone(priority('torch',[],pharmacophobia=True))
        self.assertIsNotNone(priority('torch',[],into_darkness=True))

    def test_armor_and_meal_metadata_are_not_forced_to_challenge_settings(self):
        s,p=self.encounter()
        with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'wait'},'observe',Intent.OTHER)) as base:
            p.choose(s)
        self.assertFalse(any(base.call_args.args[0]['policy_rules'].values()))

    def test_regular_recovery_and_search_are_not_challenge_scarcity_budgets(self):
        s,p=self.encounter()
        self.assertEqual(24,p.recovery_limit(s,False))
        self.assertEqual(40,p.search_limit(s,40,True))
        self.assertFalse(p.badder_bosses)

    def test_mode_and_all_config_flags_are_in_audit_result(self):
        p=verified();s=fully_known(state())
        api=SimpleNamespace(observation=s)
        with tempfile.TemporaryDirectory() as temp,patch.object(MagePolicy,'choose',side_effect=Finished('blocked','test stop')):
            result=run(api,p,1,0,Path(temp)/'observations.jsonl',bounded=True)
        self.assertEqual('regular',result['challenge_mode'])
        self.assertEqual([],result['enabled_challenges'])
        self.assertFalse(any(result['challenge_rules'].values()))


class ConfiguredCLITests(unittest.TestCase):
    def args(self,**overrides):
        values=dict(goal='survival',engine='legacy',seed=None,challenge_preset=None,
                    challenge=[],disable_challenge=[],without_on_a_diet=False)
        values.update(overrides);return SimpleNamespace(**values)

    def test_default_cli_factory_is_regular_and_random(self):
        p=configured_policy(self.args())
        self.assertIsInstance(p,MagePolicy)
        self.assertFalse(p.enabled_challenges)
        self.assertIsNone(p.requested_seed)

    def test_cli_enables_and_disables_rules_without_editing_source(self):
        p=configured_policy(self.args(challenge=['barren-land','badder-bosses']))
        self.assertEqual(('badder bosses','barren land'),p.enabled_challenges)
        p=configured_policy(self.args(challenge_preset='all-nine',disable_challenge=['on-diet']))
        self.assertEqual(8,len(p.enabled_challenges));self.assertFalse(p.on_diet)

    def test_regular_override_of_legacy_launcher_and_seed_support(self):
        p=configured_policy(self.args(challenge_preset='regular',seed='ABC-DEF-GHI'),NineChallengePolicy)
        self.assertFalse(p.enabled_challenges);self.assertEqual('ABC-DEF-GHI',p.requested_seed)

    def test_legacy_opt_in_and_conflicting_options(self):
        self.assertEqual(9,len(configured_policy(self.args(),NineChallengePolicy).enabled_challenges))
        self.assertEqual(8,len(configured_policy(self.args(without_on_a_diet=True)).enabled_challenges))
        with self.assertRaises(ValueError):
            configured_policy(self.args(without_on_a_diet=True,challenge=['barren-land']))
