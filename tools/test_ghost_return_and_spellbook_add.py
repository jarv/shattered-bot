import unittest
from unittest.mock import patch
from tools.test_regular_feedback import arena
from tools.test_complete_artifact_utilization import artifact
from tools.ghost_quest import observe_quest,visit_ghost
from tools.spellbook_feeding import choose,menu,observe,requests
from tools.policy_geometry import distance,neighbors
from tools.policy_decision import Intent,Finished
from tools.policy_runtime import Transaction


class GhostReturnTests(unittest.TestCase):
    def setup_ghost(self):
        s,p=arena();s['depth']=3;s['objects']=[{'name':'sad ghost','cell':42}]
        p.update(s)
        return s,p

    def test_first_encounter_area_is_retained_when_ghost_moves(self):
        s,p=self.setup_ghost();area=list(p.ghost_quest['origin_area'])
        s['objects'][0]['cell']=60;p.update(s)
        self.assertEqual(42,p.ghost_quest['origin_cell'])
        self.assertEqual(area,p.ghost_quest['origin_area'])
        self.assertEqual(60,p.ghost_quest['last_cell'])

    def test_absent_stale_cell_does_not_create_neighbor_orbit(self):
        s,p=self.setup_ghost();s['objects']=[]
        p.ghost_quest.update(stage='reward',last_cell=60,last_depth=3,origin_area=[42,43])
        p.update(s)
        a=visit_ghost(p,s,[],distance,neighbors);goal=p.ghost_quest['return_goal']
        self.assertIn(goal,{42,43,32,33,34,41,51,52,53,44,35,54})
        s['hero']['cell']=goal
        a=visit_ghost(p,s,[],distance,neighbors)
        self.assertIn(goal,p.ghost_quest['return_views'])
        self.assertNotEqual(goal,p.ghost_quest['return_goal'])
        self.assertFalse(p.ghost_quest.get('selected'))

    def test_reward_arrival_interacts_only_with_visible_ghost(self):
        s,p=self.setup_ghost();p.ghost_quest['stage']='reward';s['hero']['cell']=41
        a=visit_ghost(p,s,[],distance,neighbors)
        self.assertEqual({'type':'cell','cell':42},a.action)
        self.assertEqual('dialogue',p.ghost_menu['stage'])

    def test_budget_exhaustion_does_not_silently_abandon_reward(self):
        s,p=self.setup_ghost();p.ghost_quest.update(stage='reward',travel=100)
        with self.assertRaises(Finished):visit_ghost(p,s,[],distance,neighbors)
        self.assertEqual('reward',p.ghost_quest['stage'])

    def test_reward_preempts_optional_preparation_and_blocks_descent(self):
        s,p=self.setup_ghost();p.ghost_quest['stage']='reward';s['hero']['cell']=41
        self.assertEqual('ghost-reward',p.choose(s).controller)
        p.ghost_menu=None
        decision=p.cell(41,'test: descend',intent=Intent.DESCEND)
        with patch('tools.survival_policy.SurvivalPolicy.choose',return_value=decision), \
                patch('tools.mage_policy.before_room_exit',return_value=None):
            with self.assertRaises(Finished):p.choose(s)


class SpellbookAddTests(unittest.TestCase):
    def setup_book(self,name='scroll of rage',quantity=1):
        s,p=arena()
        book=artifact('unstable spellbook',['ADD','READ'])
        book['description']='The book is incomplete. Its index is currently pointing to the following blank pages:\n_scroll of rage_\n_scroll of identify_\n\nEmpowered effects.'
        scroll={'id':'scroll','name':name,'quantity':quantity,'identified':True,'actions':['READ','DROP']}
        s['inventory'] += [book,scroll]
        return s,p,book,scroll

    def test_only_identified_current_index_requests_can_be_added(self):
        for name,identified,eligible in (('scroll of rage',True,True),('scroll of rage',False,False),
                                         ('scroll of lullaby',True,False)):
            s,p,book,scroll=self.setup_book(name);scroll['identified']=identified
            a=choose(p,s,[],book)
            self.assertEqual(eligible,a is not None)
        self.assertEqual({'scroll of rage','scroll of identify'},requests(book))

    def test_unidentified_appearances_not_promoted_to_named_scrolls(self):
        s,p,book,scroll=self.setup_book('scroll of KAUNAN');scroll['identified']=False
        self.assertIsNone(choose(p,s,[],book))

    def test_essential_reserve_retained_but_requested_surplus_can_be_added(self):
        s,p,book,scroll=self.setup_book('scroll of identify')
        self.assertIsNone(choose(p,s,[],book))
        scroll['quantity']=2
        self.assertEqual('ADD',choose(p,s,[],book).action['action'])

    def test_selector_rechecks_index_then_verifies_consumption_and_book_change(self):
        s,p,book,scroll=self.setup_book();choose(p,s,[],book);plan=p.artifact_menu
        s['ui']={'texts':['Select a scroll'],'buttons':[{'id':'scroll-button','label':'scroll of rage'}]}
        self.assertEqual('scroll-button',menu(p,s,plan).action['id'])
        s['inventory'].remove(scroll);book['name']='unstable spellbook +1'
        observe(p,s)
        self.assertTrue(p.planner.report['spellbook_add']['confirmed'])
        self.assertIsNone(p.artifact_menu)

    def test_changed_request_cancels_instead_of_feeding_arbitrary_identified_scroll(self):
        s,p,book,scroll=self.setup_book();choose(p,s,[],book)
        book['description']=book['description'].replace('scroll of rage','scroll of lullaby')
        s['ui']={'texts':['Select a scroll'],'buttons':[{'id':'scroll-button','label':'scroll of rage'}]}
        self.assertEqual('back',menu(p,s,p.artifact_menu).action['type'])

    def test_unconfirmed_add_is_not_retried_or_credited(self):
        s,p,book,scroll=self.setup_book();choose(p,s,[],book)
        p.artifact_menu['stage']='verify';observe(p,s)
        self.assertFalse(p.planner.report['spellbook_add']['confirmed'])
        self.assertIsNone(choose(p,s,[],book))

    def test_rejected_proposal_rolls_back_feed_budget_and_menu(self):
        s,p,book,scroll=self.setup_book();tx=Transaction(p,p.planner);choose(p,s,[],book);tx.rollback()
        self.assertIsNone(p.artifact_menu);self.assertFalse(p.artifact_extension_attempts)


if __name__=='__main__':unittest.main()
