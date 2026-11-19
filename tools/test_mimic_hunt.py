import unittest
from unittest.mock import patch

from tools.test_challenge_systems import ready, item
from tools.policy_geometry import distance
from tools.policy_decision import Decision, Intent, Finished
from tools.mimic_hunt import begin_hunt, observe_hunts, hunt_missing_mimic
from tools.room_completion import obligations
from tools.room_loot import before_room_exit
from tools.loot_completion import pending_collections,required_loot
from tools.survival_policy import SurvivalPolicy


class MimicHuntTests(unittest.TestCase):
    def test_room_pickup_plan_survives_distant_goal_reselection_before_exit(self):
        s,p=ready()
        p.tiles={c:{"cell":c,"terrain":6 if c==25 else 1,"visible":True} for c in (22,23,24,25,26)}
        p.loot[22]={"name":"seed of stormvine","top_item":item("seed of stormvine","THROW")}
        first=Decision({"type":"cell","cell":25},"distant chest",Intent.LOOT)
        self.assertEqual(23,before_room_exit(p,s,first).action["cell"])
        s["hero"]["cell"]=23
        second=Decision({"type":"cell","cell":24},"distant chest again",Intent.LOOT)
        self.assertEqual(22,before_room_exit(p,s,second).action["cell"])
        p.loot.pop(22)
        self.assertIsNone(before_room_exit(p,s,second))
        self.assertIsNone(p.room_loot_plan)

    def test_public_escape_is_permitted_and_recorded_as_reward_lost_not_pickup(self):
        s,p=ready()
        begin_hunt(p,s,26,{"description":"a wand"})
        s["ui"]={"texts":["The crystal mimic has escaped!"]}
        observe_hunts(p,s,distance)
        self.assertIsNone(hunt_missing_mimic(p,s,[],distance))
        self.assertFalse(p.mimic_obligations)
        self.assertIn((s["depth"],"mimic-escaped-reward-lost",26),p.room_attempts)
        self.assertFalse(pending_collections(p))
        self.assertEqual('missed-unrecoverable',p.missed_loot[0]['status'])
        self.assertFalse(p.missed_loot[0]['collected'])
        self.assertFalse(p.descent_counts_as_clear())
        self.assertTrue(any(o['kind']=='unrecoverable escaped mimic reward' for o in obligations(p,s)))

    def test_confirmed_escape_does_not_block_descent_or_certify_clearance(self):
        s,p=ready();begin_hunt(p,s,26,{'description':'a wand'})
        s['ui']={'texts':['The crystal mimic has escaped!']}
        observe_hunts(p,s,distance)
        with patch.object(SurvivalPolicy,'choose',return_value=Decision({'type':'cell','cell':25},'descend',Intent.DESCEND)):
            action=p.choose(s)
        self.assertEqual(Intent.DESCEND,action.intent)
        self.assertFalse(p.descent_counts_as_clear())
        self.assertTrue(p.deferred_obligations)

    def test_stale_escape_message_and_mere_disappearance_are_not_losses(self):
        for stale in (True,False):
            s,p=ready()
            if stale:s['ui']={'texts':['The crystal mimic has escaped!']}
            begin_hunt(p,s,26,{'description':'a wand'})
            observe_hunts(p,s,distance)
            self.assertFalse(p.missed_loot)
            self.assertTrue(pending_collections(p))

    def test_visible_pile_at_escape_origin_remains_collectible(self):
        s,p=ready();begin_hunt(p,s,26,{'description':'a wand'})
        p.loot[26]={'cell':26,'name':'gold','top_item':item('gold','THROW')}
        s['ui']={'texts':['The crystal mimic has escaped!']}
        observe_hunts(p,s,distance)
        self.assertIn(26,required_loot(p))

    def test_loss_ledger_survives_floor_reset_without_duplicate_escape(self):
        s,p=ready();begin_hunt(p,s,26,{'description':'a wand'})
        s['ui']={'texts':['The crystal mimic has escaped!']}
        observe_hunts(p,s,distance);observe_hunts(p,s,distance)
        self.assertEqual(1,len(p.missed_loot))
        p.memory.reset_floor(0)
        self.assertEqual(1,len(p.missed_loot))

    def test_crystal_mimic_displacement_invalidates_doorway_and_snake_plans(self):
        import copy
        s,p=ready()
        s["objects"]=[{"name":"crystal mimic","cell":26}]
        p.update(copy.deepcopy(s))
        p.ambush_plan={"kind":"doorway","door":25,"hide":24,"waits":0}
        p.doorway_hold={"depth":1,"door":25,"hide":24,"inputs":0,"quiet":0,"waits":0}
        p.snake_door_reset={"depth":1,"door":25,"hp":20,"steps":0,"waits":0}
        s["hero"]["cell"]=17
        p.update(s)
        self.assertIsNone(p.ambush_plan)
        self.assertIsNone(p.doorway_hold)
        self.assertIsNone(p.snake_door_reset)
        self.assertIsNone(p.door_ambush(s,s["objects"],s["objects"],kind="doorway"))

    def test_disappearance_does_not_resolve_reward_but_public_pickup_does(self):
        s,p=ready()
        begin_hunt(p,s,26,{"description":"You can see a wand inside."})
        observe_hunts(p,s,distance)
        self.assertTrue(any(o["kind"]=="unresolved suspicious mimic/reward" for o in obligations(p,s)))
        reward=item("wand of frost","ZAP")
        s["objects"]=[{"cell":25,"name":"wand of frost","top_item":reward}]
        observe_hunts(p,s,distance)
        s["objects"]=[]
        s["hero"]["cell"]=25
        s["inventory"].append(reward)
        s["ui"]={"texts":["You picked up: wand of frost."]}
        observe_hunts(p,s,distance)
        self.assertFalse(p.mimic_obligations)

    def test_search_is_bounded_and_crystal_interception_does_not_wait_for_pursuit(self):
        s,p=ready()
        begin_hunt(p,s,26,{"description":"a wand"})
        p.mimic_obligations[26]["steps"]=16
        with self.assertRaises(Finished):hunt_missing_mimic(p,s,[],distance)
        p.door_ambush=lambda *a,**k:(_ for _ in ()).throw(AssertionError("must not lure fleeing crystal mimic"))
        action=p.combat_override(s,[{"name":"crystal mimic","cell":26}])
        self.assertEqual("ZAP",action.action.get("action"))

    def test_room_ground_pickup_precedes_exit_but_recent_threat_interrupts(self):
        s,p=ready()
        p.tiles={c:{"cell":c,"terrain":6 if c==25 else 1,"visible":True} for c in (22,23,24,25,26)}
        p.loot[23]={"name":"seed of stormvine","top_item":item("seed of stormvine","THROW")}
        decision=Decision({"type":"cell","cell":25},"leave room",Intent.EXPLORE)
        self.assertEqual(23,before_room_exit(p,s,decision).action["cell"])
        p.recent_threats[22]={"name":"marsupial rat","cell":22}
        self.assertIsNone(before_room_exit(p,s,decision))
