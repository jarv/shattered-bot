"""Public room signatures and synthetic remote-activation sequences."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.summoning_tactics import choose, ready, suspected_rooms
from tools.trap_field_tactics import observe_accepted
from tools.policy_decision import Finished


def chamber():
    s=state()
    s["map"]=dict(width=11,height=8,cells=[
        dict(cell=c,terrain=1 if (2<=c%11<=4 and 2<=c//11<=4)
             or (6<=c%11<=9 and c//11==3) else 6 if c==38 else 4,
             observed=True,visible=True,effects=[]) for c in range(88)])
    s["hero"].update(cell=38,hp=30,max_hp=30,strength=14,buffs=[])
    s["objects"]=[dict(cell=36,name="Skeletal remains")]
    s["inventory"]=[
        dict(id="armor",name="mail armor",identified=True,equipped=True,
             description="This armor blocks 0-6 damage and requires 14 strength.",actions=[]),
        dict(id="weapon",name="sword",identified=True,equipped=True,
             description="This melee weapon deals 4-12 damage and requires 14 strength.",actions=[]),
        dict(id="water",name="waterskin",actions=["THROW"])]
    return s,verified()


class SummoningTests(unittest.TestCase):
    def test_bones_signature_searches_from_door_and_counts_only_accepted_search(self):
        s,p=chamber()
        d=p.choose(s)
        self.assertEqual({"type":"search"},d.action)
        self.assertEqual(0,p.trap_scan_cells[38])
        observe_accepted(p,s,d,copy.deepcopy(s))
        self.assertEqual(1,p.trap_scan_cells[38])
        self.assertNotIn(37,p.paths(s))

    def test_bones_alone_do_not_classify_other_rooms(self):
        for change in ("corner","water","extra_loot","large"):
            s,p=chamber()
            if change=="corner":s["objects"][0]["cell"]=24
            if change=="water":s["map"]["cells"][24]["terrain"]=29
            if change=="extra_loot":s["objects"].append(dict(cell=25,name="chest"))
            if change=="large":s["map"]["cells"][23]["terrain"]=1
            p.update(s)
            self.assertEqual([],suspected_rooms(p.tiles,p.loot,11,8),change)

    def test_reveal_stage_remote_trigger_and_hold_room_until_observed_clear(self):
        s,p=chamber()
        s["map"]["cells"][36].update(terrain=18,trap="summoning trap")
        # Bones are elsewhere: don't throw at/destroy the reward heap.
        s["objects"][0]["cell"]=25
        p.update(s)
        d=choose(p,s,[])
        self.assertEqual({"type":"cell","cell":39},d.action)
        s["hero"]["cell"]=39
        p.update(s)
        d=choose(p,s,[])
        self.assertEqual({"type":"item","id":"water","action":"THROW"},d.action)
        self.assertEqual(36,p.trap_payload_return["cell"])
        self.assertEqual(39,p.summoning_pending["stand"])
        # Activation without known clearance never allows early retrieval.
        s["map"]["cells"][36]["terrain"]=19
        p.update(s)
        self.assertNotIn(36,p.paths(s))
        self.assertIsNotNone(p.summoning_pending)
        for c in p.summoning_pending["area"]:
            s["map"]["cells"][c].update(terrain=19,trap="summoning trap")
        p.update(s)
        self.assertIsNone(p.summoning_pending)

    def test_unknown_weak_gear_and_unsafe_geometry_do_not_trigger(self):
        for change in ("unknown","weak","strength","hp","second_door","unknown_wall","blocked_escape"):
            s,p=chamber()
            s["map"]["cells"][36].update(terrain=18,trap="summoning trap")
            s["objects"][0]["cell"]=25
            s["hero"]["cell"]=39
            if change=="unknown":s["inventory"][0]["identified"]=False
            if change=="weak":s["inventory"][0]["description"]="This armor blocks 0-2 damage and requires 10 strength."
            if change=="strength":s["hero"]["strength"]=10
            if change=="hp":s["hero"]["hp"]=15
            if change=="second_door":s["map"]["cells"][23]["terrain"]=6
            if change=="unknown_wall":s["map"]["cells"]=[t for t in s["map"]["cells"] if t["cell"]!=23]
            if change=="blocked_escape":s["map"]["cells"][40]["terrain"]=4
            p.update(s)
            self.assertIsNone(choose(p,s,[]),change)
            self.assertIsNone(p.trap_payload_return)

    def test_original_run81_signature_prevents_first_entry(self):
        s,p=chamber()
        s["hero"].update(cell=558,strength=11)
        s["inventory"][1].update(name="staff of magic missile +1",actions=["ZAP","IMBUE"],
            status="3/5",description="This melee weapon deals 2-8 damage and requires 9 strength.")
        groups={1:[506,507,508,555,556,557,604,605,606,653,654,655,560,609],
                4:[456,457,458,459,505,509,554,603,607,652,656,702,703,510,608],
                6:[558],29:[559]}
        s["map"]=dict(width=49,height=30,cells=[
            dict(cell=c,terrain=t,visible=True,observed=True,effects=[])
            for t,cells in groups.items() for c in cells])
        s["objects"]=[dict(cell=605,name="Skeletal remains")]
        d=p.choose(s)
        self.assertEqual({"type":"search"},d.action)
        for _ in range(2):
            observe_accepted(p,s,d,copy.deepcopy(s))
            if p.trap_scan_cells[558]<2:d=p.choose(s)
        self.assertEqual(2,p.trap_scan_cells[558])
        p.update(s)
        self.assertNotIn(557,p.paths(s))
        self.assertFalse(ready(p,s))


if __name__=="__main__":
    unittest.main()
