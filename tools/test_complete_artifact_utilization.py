import copy
import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.artifact_tactics import ARTIFACT_PRIORITY,ARTIFACT_STRATEGIES,equip_artifact,use_artifact
from tools.artifact_extensions import choose,menu,observe,seek_pickup
from tools.inventory_tactics import inferior
from tools.policy_runtime import Transaction
from tools.policy_decision import Finished,Decision,Intent
from tools.room_loot import before_room_exit
from tools.policy_runtime import Context
from tools.policy_nodes import ordinary_combat
from tools.policy_decision import TacticalBlocked
from tools.test_multi_enemy_and_fly_feedback import choke


def artifact(name,actions,status='3/5',equipped=True,**kw):
    return dict(id=name,name=name,actions=actions,status=status,equipped=equipped,
                identified=True,curse_known=True,known_cursed=False,**kw)


class CompleteArtifactTests(unittest.TestCase):
    def test_catalog_strategy_and_preservation_for_every_artifact_and_nature_form(self):
        self.assertEqual(set(ARTIFACT_PRIORITY),set(ARTIFACT_STRATEGIES))
        for name in ARTIFACT_PRIORITY:
            s,p=arena();item=artifact(name,['DROP','EQUIP'],equipped=False)
            self.assertFalse(inferior(s,item),name)
            self.assertNotIn('Deferred:',ARTIFACT_STRATEGIES[name])
            s['inventory'].append(item)
            self.assertEqual('EQUIP',equip_artifact(p,s).action['action'],name)

    def test_skeleton_key_unlocks_and_verifies_actual_door_change(self):
        s,p=arena();item=artifact('skeleton key',['INSERT']);s['inventory'].append(item);p.tiles[41]['terrain']=10
        a=choose(p,s,[]);self.assertEqual('INSERT',a.action['action']);self.assertEqual(41,p.target)
        p.target=None;p.tiles[41]['terrain']=5;observe(p,s)
        self.assertTrue(p.planner.report['artifact_outcome']['confirmed_public_effect'])
        self.assertFalse(p.loot_collection_receipts)

    def test_key_does_not_open_boss_exits_or_act_without_known_charge(self):
        for case in ('boss','branch','exit','charge','curse'):
            s,p=arena();item=artifact('skeleton key',['INSERT']);s['inventory'].append(item);p.tiles[41]['terrain']=10
            if case=='boss':s['depth']=5
            if case=='branch':s['branch']=1
            if case=='exit':p.tiles[41]['terrain']=21
            if case=='charge':item['status']='?'
            if case=='curse':item['known_cursed']=True
            self.assertIsNone(choose(p,s,[]),case)

    def test_key_can_reopen_own_door_without_charge(self):
        s,p=arena();s['inventory'].append(artifact('skeleton key',['INSERT'],status='0/3'));p.tiles[41]['terrain']=38
        self.assertEqual('INSERT',choose(p,s,[]).action['action'])

    def test_key_locks_only_an_empty_verified_choke_with_escape_space(self):
        s,p,foes=choke();s['hero'].update(cell=31,hp=10);p.update(s)
        s['inventory'].append(artifact('skeleton key',['INSERT']))
        a=choose(p,s,foes);self.assertEqual('INSERT',a.action['action']);self.assertEqual(24,p.target)
        self.assertEqual(38,p.artifact_extension_pending['expected'])
        s,p,foes=choke();s['hero'].update(cell=31,hp=10);s['objects']=foes+[enemy('gnoll scout',24)];p.update(s)
        s['inventory'].append(artifact('skeleton key',['INSERT']))
        self.assertIsNone(choose(p,s,s['objects']))

    def test_key_stages_to_an_observed_lock_not_an_unseen_or_boss_exit(self):
        s,p=arena();s['inventory'].append(artifact('skeleton key',['INSERT']));p.tiles[44]['terrain']=10
        a=choose(p,s,[]);self.assertEqual('cell',a.action['type']);self.assertIn('approach observed ordinary lock',a.reason)

    def test_rose_summon_uses_action_eligibility_and_confirms_direct_not_guessed_position(self):
        s,p=arena();rose=artifact('dried rose',['SUMMON'],status='100%');s['inventory'].append(rose)
        a=choose(p,s,[]);self.assertEqual('SUMMON',a.action['action'])
        rose['actions']=['DIRECT'];observe(p,s)
        self.assertTrue(p.planner.report['artifact_outcome']['confirmed_public_effect'])
        self.assertFalse(p.defeated_bosses)
        s,p=arena();s['inventory'].append(artifact('dried rose',['OUTFIT']))
        self.assertIsNone(choose(p,s,[]))  # Quest-ineligible: do not force summon or sacrifice gear.

    def test_rose_direct_targets_only_observed_enemy(self):
        s,p=arena();s['inventory'].append(artifact('dried rose',['DIRECT']));foe=enemy('gnoll scout',43)
        self.assertEqual('DIRECT',choose(p,s,[foe]).action['action']);self.assertEqual(43,p.target)

    def test_tome_ward_selects_exact_offered_spell_and_requires_actual_buff(self):
        s,p=arena();s['hero']['hp']=10;s['inventory'].append(artifact('holy tome',['CAST']))
        self.assertEqual('CAST',choose(p,s,[enemy('gnoll scout',42)]).action['action'])
        s['ui']={'buttons':[{'id':'ward','label':'_Holy Ward_\nGain armor'}],'texts':['Cast a spell']}
        a=menu(p,s,p.artifact_menu);self.assertEqual('ward',a.action['id'])
        s['hero']['buffs']=[{'name':'holy ward'}];observe(p,s)
        self.assertTrue(p.planner.report['artifact_outcome']['confirmed_public_effect'])

    def test_unknown_tome_ui_stops_instead_of_clicking_by_index(self):
        s,p=arena();s['ui']={'buttons':[{'id':'guess','label':'Unknown spell'}],'texts':[]}
        with self.assertRaises(Finished):menu(p,s,{'kind':'tome','steps':0})

    def test_spellbook_is_bounded_and_handled_by_named_regular_scroll_choice(self):
        s,p=arena();s['inventory'].append(artifact('unstable spellbook',['READ']))
        self.assertEqual('READ',choose(p,s,[]).action['action'])
        s['ui']={'buttons':[{'id':'base','label':'Scroll of Magic Mapping'},{'id':'exotic','label':'Scroll of Foresight'}],
                 'texts':['Select the regular or exotic version of this scroll.']}
        self.assertEqual('base',menu(p,s,p.artifact_menu).action['id'])
        self.assertEqual('discover-scroll',p.menu_plan)

    def test_instant_spellbook_effect_does_not_leave_a_stuck_menu_plan(self):
        s,p=arena();book=artifact('unstable spellbook',['READ']);s['inventory'].append(book)
        choose(p,s,[]);book['status']='2/5';observe(p,s)
        self.assertIsNone(p.artifact_menu);self.assertIsNone(p.artifact_extension_pending)
        self.assertTrue(p.planner.report['artifact_outcome']['confirmed_public_effect'])

    def test_known_curse_and_random_reading_during_threat_are_rejected(self):
        s,p=arena();book=artifact('unstable spellbook',['READ']);book['known_cursed']=True;s['inventory'].append(book)
        self.assertIsNone(choose(p,s,[]));book['known_cursed']=False
        self.assertIsNone(choose(p,s,[enemy('gnoll scout',43)]))

    def test_unconfirmed_artifact_pickup_requires_changed_bank_and_is_bounded(self):
        s,p=arena();p.loot[41]={'cell':41,'name':'skeleton key','top_item':{'name':'skeleton key'}}
        for c in p.tiles:
            if p.tiles[c]['terrain']==1:p.tiles[c]['terrain']=2  # Observed grass is valid pickup approach, not a fire-test bank.
        p.failed_moves[41]=1;p.room_loot_deferred[41]=('old context',)
        a=seek_pickup(p,s);self.assertEqual('cell',a.action['type']);self.assertNotEqual(41,a.action['cell'])
        bank=p.artifact_pickup_banks[41];s['hero']['cell']=bank
        a=seek_pickup(p,s);self.assertEqual(41,a.action['cell']);self.assertIn('changed approach',a.reason)
        self.assertIsNone(before_room_exit(p,s,a));self.assertIsNone(seek_pickup(p,s))
        self.assertFalse(p.loot_collection_receipts)

    def test_upgraded_skeleton_key_keeps_its_utilization_strategy(self):
        s,p=arena();s['inventory'].append(artifact('skeleton key +2',['INSERT']));p.tiles[41]['terrain']=10
        self.assertEqual('INSERT',choose(p,s,[]).action['action'])

    def test_rejected_artifact_activation_rolls_back_budget_and_pending_outcome(self):
        s,p=arena();s['inventory'].append(artifact('skeleton key',['INSERT']));p.tiles[41]['terrain']=10
        tx=Transaction(p,p.planner);choose(p,s,[]);tx.rollback()
        self.assertFalse(p.artifact_extension_attempts);self.assertIsNone(p.artifact_extension_pending)

    def test_no_passive_ordinary_recharge_wait_under_an_adjacent_attacker(self):
        s,p=arena();foe=enemy('gnoll scout',41);s['objects']=[foe]
        c=Context(p,s,enemies=[foe],active=[foe],engage=[foe])
        with patch.object(p,'best_attack',return_value=None),self.assertRaises(TacticalBlocked):
            ordinary_combat(c)


if __name__=='__main__':unittest.main()
