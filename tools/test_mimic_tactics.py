import unittest

from tools.test_challenge_systems import ready
from tools.policy_geometry import distance, neighbors, line_clear
from tools.mimic_tactics import suspicious_container, fight_mimic
from tools.room_tactics import prepare_containers
from tools.policy_decision import Finished


class MimicTacticsTests(unittest.TestCase):
    def test_only_public_warning_blocks_ordinary_chest_opening_even_with_key(self):
        s,p=ready()
        chest={"name":"crystal chest","description":"Contains a wand. It _feels off_; opening is a bad idea."}
        p.loot[25]=chest
        p.keys["crystal"]=1
        p.allowed_chests.add(25)
        self.assertFalse(p.walkable(25))
        prepare_containers(p,s)
        self.assertNotIn(25,p.allowed_chests)
        self.assertTrue(suspicious_container(chest))
        self.assertFalse(suspicious_container({"name":"chest","description":"An ordinary chest."}))

    def test_revealed_mimic_at_range_gets_magic_not_approach(self):
        s,p=ready()
        action=fight_mimic(p,s,[{"name":"mimic","cell":26}],distance,neighbors,line_clear)
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual(26,p.target)

    def test_adjacent_mimic_kite_is_unexposed_and_bounded(self):
        s,p=ready()
        enemy={"name":"mimic","cell":25}
        action=fight_mimic(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual("retreat",action.intent)
        self.assertGreaterEqual(distance(action.action["cell"],25,7),2)
        p.mimic_kites=6
        action=fight_mimic(p,s,[enemy],distance,neighbors,line_clear)
        self.assertEqual("ZAP",action.action.get("action"))

    def test_wounded_mage_does_not_force_empty_staff_trade(self):
        s,p=ready()
        s["hero"]["hp"]=10
        s["inventory"][0]["status"]="0/4"
        p.mimic_kites=6
        with self.assertRaises(Finished):
            fight_mimic(p,s,[{"name":"mimic","cell":25}],distance,neighbors,line_clear)
