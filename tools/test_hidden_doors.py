import unittest

from tools.survival_bot import SurvivalPolicy
from tools.hidden_doors import search_coverage, wall_scores, corridor_ends, seek_corridor_end
from tools.survival_bot import distance
from tools.test_challenge_systems import ready
from tools.test_survival_bot import state


class HiddenDoorTests(unittest.TestCase):
    def corridor(self):
        s,p=ready()
        s["hero"]["cell"]=24
        p.tiles={c:{"cell":c,"terrain":1 if c in {24,31,38} else 4,"visible":True}
                 for c in (16,17,18,23,24,25,30,31,32,38)}
        p.paths=lambda state,occupied=():{24:None,31:24,38:31}
        return s,p

    def test_two_tile_narrow_dead_end_is_stronger_than_generic_room_wall(self):
        s,p=self.corridor()
        self.assertEqual({17},corridor_ends(p.tiles,7,7))
        self.assertEqual(12,wall_scores(p.tiles,7,7)[17])
        p.tiles[10]={"terrain":4,"visible":True}
        self.assertFalse(corridor_ends(p.tiles,7,7))

    def test_dead_end_search_runs_on_floor_one_once_without_hidden_metadata(self):
        s,p=self.corridor()
        p.tiles[17]["generated_door_type"]="not a door"
        action=seek_corridor_end(p,s,[],distance)
        self.assertEqual("search",action.action["type"])
        self.assertIn(17,p.searched_walls)
        self.assertIsNone(seek_corridor_end(p,s,[],distance))

    def test_dead_end_search_rejects_threats_hunger_health_and_spent_budget(self):
        for mode in ("enemy","hungry","hp","budget","wide"):
            s,p=self.corridor()
            enemies=[]
            if mode=="enemy":enemies=[{"name":"marsupial rat","cell":38}]
            elif mode=="hungry":s["hero"]["buffs"]=[{"name":"hungry"}]
            elif mode=="hp":s["hero"]["hp"]=5
            elif mode=="budget":p.corridor_tip_searches=4
            elif mode=="wide":p.tiles[23]["terrain"]=1
            self.assertIsNone(seek_corridor_end(p,s,enemies,distance),mode)

    def test_generic_search_budget_does_not_skip_new_corridor_tip(self):
        s,p=self.corridor();p.searches=2
        self.assertEqual('search',seek_corridor_end(p,s,[],distance).action['type'])

    def test_finish_corridor_at_cardinal_tip_before_searching(self):
        s,p=self.corridor();s['hero']['cell']=38
        p.paths=lambda state,occupied=():{38:None,31:38,24:31}
        action=seek_corridor_end(p,s,[],distance)
        self.assertEqual(31,action.action['cell'])
        self.assertEqual(0,p.corridor_tip_searches)

    def room(self):
        s = state()
        s["depth"] = 2
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if 3 <= c // 7 <= 5 and 1 <= c % 7 <= 5 else 4,
                               "visible": True} for c in range(49) if c not in range(8, 13)]
        next(t for t in s["map"]["cells"] if t["cell"] == 31)["terrain"] = 8
        s["inventory"].append({"id": "ration", "name": "ration of food", "actions": ["EAT"]})
        return s

    def policy(self, s):
        p = SurvivalPolicy()
        p.update(s)
        p.exhausted.update(p.tiles)
        return p

    def test_room_wall_facing_unknown_space_is_a_candidate(self):
        s = self.room()
        ts = {t["cell"]: t for t in s["map"]["cells"]}
        self.assertEqual(5, wall_scores(ts, 7, 7)[17])
        self.assertNotIn(14, wall_scores(ts, 7, 7))  # Corner, not a doorway.

    def test_known_floor_beyond_wall_has_stronger_shortcut_score(self):
        s = self.room()
        ts = {t["cell"]: t for t in s["map"]["cells"]}
        ts[10] = {"terrain": 1}
        self.assertEqual(8, wall_scores(ts, 7, 7)[17])

    def test_double_thick_wall_is_not_a_door_hypothesis(self):
        s = self.room()
        ts = {t["cell"]: t for t in s["map"]["cells"]}
        ts[10] = {"terrain": 4}
        self.assertNotIn(17, wall_scores(ts, 7, 7))

    def test_one_search_covers_visible_diagonal_walls_only(self):
        s = self.room()
        ts = {t["cell"]: t for t in s["map"]["cells"]}
        self.assertEqual({16, 17, 18}, search_coverage(ts, 24, 7, 7))
        ts[18]["visible"] = False
        self.assertEqual({16, 17}, search_coverage(ts, 24, 7, 7))

    def test_seeks_secret_doors_even_when_downstairs_is_known(self):
        s = self.room()
        p = self.policy(s)
        self.assertEqual("search", p.choose(s).action["type"])
        self.assertEqual({16, 17, 18}, p.searched_walls)
        self.assertNotIn(17, wall_scores(p.tiles, 7, 7, p.searched_walls))

    def test_no_optional_search_on_floor_one_or_when_hungry_or_without_food(self):
        for scenario in ("first floor", "hungry", "no food", "budget"):
            with self.subTest(scenario=scenario):
                s = self.room()
                if scenario == "first floor": s["depth"] = 1
                if scenario == "hungry": s["hero"]["buffs"] = [{"name": "hungry"}]
                if scenario == "no food": s["inventory"].pop()
                p = self.policy(s)
                if scenario == "budget": p.secret_search_steps = 24
                self.assertTrue(p.choose(s).reason.startswith("stairs:"))

    def test_search_memory_resets_on_new_floor(self):
        s = self.room()
        p = self.policy(s)
        p.choose(s)
        s["depth"] = 3
        p.update(s)
        self.assertEqual(set(), p.searched_walls)
        self.assertEqual(0, p.secret_search_steps)

    def test_newly_revealed_door_enters_ordinary_exploration(self):
        s = self.room()
        p = self.policy(s)
        p.choose(s)
        next(t for t in s["map"]["cells"] if t["cell"] == 17)["terrain"] = 5
        d = p.choose(s)
        self.assertEqual("explore: unopened door", d.reason)
        self.assertEqual(17, d.action["cell"])
