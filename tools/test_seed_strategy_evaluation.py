import copy
import unittest
from unittest.mock import patch
from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.policy_geometry import distance
from tools.policy_runtime import Transaction
from tools.policy_runtime import Context
from tools.policy_nodes import seed_preparation
from tools.artifact_tactics import use_artifact
from tools.seed_strategies import choose,observe
from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import neighbors,line_clear


def corridor(kind='blindweed',species='gnoll scout',gap=4):
    s,_=arena();s['hero'].update(cell=31,hp=10)
    s['evaluation_stats']={'elapsed_turns':0}
    s['map']={'width':15,'height':5,'cells':[{'cell':c,'terrain':1 if c//15==2 and 1<=c%15<=13 else 4,
                'visible':True,'observed':True} for c in range(75)]}
    s['objects']=[enemy(species,31+gap)]
    s['inventory'].append({'id':kind,'name':'seed of '+kind,'quantity':1,'actions':['PLANT','THROW']})
    p=verified();p.update(s)
    return s,p


class SeedStrategyEvaluationTests(unittest.TestCase):
    def test_lone_pursuer_can_use_carried_blindweed_without_sorrowmoss(self):
        s,p=corridor();a=choose(p,s,s['objects'])
        self.assertEqual('THROW',a.action['action']);self.assertEqual('blindweed',a.action['id'])
        self.assertNotEqual(s['objects'][0]['cell'],p.target)

    def test_seed_preparation_can_preempt_ordinary_unit_zap_but_not_adjacent_pressure(self):
        s,p=corridor('earthroot');a=p.choose(s)
        self.assertEqual('seed-preparation',a.controller);self.assertEqual('PLANT',a.action['action'])
        s,p=corridor('earthroot',gap=1)
        self.assertIsNone(choose(p,s,s['objects']))

    def test_fast_enemy_requires_larger_two_turn_margin(self):
        s,p=corridor('earthroot','sewer crab',gap=4)
        self.assertIsNone(choose(p,s,s['objects']))
        s,p=corridor('earthroot','sewer crab',gap=6)
        self.assertEqual('PLANT',choose(p,s,s['objects']).action['action'])

    def test_actual_plant_and_buff_are_observed_not_assumed(self):
        s,p=corridor('earthroot');before=copy.deepcopy(s);a=choose(p,s,s['objects'])
        s['inventory']=[i for i in s['inventory'] if i['id']!='earthroot']
        tile=next(t for t in s['map']['cells'] if t['cell']==31);tile['plant']='Earthroot'
        s['evaluation_stats']['elapsed_turns']=1
        receipt=observe(p,before,a,s)
        self.assertTrue(receipt['plant_observed']);self.assertEqual(1,p.seed_attempts['earthroot'])
        s['objects'][0]['cell']=34;p.update(s)
        activation=choose(p,s,s['objects']);self.assertEqual({'type':'cell','cell':31},activation.action)
        tile.pop('plant');s['hero']['buffs']=[{'name':'herbal armor'}];p.update(s)
        choose(p,s,s['objects'])
        self.assertTrue(p.planner.report['seed_activation']['observed_buff'])

    def test_cooldown_uses_public_turns_not_number_of_policy_calls(self):
        s,p=corridor();p.seed_ready_at['blindweed']=10;s['evaluation_stats']['elapsed_turns']=3
        for _ in range(5):self.assertIsNone(choose(p,s,s['objects']))
        s['evaluation_stats']['elapsed_turns']=11
        self.assertEqual('THROW',choose(p,s,s['objects']).action['action'])

    def test_one_seed_cooldown_does_not_block_other_seed_cleansing(self):
        s,p=corridor('mageroyal');s['objects']=[];s['hero']['buffs']=[{'name':'poisoned'}]
        p.seed_ready_at['blindweed']=99
        self.assertEqual('mageroyal',choose(p,s,[]).action['id'])

    def test_flying_targets_do_not_trigger_ground_seed_traps(self):
        s,p=corridor('blindweed','swarm of flies')
        self.assertIsNone(choose(p,s,s['objects']))

    def test_poison_is_not_spent_on_known_undead_guard(self):
        s,p=corridor('sorrowmoss','prison guard');p.ranged_plan={'mode':'cover','goal':31}
        with patch.object(p,'enemy_can_see',return_value=False):
            self.assertIsNone(choose(p,s,s['objects']))

    def test_icecap_avoids_hero_and_known_loot_in_freezing_area(self):
        s,p=corridor('icecap');a=choose(p,s,s['objects'])
        self.assertEqual('THROW',a.action['action']);self.assertGreater(distance(31,p.target,15),1)
        s,p=corridor('icecap');p.loot[34]={'name':'potion','top_item':{'name':'azure potion'}}
        self.assertIsNone(choose(p,s,s['objects']))

    def test_firebloom_requires_observed_isolated_nonflammable_area(self):
        s,p=corridor('firebloom');self.assertEqual('THROW',choose(p,s,s['objects']).action['action'])
        s,p=corridor('firebloom');p.tiles[33]['terrain']=2
        self.assertIsNone(choose(p,s,s['objects']))
        s,p=corridor('firebloom');p.tiles.pop(19)
        self.assertIsNone(choose(p,s,s['objects']))

    def test_stormvine_has_inventory_aware_control_fallback(self):
        s,p=corridor('stormvine');self.assertEqual('stormvine',choose(p,s,s['objects']).action['id'])

    def test_rejected_seed_proposals_do_not_consume_attempts_or_cooldowns(self):
        s,p=corridor();tx=Transaction(p,p.planner);choose(p,s,s['objects']);tx.rollback()
        self.assertIsNone(p.seed_pending);self.assertFalse(any(p.seed_attempts.values()));self.assertFalse(p.seed_ready_at)

    def test_sungrass_does_not_assume_nearby_sleepers_stay_asleep(self):
        s,p=corridor('sungrass',gap=1);s['objects'][0]['sleeping']=True
        self.assertIsNone(choose(p,s,s['objects']))

    def test_safe_doorway_lure_can_prepare_armor_instead_of_only_waiting(self):
        s,p=corridor('earthroot');p.tiles[32]['terrain']=6
        p.doorway_hold={'depth':s['depth'],'door':32,'hide':31,'inputs':0,'quiet':0,'waits':0}
        a=hold_doorway(p,s,s['objects'],distance,neighbors,line_clear)
        self.assertEqual('PLANT',a.action['action']);self.assertEqual('earthroot',a.action['id'])

    def test_seed_priority_does_not_interrupt_committed_escape_or_ambush_routes(self):
        for owner in ('ambush_plan','multi_door_plan','ranged_plan'):
            s,p=corridor('earthroot');setattr(p,owner,{'goal':40})
            self.assertIsNone(seed_preparation(Context(p,s,enemies=s['objects'],active=s['objects'])),owner)
            self.assertIsNone(p.seed_pending)

    def test_nature_feeding_preserves_sungrass_needed_for_current_recovery(self):
        s,p=arena();s['hero']['hp']=15
        s['inventory'].append({'id':'sungrass','name':'seed of sungrass','actions':['PLANT']})
        s['inventory'].append({'id':'sandals','name':'sandals of nature','equipped':True,'actions':['FEED'],
                               'curse_known':True,'known_cursed':False})
        self.assertIsNone(use_artifact(p,s,[]))
        self.assertEqual('sungrass',choose(p,s,[]).action['id'])

    def test_sungrass_wait_does_not_preempt_cleansing_new_poison(self):
        s,p=arena();s['hero'].update(hp=15,buffs=[{'name':'herbal healing'},{'name':'poisoned'}])
        s['inventory'].append({'id':'mageroyal','name':'seed of mageroyal','actions':['PLANT']})
        p.seed_plan={'kind':'sungrass','cell':40,'stage':'recover','waits':0}
        self.assertEqual('mageroyal',choose(p,s,[]).action['id'])

    def test_sungrass_stops_waiting_without_observed_health_progress(self):
        s,p=arena();s['hero'].update(hp=15,buffs=[{'name':'herbal healing'}]);s['evaluation_stats']={'elapsed_turns':10}
        p.seed_plan={'kind':'sungrass','cell':40,'stage':'recover','waits':0,'heal_hp':15,'heal_progress_at':0}
        self.assertIsNone(choose(p,s,[]));self.assertIsNone(p.seed_plan)

    def test_known_emergency_healing_preempts_quiet_seed_setup(self):
        s,p=arena();s['hero']['hp']=4
        s['inventory'] += [{'id':'sungrass','name':'seed of sungrass','actions':['PLANT']},
                           {'id':'heal','name':'potion of healing','actions':['DRINK']}]
        self.assertIsNone(choose(p,s,[]))
        self.assertEqual('emergency-healing',p.choose(s).controller)


if __name__=='__main__':unittest.main()
