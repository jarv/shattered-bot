import unittest

from tools.test_challenge_systems import ready


class SnakeNextDoorTests(unittest.TestCase):
    def test_exhausted_snake_fight_can_take_exposed_but_not_worsened_route_to_next_door(self):
        s,p=ready()
        s["hero"]["hp"]=13
        s["inventory"][0]["status"]="0/4"
        p.tiles[22]["terrain"]=6
        p.paths=lambda *a,**k:{24:None,23:24,22:23}
        p.door_ambush=lambda *a,**k:None
        p.retreat=lambda *a,**k:None
        enemy={"name":"sewer snake","cell":30}
        action=p.snake_combat(s,[enemy],"")
        self.assertEqual(23,action.action.get("cell"))
        self.assertEqual("retreat",action.intent)
        self.assertEqual(22,p.snake_route["door"])
        s["inventory"][0]["status"]="1/4"
        self.assertEqual("ZAP",p.snake_combat(s,[enemy],"").action.get("action"))

    def test_next_door_movement_stops_at_damage_and_input_budget(self):
        s,p=ready()
        s["hero"]["hp"]=13
        p.snake_route={"door":22,"hp":18}
        enemy={"name":"sewer snake","cell":30}
        self.assertIsNone(p.snake_reposition(s,[enemy]))
        p.snake_route=None
        p.snake_route_inputs=12
        self.assertIsNone(p.snake_reposition(s,[enemy]))
