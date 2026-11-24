"""Run 113 health gap and run 115 known-invisibility arrival contract."""
import copy
import unittest

from tools.test_challenge_rules import verified
from tools.test_survival_bot import state
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies, safe_test_bank, known_pool_bank
from tools.exploration_budget import useful_loot, selective_descent


def pool():
    s=state()
    s["depth"]=2
    s["hero"].update(cell=1267,hp=30,max_hp=30,strength=11,buffs=[])
    groups={
        4:[1222,1223,1225,1226,1227,1228,1229,1230,1231,1259,1296,1333,
           1370,1407,1303,1304,1305,1306,1307,1308,1309,1346,1383,1420,1457],
        12:[1224],1:[1267,1268,1269,1270,1233],20:[1232,1271],
        29:[1260,1261,1262,1263,1264,1297,1298,1299,1300,1301,1334,1335,
            1336,1337,1338,1372,1373,1374,1375,1408,1409,1410,1411,1445,1446,1447],
        14:[1265,1302,1339],5:[1266,1272],11:[1371]}
    s["map"]=dict(width=37,height=46,cells=[
        dict(cell=c,terrain=t,visible=True,observed=True,effects=[])
        for t,cells in groups.items() for c in cells])
    s["inventory"]=[
        dict(id="invis",name="potion of invisibility",identified=True,actions=["DRINK"]),
        dict(id="armor",name="cloth armor",identified=True,equipped=True,actions=[],
             description="This armor blocks 0-2 damage and requires 10 strength.")]
    s["objects"]=[dict(cell=c,name="giant piranha",sleeping=True) for c in [1334,1338,1410]]
    s["objects"].append(dict(cell=1371,name="Chest"))
    p=verified();p.update(s)
    s["objects"]=[]
    for tile in s["map"]["cells"]:
        if tile["cell"]%37<8:tile["visible"]=False
    p.update(s)
    return s,p


class ProgressionPrerequisites(unittest.TestCase):
    def test_known_invisibility_opens_door_then_activates_without_unknown_drink_rules(self):
        s,p=pool()
        self.assertFalse(safe_test_bank(p,s,1267,distance,neighbors,allow_dry=True,pool_bank=True))
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(d)
        self.assertEqual({"type":"cell","cell":1266},d.action)
        self.assertIsNone(p.room_journey)
        s["hero"]["cell"]=1266
        next(t for t in s["map"]["cells"] if t["cell"]==1266)["terrain"]=6
        p.update(s)
        d=prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual("DRINK",d.action.get("action"))
        plan=copy.deepcopy(p.room_journey)
        self.assertEqual(1371,plan.route[-1])
        self.assertIsNone(p.room_journey.advance(p,s,[],neighbors))  # No actual buff.
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.completed_room_rewards)
        p.room_journey=plan
        # Synthetic accepted movement/pickup observations, not a gameplay replay.
        for turn in range(18):
            s["hero"]["buffs"]=[dict(name="invisible",description=f"Turns remaining: {20-turn}.")]
            d=plan.advance(p,s,[],neighbors)
            if d is None:break
            target=d.action["cell"]
            if target==s["hero"]["cell"]==1371:
                from tools.loot_completion import observe_collected
                before=copy.deepcopy(s)
                before["objects"]=[dict(cell=1371,name="gold",top_item=dict(name="gold",quantity=10))]
                s["hero"]["gold"]=s["hero"].get("gold",0)+10
                observe_collected(p,before,d,s)
                p.loot.pop(1371,None)
            s["hero"]["cell"]=target
        self.assertEqual(1266,s["hero"]["cell"])
        self.assertIsNone(p.room_journey)
        self.assertIn((2,"pool",1371),p.completed_room_rewards)

    def test_known_bank_keeps_habitat_effect_and_retreat_checks(self):
        for bad in ("habitat","effect","unseen","no_escape"):
            s,p=pool()
            if bad=="habitat":p.room_blocked.add(1267)
            elif bad=="effect":p.tiles[1267]["effects"]=["toxic gas"]
            elif bad=="unseen":p.tiles[1267]["visible"]=False
            else:p.tiles[1268]["terrain"]=4
            self.assertFalse(known_pool_bank(p,s,1267,neighbors,arrival=True),bad)

    def test_health_prerequisite_uses_existing_recovery_without_lowering_drink_threshold(self):
        s=state();p=verified()
        s["hero"].update(hp=19,max_hp=25,buffs=[])
        s["inventory"].append(dict(id="unknown",name="golden potion",identified=False,actions=["DRINK","DROP"]))
        s["inventory"].append(dict(id="food",name="ration of food",actions=["EAT"]))
        p.update(s)
        self.assertGreaterEqual(p.recovery_target(s),.85)
        for hp in (19,20,21):
            s["hero"]["hp"]=hp
            action=p.choose(s)
            self.assertEqual({"type":"wait"},action.action)
            self.assertEqual("recover: natural healing",action.reason)
        s["hero"]["hp"]=22
        self.assertGreaterEqual(22/25,p.recovery_target(s))
        p.strength_identified=True
        self.assertEqual(.75,p.recovery_target(s))
        p.natural_healing_waits=1000
        self.assertEqual(0,p.recovery_limit(s,False))

    def test_future_equipment_is_useful_but_curses_and_sales_are_not_free_pickups(self):
        equipment=dict(name="plate armor",description="This armor blocks 0-10 damage and requires 18 strength.")
        self.assertTrue(useful_loot(dict(top_item=equipment)))
        self.assertTrue(useful_loot(dict(top_item=dict(name="ring of might"))))
        self.assertFalse(useful_loot(dict(for_sale=True,top_item=equipment)))
        self.assertFalse(useful_loot(dict(top_item=dict(equipment,known_cursed=True))))

    def test_experience_target_is_advisory_not_a_descent_gate(self):
        s=state();p=verified();p.update(s)
        s["hero"]["level"]=1
        selective_descent(p,s,[])
        self.assertTrue(p.planner.report["progression"]["below_early_target"])
        self.assertEqual(2,p.planner.report["progression"]["early_level_target"])
