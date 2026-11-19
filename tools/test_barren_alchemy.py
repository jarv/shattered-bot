import unittest

from tools.alchemy_tactics import plan_brew, approach_alchemy
from tools.seed_tactics import choose_seed
from tools.test_challenge_systems import ready, item
from tools.policy_geometry import distance, neighbors


class BarrenAlchemyTests(unittest.TestCase):
    def test_rendered_colon_energy_allows_verified_meat_recipe(self):
        from tools.alchemy_tactics import alchemy_menu,Brew
        s,p=ready()
        s.update(scene='AlchemyScene',modal=False)
        s['ui']={'energy_text':'Energy: 5','buttons':[
            {'id':'back','label':'Back'},{'id':'craft','label':'Craft: stewed meat'}]}
        p.alchemy_plan={'brew':Brew(('mystery meat',),'stewed meat','urgent food',1),
                        'index':1,'stage':'slot','steps':0,'reserve':0}
        self.assertEqual('craft',alchemy_menu(p,s).action['id'])

    def test_completed_alchemy_uses_visible_scene_back_not_window_dismissal(self):
        from tools.alchemy_tactics import alchemy_menu,Brew
        s,p=ready()
        s.update(scene='AlchemyScene',modal=False)
        s['ui']={'buttons':[{'id':'scene-exit','label':'Back'}]}
        p.alchemy_plan={'brew':Brew(('mystery meat',),'stewed meat','food'),
                        'index':1,'stage':'done','steps':0}
        self.assertEqual({'type':'button','id':'scene-exit'},alchemy_menu(p,s).action)
        self.assertIsNone(p.alchemy_plan)

    def test_unplanned_scene_uses_visible_back_but_bag_window_can_be_dismissed(self):
        from tools.alchemy_tactics import alchemy_menu
        s,p=ready()
        s.update(scene='AlchemyScene',modal=False)
        s['ui']={'buttons':[{'id':'exit','label':'Back'}]}
        self.assertEqual('button',alchemy_menu(p,s).action['type'])
        s['modal']=True
        self.assertEqual('back',alchemy_menu(p,s).action['type'])

    def test_unavailable_scene_exit_is_explicit_stop_not_invalid_api_action(self):
        from tools.alchemy_tactics import alchemy_menu
        from tools.policy_decision import Finished
        s,p=ready()
        s.update(scene='AlchemyScene',modal=False)
        s['ui']={'buttons':[]}
        with self.assertRaisesRegex(Finished,'no observed exit button'):alchemy_menu(p,s)

    def test_urgent_meat_cooking_is_not_hidden_behind_optional_low_health_crafting_gate(self):
        s,p=ready()
        s["hero"].update(hp=8,buffs=[{"name":"starving"}])
        s["inventory"].append(item("mystery meat","THROW"))
        p.tiles[25].update(terrain=28,visible=True)
        action=p.challenge_preparation(s,[])
        self.assertEqual(25,action.action.get("cell"))
        self.assertEqual("stewed meat",p.alchemy_plan["brew"].output)

    def test_barren_seed_recipe_reaches_public_station_without_bag_pressure(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of icecap","THROW"),quantity=2),
                           item("seed of stormvine","THROW")]
        p.tiles[25].update(terrain=28,visible=True)
        action=approach_alchemy(p,s)
        self.assertEqual(25,action.action.get("cell"))
        self.assertEqual("random potion",p.alchemy_plan["brew"].output)
        self.assertEqual(3,len(p.alchemy_plan["brew"].ingredients))
        self.assertIsNone(approach_alchemy(p,s))  # Never replace an active recipe.

    def test_inventory_pressure_does_not_consume_reserved_frost_or_starflower(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of icecap","THROW"),quantity=2),
                           item("seed of starflower","THROW"),item("seed of stormvine","THROW")]
        s["inventory"] += [item(f"unrelated object {n}","DROP") for n in range(20)]
        self.assertIsNone(plan_brew(s,{"frost"},barren_land=True))
    def test_required_frost_recipe_precedes_other_matching_triples(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of blindweed","THROW"),quantity=3),
                           dict(item("seed of icecap","THROW"),quantity=3)]
        brew=plan_brew(s,{"frost"},barren_land=True)
        self.assertEqual(("seed of icecap",)*3,brew.ingredients)

    def test_mixed_brew_reserves_incomplete_required_recipe(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of icecap","THROW"),quantity=2),
                           item("seed of stormvine","THROW")]
        self.assertIsNone(plan_brew(s,{"frost"},barren_land=True))
    def test_mixed_seeds_brew_without_inventory_pressure_only_under_barren_land(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of icecap","THROW"),quantity=2),
                           item("seed of stormvine","THROW")]
        self.assertIsNone(plan_brew(s))
        brew=plan_brew(s,barren_land=True)
        self.assertEqual(("seed of icecap","seed of icecap","seed of stormvine"),brew.ingredients)
        self.assertEqual("random potion",brew.output)
        self.assertIsNone(choose_seed(p,s,[{"name":"mimic","cell":26}],distance,neighbors))

    def test_matching_recipe_precedes_mixed_and_preserves_starflower(self):
        s,p=ready()
        s["inventory"] += [dict(item("seed of icecap","THROW"),quantity=3),
                           item("seed of starflower","THROW"),item("seed of stormvine","THROW")]
        self.assertEqual(("seed of icecap",)*3,plan_brew(s,barren_land=True).ingredients)
        s["inventory"][-3]["quantity"]=1
        self.assertIsNone(plan_brew(s,barren_land=True))

    def test_urgent_satiety_precedes_seed_conversion(self):
        s,p=ready()
        s["hero"]["buffs"]=[{"name":"starving"}]
        s["inventory"] += [item("potion of purity","DRINK"),
                           dict(item("seed of icecap","THROW"),quantity=3)]
        self.assertEqual("potion of cleansing",plan_brew(s,barren_land=True).output)
