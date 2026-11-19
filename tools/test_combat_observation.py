import copy
import unittest

from tools.test_challenge_systems import ready, item
from tools.combat_observation import context, source, observe_accepted_attack


class ObservedDamageTests(unittest.TestCase):
    def test_public_fizzle_is_not_recorded_as_a_zero_damage_wand_sample(self):
        s,p=ready()
        s["objects"]=[{"name":"gnoll scout","cell":25,"health_bar":[80,100]}]
        wand=dict(item("wand of magic missile","ZAP"),curse_known=True)
        s["inventory"].append(wand)
        targeting=copy.deepcopy(s)
        targeting["status"]="targeting"
        observe_accepted_attack(p,s,p.use(wand,"ZAP","cast",target=25),targeting)
        after=copy.deepcopy(s)
        after["ui"]={"texts":["Your wand fizzles; it must not have enough charge."]}
        self.assertIsNone(observe_accepted_attack(p,targeting,p.cell(25,"target"),after))
        self.assertFalse(p.damage_samples)

    def test_confirmed_kill_is_a_censored_lower_bound_not_a_small_exact_hit(self):
        s,p=ready()
        s["objects"]=[{"name":"gnoll scout","cell":25,"health_bar":[20,100]}]
        after=copy.deepcopy(s)
        after["objects"]=[]
        after["ui"]={"texts":["You defeated gnoll scout."]}
        feedback=observe_accepted_attack(p,s,p.cell(25,"melee"),after)
        self.assertTrue(feedback["censored"])
        self.assertAlmostEqual(0.2,feedback["bar_loss_lower_bound"])
        sample=next(iter(p.damage_samples.values()))
        self.assertEqual(0,sample["count"])
        self.assertEqual(1,sample["censored_count"])

    def test_wand_sample_waits_for_target_execution_and_uses_only_public_bar_delta(self):
        s,p=ready()
        enemy={"name":"gnoll scout","cell":25,"health_bar":[80,100]}
        s["objects"]=[enemy]
        wand=dict(item("wand of magic missile","ZAP"),curse_known=True,identified=False)
        s["inventory"].append(wand)
        targeting=copy.deepcopy(s)
        targeting["status"]="targeting"
        action=p.use(wand,"ZAP","cast",target=25)
        observe_accepted_attack(p,s,action,targeting)
        self.assertFalse(p.damage_samples)
        after=copy.deepcopy(s)
        after["objects"][0]["health_bar"]=[50,100]
        observe_accepted_attack(p,targeting,p.cell(25,"target"),after)
        sample=next(iter(p.damage_samples.values()))
        self.assertEqual(1,sample["count"])
        self.assertAlmostEqual(0.3,sample["bar_loss"])

    def test_unidentified_item_outperforming_equipped_wand_can_win_observed_comparison(self):
        s,p=ready()
        enemy={"name":"gnoll scout","cell":25,"health_bar":[80,100]}
        s["objects"]=[enemy]
        wand=dict(item("wand of magic missile","ZAP"),id="spare",curse_known=True,identified=False)
        s["inventory"].append(wand)
        staff=s["inventory"][0]
        for item_,action,loss in ((wand,"ZAP",0.6),(staff,"ZAP",0.2),(None,None,0.1)):
            p.damage_samples[(context(s,enemy),source(s,item_,action))]={"count":2,"bar_loss":loss}
        chosen=p.best_attack(s,enemy)
        self.assertEqual("spare",chosen.action["id"])
        self.assertIn("observed_damage_comparison",p.planner.report)
        self.assertFalse(wand["identified"])

    def test_missing_before_bar_or_fire_never_manufactures_a_damage_sample(self):
        for mode in ("missing","fire"):
            s,p=ready()
            s["objects"]=[{"name":"gnoll scout","cell":25,"health_bar":[80,100]}]
            if mode=="missing":s["objects"][0].pop("health_bar")
            if mode=="fire":next(t for t in s["map"]["cells"] if t["cell"]==25)["effects"]=["A fire is raging here."]
            after=copy.deepcopy(s)
            after["objects"][0]["health_bar"]=[50,100]
            observe_accepted_attack(p,s,p.cell(25,"melee"),after)
            self.assertFalse(p.damage_samples)
