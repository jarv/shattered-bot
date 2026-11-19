import copy
import unittest
from unittest.mock import patch

from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.policy_decision import Decision,Intent,NoSafeAction
from tools.policy_geometry import distance,line_clear,projectile_line_clear
from tools.policy_runtime import Transaction
from tools import inventory_tactics as inventory
from tools import trap_field_tactics as traps
from tools import ranged_tactics as ranged
from tools.artifact_tactics import ARTIFACT_PRIORITY,ARTIFACT_STRATEGIES,use_artifact
from tools.chain_tactics import choose_chasm_pull
from tools.loot_completion import required_loot
from tools.room_loot import local_loot


def weapon(name='dagger',low=1,high=3,strength=10,equipped=False,identified=True):
    return {'id':name,'name':name,'identified':identified,'equipped':equipped,'quantity':1,
            'description':f'This melee weapon deals {low}-{high} damage and requires {strength} strength',
            'actions':['DROP','EQUIP']}


def gear():
    s,p=arena();s['inventory']=[weapon('sword',10,20,equipped=True),weapon()]
    return s,p


class InventoryFeedbackTests(unittest.TestCase):
    def test_only_demonstrably_weaker_comparable_gear_is_disposable(self):
        s,p=gear();self.assertTrue(inventory.inferior(s,s['inventory'][1]))
        for item in (weapon('future',20,30,18),weapon('unknown',identified=False),
                     weapon('equal',10,20),weapon('staff',0,1),weapon('ring of might',0,1),
                     weapon('light',1,3,8),weapon('equipped',equipped=True)):
            self.assertFalse(inventory.inferior(s,item),item['name'])
        special=weapon();special['description']+=' It has extra reach.'
        self.assertFalse(inventory.inferior(s,special))

    def test_potions_seeds_wands_quest_and_unknown_items_are_not_junk(self):
        s,p=gear()
        for name in ('azure potion','seed of sungrass','wand of frost','skeleton key','ankh','dried rose'):
            self.assertFalse(inventory.inferior(s,{'name':name,'identified':True,'actions':['DROP']}))

    def test_no_dropping_based_on_flat_inventory_count(self):
        s,p=gear();s['inventory'] += [{'id':str(n),'name':'azure potion','actions':['DRINK']} for n in range(30)]
        self.assertIsNone(inventory.choose(p,s,[]))

    def test_duplicate_ui_titles_are_not_selected_for_sale(self):
        s,p=gear();s['inventory'].append(dict(s['inventory'][1],id='another'))
        self.assertFalse(inventory.candidates(p,s,'DROP'))

    def test_shop_sale_is_validated_and_records_only_observed_gold_and_removal(self):
        s,p=gear();s['objects']=[{'name':'shopkeeper','cell':41}]
        action=inventory.choose(p,s,[]);self.assertEqual(41,action.action['cell'])
        s.update(status='menu',modal=True);s['ui']={'texts':['Shopkeeper'],'buttons':[{'id':'sell','label':'Sell an item'}]}
        self.assertEqual('sell',inventory.sale_menu(p,s).action['id'])
        s['ui']={'texts':['Sell an item'],'buttons':[{'id':'dagger-slot','label':'dagger'}]}
        self.assertEqual('dagger-slot',inventory.sale_menu(p,s).action['id'])
        s['ui']={'texts':['Dagger'],'buttons':[{'id':'quote','label':'Sell for 10g'}]}
        confirm=inventory.sale_menu(p,s);self.assertEqual('quote',confirm.action['id'])
        self.assertFalse(p.inventory_events)
        after=copy.deepcopy(s);after['inventory'].pop();after['hero']['gold']=s['hero'].get('gold',0)+10
        receipt=inventory.observe_accepted(p,s,confirm,after)
        self.assertEqual('sold',receipt[0]['kind']);self.assertEqual(10,receipt[0]['gold'])
        self.assertEqual('close',p.sell_plan['stage'])

    def test_wrong_sale_title_or_changed_equipment_cancels(self):
        for case in ('title','equipment'):
            s,p=gear();p.sell_plan={'stage':'quote','depth':s['depth'],'branch':0,'name':'dagger','steps':0,'bags':[]}
            s.update(status='menu',modal=True)
            s['ui']={'texts':['Dagger' if case=='equipment' else 'Sword'],'buttons':[{'id':'sell','label':'Sell for 10g'}]}
            if case=='equipment':s['inventory'][1]['equipped']=True
            self.assertEqual('back',inventory.sale_menu(p,s).action['type'])

    def test_unverified_sale_is_not_retried_or_claimed(self):
        s,p=gear();p.sell_plan={'stage':'verify','depth':s['depth'],'branch':0,'name':'dagger',
                               'steps':0,'price':10,'gold_before':s['hero'].get('gold',0),'button':'confirm'}
        receipt=inventory.observe_accepted(p,s,Decision({'type':'button','id':'confirm'},'sell'),copy.deepcopy(s))
        self.assertEqual('sale-unverified',receipt[0]['kind']);self.assertEqual('unverified',p.sell_plan['stage'])

    def test_fresh_full_pack_message_admits_one_verified_drop_and_no_repickup(self):
        s,p=gear();s['objects']=[{'cell':40,'name':'azure potion','top_item':{'name':'azure potion'}}]
        after=copy.deepcopy(s);after['ui']={'texts':["You can't carry: azure potion."],'buttons':[]}
        action=Decision({'type':'cell','cell':40},'pickup',Intent.LOOT)
        inventory.observe_accepted(p,s,action,after)
        self.assertIsNotNone(p.inventory_pressure)
        after['objects']=[]
        drop=inventory.choose(p,after,[]);self.assertEqual('DROP',drop.action['action'])
        result=copy.deepcopy(after);item=result['inventory'].pop()
        result['objects']=[{'cell':40,'name':'dagger','top_item':item}]
        receipts=inventory.observe_accepted(p,after,drop,result)
        self.assertEqual('discarded-inferior-gear',receipts[0]['kind'])
        p.loot[40]=result['objects'][0]
        self.assertNotIn(40,required_loot(p))
        self.assertFalse(p.exploration_loot_allowed(result,40,p.paths(result)))
        self.assertFalse(local_loot(p,result,{40},{40:None}))
        p.loot[40]={'top_item':{'name':'potion of healing'},'name':'potion of healing'}
        self.assertIn(40,required_loot(p))  # Never ignore a different item at the same cell.

    def test_old_full_pack_text_or_changed_inventory_does_not_trigger_cleanup(self):
        s,p=gear();s['objects']=[{'cell':40,'top_item':{'name':'azure potion'},'name':'azure potion'}]
        s['ui']={'texts':["You can't carry: azure potion."],'buttons':[]}
        inventory.observe_accepted(p,s,Decision({'type':'cell','cell':40},'pickup'),copy.deepcopy(s))
        self.assertIsNone(p.inventory_pressure)

    def test_threats_and_pending_resource_plans_preempt_disposal(self):
        for kind in ('enemy','stash'):
            s,p=gear();p.inventory_pressure={'signature':inventory.signature(s)}
            foes=[enemy('gnoll scout',41)] if kind=='enemy' else []
            if kind=='stash':p.potion_stash={'cell':30}
            self.assertIsNone(inventory.choose(p,s,foes))


class TrapFieldFeedbackTests(unittest.TestCase):
    def fixture(self):
        s,p=arena()
        for c in (43,52,61):p.tiles[c].update(terrain=18,trap='burning trap')
        action=Decision({'type':'cell','cell':41},'explore',Intent.EXPLORE)
        return s,p,action

    def test_revealed_dense_field_is_searched_before_walking_not_assumed_safe(self):
        s,p,move=self.fixture()
        for n in (1,2):
            action=traps.before_move(p,s,move,[])
            self.assertEqual({'type':'search'},action.action)
            receipt=traps.observe_accepted(p,s,action,copy.deepcopy(s))
            self.assertEqual(n,receipt['accepted_searches'])
        self.assertIsNone(traps.before_move(p,s,move,[]))
        self.assertFalse(p.walkable(43));self.assertEqual('burning trap',p.tiles[43]['trap'])

    def test_sparse_or_unobserved_fields_do_not_invent_traps(self):
        s,p,move=self.fixture();p.tiles[61].pop('trap')
        self.assertIsNone(traps.before_move(p,s,move,[]))
        p.tiles[61]['trap']='burning trap'
        for c in (43,52,61):p.tiles[c].update(visible=False,observed=False)
        self.assertIsNone(traps.before_move(p,s,move,[]))

    def test_scan_never_preempts_escape_combat_or_critical_health(self):
        for case in ('escape','combat','hp'):
            s,p,move=self.fixture();foes=[]
            if case=='escape':move.intent=Intent.RETREAT
            if case=='combat':foes=[enemy('gnoll scout',42)]
            if case=='hp':s['hero']['hp']=1
            self.assertIsNone(traps.before_move(p,s,move,foes),case)

    def test_foresight_has_a_bounded_priority_scan(self):
        s,p,move=self.fixture()
        s['inventory'].append({'name':'talisman of foresight','id':'foresight','equipped':True,'status':'50%','actions':['SCRY']})
        action=traps.before_move(p,s,move,[])
        self.assertEqual('SCRY',action.action['action']);self.assertIn(p.target,(43,52,61))

    def test_rejected_scan_proposal_does_not_consume_searches(self):
        s,p,move=self.fixture();transaction=Transaction(p,p.planner)
        traps.before_move(p,s,move,[]);transaction.rollback()
        self.assertIsNone(p.trap_scan_pending);self.assertFalse(p.trap_scan_cells)


class ArtifactFeedbackTests(unittest.TestCase):
    def test_all_known_artifacts_have_explicit_utilization_strategies(self):
        self.assertEqual(set(ARTIFACT_PRIORITY),set(ARTIFACT_STRATEGIES))
        self.assertIn('Holy Ward',ARTIFACT_STRATEGIES['holy tome'])
        self.assertIn('unlock',ARTIFACT_STRATEGIES['skeleton key'])
        self.assertFalse(any('Deferred:' in text for text in ARTIFACT_STRATEGIES.values()))

    def fixture(self):
        s,p=arena();foe=enemy('gnoll shaman',43);s['objects']=[foe]
        p.tiles[41]['terrain']=0
        chains={'id':'chains','name':'ethereal chains','equipped':True,'status':'5/5','actions':['CAST']}
        s['inventory'].append(chains)
        return s,p,foe,chains

    def test_chains_prioritize_a_grounded_enemy_chasm_pull_even_at_full_hp(self):
        s,p,foe,chains=self.fixture()
        action=use_artifact(p,s,[foe])
        self.assertEqual('CAST',action.action['action']);self.assertEqual(43,p.target)
        self.assertEqual(41,p.planner.report['chains_pull']['predicted_landing'])
        self.assertEqual(40,s['hero']['cell']);self.assertFalse(p.defeated_bosses)

    def test_chains_reject_flight_bosses_occupied_or_ground_landing_and_unknown_charges(self):
        for case in ('fly','boss','occupied','ground','charge','wall'):
            s,p,foe,chains=self.fixture()
            if case=='fly':foe['name']='vampire bat'
            if case=='boss':foe['name']='goo'
            if case=='occupied':s['objects'].append({'cell':41,'name':'sad ghost'})
            if case=='ground':p.tiles[41]['terrain']=1
            if case=='charge':chains['status']='?'
            if case=='wall':p.tiles[42]['terrain']=4
            self.assertIsNone(choose_chasm_pull(p,s,[foe],chains),case)

    def test_chains_can_make_one_safe_step_to_a_verified_pull_bank(self):
        s,p,foe,chains=self.fixture();p.tiles[41]['terrain']=1;p.tiles[42]['terrain']=0
        action=choose_chasm_pull(p,s,[foe],chains)
        self.assertEqual(Intent.REPOSITION,action.intent);self.assertEqual(1,distance(40,action.action['cell'],9))
        self.assertEqual(0,p.artifact_cooldown)
        s['hero']['cell']=action.action['cell']
        self.assertEqual('CAST',choose_chasm_pull(p,s,[foe],chains).action['action'])
        self.assertEqual(42,p.planner.report['chains_pull']['predicted_landing'])


class RangedDeathFeedbackTests(unittest.TestCase):
    def test_pit_blocks_walking_not_magic_and_does_not_count_as_cover(self):
        s,p=arena();p.tiles[41]['terrain']=0;foe=enemy('gnoll shaman',43)
        self.assertFalse(line_clear(40,43,9,p.tiles))  # Historical geometry.
        self.assertTrue(projectile_line_clear(40,43,9,p.tiles))
        self.assertTrue(p.shot_clear(s,43));self.assertTrue(p.enemy_can_see(s,foe,40))
        self.assertFalse(p.walkable(41));self.assertTrue(ranged.exposed_wait(p,s,[foe]))

    def test_short_safe_closure_is_preferred_to_long_exposed_detours(self):
        s,p=arena();s['hero'].update(hp=100,max_hp=100);s['inventory']=[]
        foe=enemy('gnoll shaman',42)
        action=ranged.choose(p,s,[foe])
        self.assertEqual(Intent.APPROACH,action.intent);self.assertEqual('close',p.ranged_plan['mode'])
        self.assertEqual(1,distance(action.action['cell'],foe['cell'],9))

    def test_cover_plan_waits_only_when_actual_ranged_geometry_is_clear(self):
        s,p=arena();foe=enemy('gnoll shaman',43)
        p.ranged_plan={'name':'gnoll shaman','mode':'cover','goal':40,'steps':1,'waits':0,'hp':s['hero']['hp']}
        with patch.object(p,'enemy_can_see',return_value=False),patch('tools.ranged_tactics.exposure',return_value={'exposure':0}):
            action=ranged.choose(p,s,[foe])
        self.assertEqual('wait',action.action['type']);self.assertIn('verified cover',action.reason)
        p.ranged_plan['hp']=s['hero']['hp']+1
        ranged.choose(p,s,[foe])
        self.assertIn(('gnoll shaman',40),p.ranged_failed_cover)

    def test_no_admitted_action_under_fire_is_typed_not_a_silent_recharge_wait(self):
        s,p=arena();s['inventory']=[];foe=enemy('gnoll shaman',43)
        with patch.object(p,'paths',return_value={40:None}),self.assertRaises(NoSafeAction):ranged.choose(p,s,[foe])


if __name__=='__main__':unittest.main()
