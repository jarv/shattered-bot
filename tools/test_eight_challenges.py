import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tools.nine_challenge import NineChallengePolicy,CHALLENGES
from tools.test_nine_challenge import selected_mage
from tools.test_survival_bot import state
from tools.policy_decision import Finished


class EightChallengeTests(unittest.TestCase):
    def panel(self):
        s=selected_mage();s['modal']=True
        s['ui']['buttons']=[{'id':str(i),'label':name,'checked':True} for i,name in enumerate(CHALLENGES)]
        return s

    def test_on_diet_is_disabled_and_other_eight_visibly_verified(self):
        p=NineChallengePolicy(on_diet=False);p.choose(selected_mage());s=self.panel()
        a=p.choose(s)
        self.assertEqual(str(CHALLENGES.index('on diet')),a.action['id'])
        self.assertIn('disable on diet',a.reason);self.assertFalse(p.challenges_verified)
        s['ui']['buttons'][CHALLENGES.index('on diet')]['checked']=False
        self.assertEqual('back',p.choose(s).action['type'])
        self.assertEqual(8,len(p.verified_challenges));self.assertNotIn('on diet',p.verified_challenges)
        self.assertEqual('start',p.choose(selected_mage()).action['id'])
        self.assertTrue(p.pharmacophobia and p.barren_land and p.badder_bosses and p.faith_is_my_armor)

    def test_wrong_eight_checked_states_are_not_an_exact_match(self):
        p=NineChallengePolicy(on_diet=False);p.choose(selected_mage());s=self.panel()
        s['ui']['buttons'][0]['checked']=False
        a=p.choose(s)
        self.assertEqual('0',a.action['id']);self.assertFalse(p.challenges_verified)
        self.assertFalse(p.verified_challenges)

    def test_missing_duplicate_or_unknown_checkbox_state_is_rejected(self):
        for mode in ('missing','duplicate','unknown'):
            p=NineChallengePolicy(on_diet=False);p.choose(selected_mage());s=self.panel()
            if mode=='missing':s['ui']['buttons'].pop()
            elif mode=='duplicate':s['ui']['buttons'].append(dict(s['ui']['buttons'][0]))
            else:s['ui']['buttons'][2]['checked']=None
            with self.assertRaises(Finished):p.choose(s)

    def test_eight_challenge_game_cannot_start_with_boolean_only_verification(self):
        p=NineChallengePolicy(on_diet=False);p.challenges_verified=True
        with self.assertRaisesRegex(Finished,'Eight-challenge configuration'):p.choose(state())

    def test_legacy_default_remains_all_nine_for_historical_tools(self):
        p=NineChallengePolicy()
        self.assertTrue(p.on_diet);self.assertEqual(tuple(CHALLENGES),p.enabled_challenges)


if __name__=='__main__':unittest.main()
