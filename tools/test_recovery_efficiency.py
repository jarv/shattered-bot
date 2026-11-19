import unittest
from tools.test_survival_bot import state
from tools.test_nine_challenge import verified_policy
from tools.puzzle_supplies import frost_recovery_nearby,prepare_supplies
from tools.policy_geometry import distance,neighbors


class RecoveryEfficiencyTests(unittest.TestCase):
    def encounter(self):
        s=state();s['hero'].update(cell=17,hp=12,max_hp=20,buffs=[])
        s['map']={'width':15,'height':15,'cells':[{'cell':c,'terrain':4 if c%15 in {0,14} or c//15 in {0,14} else 1,'visible':True,'effects':[]} for c in range(225)]}
        s['objects']=[]
        s['inventory'] += [{'name':'ration of food','actions':['EAT'],'quantity':1,'id':'food'},
                           {'name':'crimson potion','actions':['DRINK'],'quantity':1,'id':'potion'}]
        p=verified_policy();p.update(s)
        p.tiles[192]['effects']=['A wall of dense bright green fire, caused by magic; extinguish it.']
        return s,p

    def test_distant_fire_does_not_raise_ordinary_healing_target(self):
        s,p=self.encounter()
        self.assertFalse(frost_recovery_nearby(p,s,distance))
        self.assertEqual(0.8,p.recovery_target(s))

    def test_already_funded_fire_budget_is_not_spent_across_floor(self):
        s,p=self.encounter();p.food_recovery_source='fire';p.food_recovery_until=114;p.floor_recovery=24
        self.assertEqual(0,p.recovery_limit(s,False))

    def test_surplus_meal_budget_remains_valid_far_from_fire(self):
        s,p=self.encounter();p.food_recovery_source='surplus';p.food_recovery_until=74;p.floor_recovery=24
        self.assertEqual(74,p.recovery_limit(s,False))

    def test_nearby_puzzle_still_requires_near_full_health(self):
        s,p=self.encounter();s['hero']['cell']=190
        self.assertTrue(frost_recovery_nearby(p,s,distance))
        self.assertEqual(0.95,p.recovery_target(s))
        action=prepare_supplies(p,s,[],distance,neighbors)
        self.assertFalse(action and action.action.get('action')=='DRINK')

    def test_deferred_controller_does_not_fund_speculative_healing(self):
        s,p=self.encounter();s['hero']['cell']=190;p.deferred_room_controllers.add('potion-supplies')
        self.assertFalse(frost_recovery_nearby(p,s,distance))
        self.assertEqual(0.8,p.recovery_target(s))


if __name__=='__main__':unittest.main()
