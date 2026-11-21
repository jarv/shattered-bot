"""Reduced public geometry from run 000052, decision 465 (line 1349).

Independent selector fixtures, not recovered runtime memory or game replay.
Only the observed approach, sight blockers, threats and usable staff are kept.
"""
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.unit_strategies import choose


def approach(hp=12):
    s = state()
    s.update(depth=2, branch=0)
    s["hero"].update(cell=92, hp=hp, max_hp=25)
    terrain = {91:4, 92:20, 93:1, 94:20, 95:1, 96:1,
               126:4, 127:4, 128:6, 129:4, 130:4, 131:4,
               132:5, 133:4, 162:4, 163:1, 164:1, 165:1, 168:2}
    s["map"] = {"width":36, "height":28, "cells":[
        {"cell":c, "terrain":t, "visible":c not in {126,162,168},
         "observed":True, "effects":[]}
        for c,t in terrain.items()]}
    s["inventory"][0].update(status="1/4", identified=True,
                             curse_known=True, known_cursed=False)
    s["objects"] = [{"name":"sewer snake", "cell":128},
                    {"name":"gnoll scout", "cell":163, "health_bar":[3,16]}]
    p = verified()
    p.update(s)
    return s,p


class SnakeLureStartHealthTests(unittest.TestCase):
    def test_wounded_snake_dispatch_uses_available_magic_not_new_lure(self):
        s,p = approach()
        d = choose(p,s,s["objects"])
        self.assertEqual({"type":"item", "id":"item-0", "action":"ZAP"},d.action)
        self.assertEqual(128,p.target)
        self.assertIsNone(p.ambush_plan)
        self.assertFalse(p.ambush_attempts)
        self.assertEqual("1/4",s["inventory"][0]["status"])

    def test_new_lure_uses_same_health_floor_as_continuation(self):
        for hp,allowed in ((12,False),(13,True)):
            with self.subTest(hp=hp):
                s,p = approach(hp)
                d = p.door_ambush(s,s["objects"],[s["objects"][0]],kind="snake")
                self.assertEqual(allowed,d is not None)
                if allowed:
                    self.assertEqual({"type":"cell","cell":93},d.action)
                    self.assertEqual(132,p.ambush_plan["door"])
                else:
                    self.assertIsNone(p.ambush_plan)
                    self.assertFalse(p.ambush_attempts)

    def test_existing_wounded_plan_still_aborts_and_records_attempt(self):
        s,p = approach()
        p.ambush_plan = {"kind":"snake","door":132,"hide":95,
                         "waits":0,"start_hp":13}
        self.assertIsNone(p.door_ambush(s,s["objects"],[s["objects"][0]],kind="snake"))
        self.assertIsNone(p.ambush_plan)
        self.assertEqual(1,p.ambush_attempts[132])

    def test_healthy_lure_still_requires_observed_walkable_route(self):
        s,p = approach(13)
        p.tiles[93]["trap"] = "burning trap"
        self.assertIsNone(p.door_ambush(s,s["objects"],[s["objects"][0]],kind="snake"))
        self.assertIsNone(p.ambush_plan)


if __name__ == "__main__":
    unittest.main()
