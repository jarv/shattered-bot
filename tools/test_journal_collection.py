import copy
import unittest

from tools.collection_evidence import journal_pickup
from tools.loot_completion import observe_collected,remember_missing,required_loot
from tools.floor_metrics import FloorMetrics,snapshot
from tools.policy_decision import Decision,Intent
from tools.test_challenge_systems import ready,item


class JournalCollectionTests(unittest.TestCase):
    def encounter(self):
        before,p=ready()
        obj={'cell':23,'name':'tome of dungeon mastery','top_item':item('tome of dungeon mastery','READ')}
        before['objects']=[obj];before['ui']['texts']=[]
        after=copy.deepcopy(before);after['objects']=[];after['hero']['cell']=23
        after['ui']['texts']=['You picked up: tome of dungeon mastery.']
        action=Decision({'type':'cell','cell':23},'pickup',Intent.LOOT)
        return before,after,p,action,obj

    def test_accepted_journal_pickup_resolves_coverage_without_backpack_increase(self):
        before,after,p,action,obj=self.encounter()
        self.assertEqual(before['inventory'],after['inventory'])
        evidence=observe_collected(p,before,action,after)
        self.assertEqual('tome of dungeon mastery',evidence['name'])
        remember_missing(p,{23:obj});self.assertFalse(required_loot(p))

    def test_name_and_disappearance_alone_never_qualify(self):
        before,after,p,action,obj=self.encounter();after['ui']['texts']=[]
        observe_collected(p,before,action,after);remember_missing(p,{23:obj})
        self.assertIn(23,required_loot(p))

    def test_stale_confirmation_does_not_qualify(self):
        before,after,p,action,obj=self.encounter();before['ui']['texts']=list(after['ui']['texts'])
        self.assertIsNone(journal_pickup(before,action.action,after))

    def test_wrong_destination_still_visible_and_other_floor_rejected(self):
        for change in ('destination','visible','floor'):
            before,after,p,action,obj=self.encounter()
            if change=='destination':after['hero']['cell']=24
            elif change=='visible':after['objects']=[obj]
            else:after['depth']+=1
            self.assertIsNone(journal_pickup(before,action.action,after))

    def test_ordinary_item_cannot_use_journal_exception(self):
        before,after,p,action,obj=self.encounter();obj['top_item']['name']='pasty'
        after['ui']['texts']=['You picked up: pasty.']
        self.assertIsNone(journal_pickup(before,action.action,after))

    def test_journal_accounting_is_separate_from_backpack_units(self):
        before,after,p,action,obj=self.encounter();metrics=FloorMetrics()
        metrics.accept(snapshot(before),action.action,snapshot(after))
        floor=metrics.report()['floors'][0]
        self.assertEqual({'tome of dungeon mastery':1},floor['confirmed_journal_pickups'])
        self.assertEqual(0,floor['confirmed_ground_pickup_units'])
        self.assertTrue(floor['journal_evidence_available'])

    def test_older_snapshots_have_unknown_not_proven_zero_journal_coverage(self):
        before,after,p,action,obj=self.encounter();before.pop('ui');after.pop('ui')
        metrics=FloorMetrics();metrics.accept(snapshot(before),action.action,snapshot(after))
        self.assertFalse(metrics.report()['floors'][0]['journal_evidence_available'])


if __name__=='__main__':unittest.main()
