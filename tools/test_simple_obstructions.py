import unittest
from tools.simple_obstructions import choose
from tools.simple_navigation import observe, accepted
from tools.test_bot_profiles import ready


class SimpleObstructionTests(unittest.TestCase):
    def test_closed_ordinary_door_is_an_observation_endpoint_not_permission_to_enter_cloud(self):
        s, p = ready()
        for c, t in p.tiles.items():
            t.update(terrain=1 if c in {23,24,25} else 4, observed=True, effects=[])
        s["hero"]["cell"] = 23
        p.tiles[24]["terrain"] = 5
        p.tiles[25].update(visible=False, effects=["The air is unnaturally frigid here."])
        p.room_blocked.add(25)
        # Unknown space beyond the cloud gives an actual information goal.
        p.tiles.pop(26)
        p.tiles[25]["terrain"] = 1
        action = choose(p, s, [], observe(p, s))
        self.assertEqual({"type": "cell", "cell": 24}, action.action)
        self.assertEqual("cold-reobserve", action.simple_obstruction)
        self.assertIn(25, p.room_blocked)
        self.assertTrue(p.tiles[25]["effects"])

    def test_offscreen_cold_requires_return_for_reobservation_not_expiry_wait(self):
        s, p = ready()
        p.tiles[25].update(visible=False, observed=True, effects=["The air is unnaturally frigid here."])
        p.room_blocked.add(25)
        for tile in p.tiles.values():tile["observed"] = True
        floor = observe(p, s)
        # Already-spent visible waiting is not evidence of offscreen expiry.
        floor["obstruction_waits"] = {"cold": 16}
        action = choose(p, s, [], floor)
        self.assertEqual("cell", action.action["type"])
        self.assertNotEqual(25, action.action["cell"])
        self.assertEqual("cold-reobserve", action.simple_obstruction)
        self.assertTrue(p.tiles[25]["effects"])
        self.assertIn(25, p.room_blocked)
        accepted(p, s, action, s)
        self.assertEqual(1, floor["obstruction_waits"]["cold-reobserve"])
    def test_ghost_exit_wait_is_bounded_accepted_only_and_not_quest_interaction(self):
        s, p = ready()
        s["objects"] = [{"name": "sad ghost", "cell": 25}]
        p.update(s)
        floor = observe(p, s)
        a = choose(p, s, [], floor)
        self.assertEqual({"type": "wait"}, a.action)
        self.assertNotIn("obstruction_waits", floor)
        for _ in range(8):
            accepted(p, s, a, s)
        self.assertIsNone(choose(p, s, [], floor))
        self.assertEqual("new", p.ghost_quest["stage"])

    def test_cold_feasibility_does_not_clear_cloud_or_credit_route(self):
        s, p = ready()
        # Adjacent cloud still blocks its tile, not a safe wait outside it.
        # Distant route to the exit blocked by a temporary cloud.
        p.tiles[25]["effects"] = ["The air is unnaturally frigid here."]
        p.room_blocked.add(25)
        floor = observe(p, s)
        original = p.tiles[25]
        a = choose(p, s, [], floor)
        self.assertEqual({"type": "wait"}, a.action)
        self.assertIs(original, p.tiles[25])
        self.assertIn(25, p.room_blocked)
        self.assertTrue(p.tiles[25]["effects"])
        accepted(p, s, a, s)
        self.assertEqual(1, floor["obstruction_waits"]["cold"])
        floor["obstruction_waits"]["cold"] = 16
        self.assertIsNone(choose(p, s, [], floor))

    def test_current_harm_or_threat_does_not_wait_out_cloud(self):
        s, p = ready()
        s["objects"] = [{"name": "sad ghost", "cell": 25}]
        p.update(s)
        for kind in ("enemy", "damage", "poison"):
            p.unseen_damage_turns = int(kind == "damage")
            s["hero"]["buffs"] = [{"name": "poison"}] if kind == "poison" else []
            self.assertIsNone(choose(p, s, [{"name": "rat"}] if kind == "enemy" else [], observe(p, s)))
