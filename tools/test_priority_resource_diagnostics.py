import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_decision import GameplayBlocked
from tools.policy_runner import run
from tools.priority_resources import choose,diagnostics
from tools.test_regular_feedback import arena


class PriorityResourceDiagnosticsTests(unittest.TestCase):
    def test_logging_does_not_admit_a_blocked_pickup(self):
        s,p=arena()
        p.loot[41]={'name':'scroll of upgrade','cell':41,
                    'top_item':{'name':'scroll of upgrade','actions':['READ']}}
        p.blocked.add(41)
        self.assertIsNone(choose(p,s,[]))
        report=p.planner.report['priority_resource']
        target=report['targets'][0]
        self.assertEqual(41,target['cell'])
        self.assertFalse(target['reachable_in_current_paths'])
        self.assertIn('blocked by prior movement bookkeeping',target['target_rejections']['reasons'])
        json.dumps(report)

    def test_observed_fire_buffers_explain_unreachable_component_boundaries(self):
        s,p=arena()
        p.loot[41]={'name':'scroll of upgrade','cell':41}
        p.fire_buffer.add(41)
        report=diagnostics(p,s)
        self.assertIn('observed eternal-fire safety buffer',
                      report['targets'][0]['target_rejections']['reasons'])
        self.assertFalse(report['targets'][0]['reachable_in_current_paths'])

    def test_veto_report_survives_without_changing_the_blocked_outcome(self):
        class BlockedPolicy(MagePolicy):
            def choose(self,s):
                self.planner.report['priority_resource']={'targets':[{'cell':41,'reachable_in_current_paths':False}]}
                raise GameplayBlocked('Observed upgrade/strength resource remains uncollected; resolve its pickup before descending')
        s,_=arena()
        api=SimpleNamespace(observation=s,step=lambda a:self.fail('Bounded block must not dispatch an action'))
        with TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            path=Path(tmp)/'decisions.jsonl'
            result=run(api,BlockedPolicy(),1,0,path,bounded=True)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual('blocked',result['outcome'])
        self.assertEqual(0,result['actions'])
        veto=next(r['policy_veto'] for r in rows if 'policy_veto' in r)
        self.assertEqual('resource-obligation',veto['kind'])
        self.assertEqual(41,veto['priority_resource']['targets'][0]['cell'])

    def test_unrelated_resource_wording_is_not_misclassified(self):
        class BlockedPolicy(MagePolicy):
            def choose(self,s):
                self.planner.report['priority_resource']={'targets':[{'cell':41}]}
                raise GameplayBlocked('Preserve accepted escape route until resources improve')
        s,_=arena()
        api=SimpleNamespace(observation=s)
        with TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            path=Path(tmp)/'decisions.jsonl'
            run(api,BlockedPolicy(),1,0,path,bounded=True)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertFalse(any('policy_veto' in r for r in rows))


if __name__=='__main__':
    unittest.main()
