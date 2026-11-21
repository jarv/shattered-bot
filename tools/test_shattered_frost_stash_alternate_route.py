"""Run 66: a door shortcut must not hide the safe floor-only stash route."""
import copy
import unittest

from tools.test_survival_bot import state
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.potion_stash import stash_cells, advance_stash
from tools.puzzle_supplies import prepare_supplies, safe_test_bank


def fixture(pos=1145):
    s = state()
    # Reduced public terminal geometry. Unknown cells stay absent.
    groups = {
        4: [1107,1108,1109,1110,1112,1113,1114,1115,1142,1150,
            1177,1185,1212,1220],
        5: [1111],
        1: [1143,1145,1146,1147,1179,1180,1181,1182],
        20: [1144,1178],
        29: [1148,1149,1183,1184],
    }
    cells = [dict(cell=c, terrain=t, visible=True, observed=True)
             for t, cs in groups.items() for c in cs]
    cells += [dict(cell=c, terrain=14, visible=True, observed=True,
                   effects=["magical fire"]) for c in range(1213,1220)]
    cells.append(dict(cell=1252,terrain=14,visible=True,observed=True))
    s["map"] = dict(width=35,height=40,cells=cells)
    s["hero"].update(cell=pos,hp=25,max_hp=25,buffs=[])
    s["inventory"] = [dict(id=str(n),name=color+" potion",quantity=1,
                           identified=False,actions=["DROP","THROW","DRINK"])
                      for n,color in enumerate(("amber","indigo","azure"))]
    s["objects"] = [dict(cell=1252,name="scroll of upgrade",
                         top_item=dict(name="scroll of upgrade",identified=True))]
    p = verified()
    p.update(s)
    return s,p


class FrostStashAlternateRouteTests(unittest.TestCase):
    def test_door_shortcut_does_not_exclude_floor_only_alternative(self):
        s,p = fixture(1148)
        ordinary = p.route(p.paths(s),1144)
        self.assertIn(1111,ordinary)
        self.assertTrue(safe_test_bank(p,s,1144,distance,neighbors,allow_dry=True))
        self.assertIn(1144,stash_cells(p,s,distance,neighbors,safe_test_bank))

    def test_terminal_preparation_can_stage_without_consumption_or_credit(self):
        s,p = fixture()
        before = copy.deepcopy(s)
        d = prepare_supplies(p,s,[],distance,neighbors)
        self.assertIsNotNone(d,"The floor-only stash route must admit preparation")
        self.assertEqual("cell",d.action["type"])
        self.assertNotIn(d.action["cell"],p.fire_buffer)
        self.assertIsNone(p.potion_stash)
        self.assertIsNone(p.puzzle_probe)
        self.assertFalse(p.puzzle_drinks)
        self.assertIn(1252,p.loot)
        self.assertEqual(before,s)

    def test_actual_stash_travel_uses_admitted_alternative(self):
        s,p = fixture(1148)
        p.potion_stash = dict(depth=1,bank=1148,cell=1144,candidate="amber potion",
                              phase="drop",steps=0,dropped={},pending=None)
        d = advance_stash(p,s,[],distance)
        self.assertEqual(dict(type="cell",cell=1147),d.action)
        self.assertNotIn(1111,d.navigation_route)
        self.assertTrue(all(p.tiles[c]["terrain"] in {1,3,9,11,14,19,20,29}
                            for c in d.navigation_route))

    def test_no_hazardous_alternative_is_admitted(self):
        for kind in ("trap","plant","effects","blocked","loot"):
            s,p = fixture(1148)
            if kind == "blocked": p.blocked.add(1146)
            elif kind == "loot": p.loot[1146] = dict(name="ration of food")
            else: p.tiles[1146][kind] = ["fire"] if kind=="effects" else "poison"
            self.assertNotIn(1144,stash_cells(p,s,distance,neighbors,safe_test_bank),kind)


if __name__ == "__main__":
    unittest.main()
