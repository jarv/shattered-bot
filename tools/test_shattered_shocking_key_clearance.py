"""Public geometry at run 000166 decision 1114; not runtime memory."""
import copy
import unittest

from tools.test_regular_feedback import arena
from tools.priority_resources import choose, targets
from tools.environment_tactics import recover_trap_payload


def fixture():
    s, _ = arena()
    s["hero"].update(cell=285, hp=35, max_hp=35)
    # Shocking plate, its radius, water conduction and observed dry boundaries.
    terrain = {71:4,72:4,113:9,114:29,115:29,116:4,156:9,157:29,
               158:9,159:4,199:9,200:1,201:18,202:4,242:1,243:1,
               244:33,245:4,283:20,284:18,285:1,286:1,287:33,288:4}
    s["map"] = {"width":43,"height":36,"cells":[
        {"cell":c,"terrain":t,"visible":True,"observed":True,
         **({"trap":"shocking trap"} if t == 18 else {})}
        for c,t in terrain.items()]}
    s["inventory"] = [{"id":"skin","name":"waterskin","actions":["THROW","DRINK"]}]
    key = {"cell":201,"name":"golden key","top_item":{"name":"golden key"}}
    s["objects"] = [key,{"cell":283,"name":"sad ghost"}]
    from tools.test_challenge_rules import verified
    p = verified()
    p.update(s)
    # Publicly remembered locked chest in the terminal diagnostic.
    p.loot[870] = {"cell":870,"name":"Locked chest"}
    return s,p


class ShockingKeyClearanceTests(unittest.TestCase):
    def test_required_key_gets_remote_clearance_not_another_potion_test(self):
        s,p = fixture()
        tiles = copy.deepcopy(p.tiles)
        self.assertIn(201, targets(p))
        action = choose(p,s,[])
        self.assertIsNotNone(action)
        self.assertEqual({"type":"item","id":"skin","action":"THROW"}, action.action)
        self.assertEqual(201,p.target)
        self.assertEqual(tiles,p.tiles)
        self.assertIn(201,targets(p))
        self.assertEqual(201,p.trap_payload_return["cell"])
        s["inventory"] = []
        self.assertIsNone(recover_trap_payload(p,s,[]))
        # Synthetic follow-up, not a continuation of the recorded run.
        p.tiles[201].update(terrain=19,trap=None,effects=["electricity"])
        self.assertIsNone(choose(p,s,[]))
        p.tiles[201]["effects"]=[]
        self.assertIsNotNone(choose(p,s,[]))
        self.assertIn(201,targets(p))  # Disarm is not a pickup receipt.

    def test_unsafe_or_uncertain_electrical_footprints_are_not_triggered(self):
        for case in ("near","water_hero","friend","unseen","storm","plant","effect","threat"):
            with self.subTest(case=case):
                s,p = fixture()
                if case == "near":s["hero"]["cell"]=243
                if case == "water_hero":s["hero"]["cell"]=114
                if case == "friend":s["objects"].append({"cell":115,"name":"sad ghost"})
                if case == "unseen":p.tiles[113]["visible"]=False
                if case == "storm":p.tiles[201]["trap"]="storm trap"
                if case == "plant":p.tiles[157]["plant"]="stormvine"
                if case == "effect":p.tiles[157]["effects"]=["electricity"]
                if case == "threat":p.recent_threats[300]={"name":"rat","cell":300}
                choose(p,s,[])
                self.assertNotIn((s["depth"],201),p.trap_attempts)
                self.assertEqual(18,p.tiles[201]["terrain"])


if __name__ == "__main__":
    unittest.main()
