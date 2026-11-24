"""Run 236 D755 public approach geometry, not recovered policy memory or replay."""
import unittest

from tools import multi_enemy_tactics as multi
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=277, hp=20, max_hp=28, strength=9)
    terrain = {
        192: 1, 193: 1, 194: 1, 195: 4,
        233: 5, 234: 1, 235: 29, 236: 1, 237: 4,
        275: 4, 276: 1, 277: 29, 278: 1, 279: 4,
        317: 4, 318: 1, 319: 29, 320: 1, 321: 4,
        359: 4, 360: 1, 361: 29, 362: 1, 363: 4,
        401: 4, 402: 18, 403: 29, 404: 18, 405: 4,
    }
    s["map"] = dict(width=42, height=41, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    for tile in s["map"]["cells"]:
        if tile["cell"] in {402, 404}:
            tile["trap"] = "toxic gas trap" if tile["cell"] == 402 else "summoning trap"
    s["objects"] = [
        dict(name="swarm of flies", cell=318),
        dict(name="marsupial rat", cell=360),
        dict(name="sewer crab", cell=403),
    ]
    s["inventory"] = [dict(
        id="armor", name="cloth armor", equipped=True, identified=True,
        description="This tier-1 armor blocks 0-2 damage and requires 10 strength.")]
    p = verified()
    p.update(s)
    return p, s


class EncumberedRetreatPressureTests(unittest.TestCase):
    def test_recorded_endpoint_is_not_single_attacker_during_slow_move(self):
        p, s = fixture()
        # Current contact is distinct from potential approach during movement.
        self.assertEqual(0, sum(multi.can_attack(p, s, e, 235) for e in s["objects"]))
        self.assertEqual(3, multi.approach_pressure(p, s, s["objects"], 235),
                         "Encumbered movement must allow the extra enemy approach opportunity")

    def test_publicly_usable_armor_preserves_normal_envelope(self):
        p, s = fixture()
        s["hero"]["strength"] = 10
        self.assertEqual(1, multi.approach_pressure(p, s, s["objects"], 235))

    def test_unknown_armor_requirement_is_not_treated_as_identified(self):
        p, s = fixture()
        s["inventory"][0]["identified"] = False
        self.assertEqual(1, multi.approach_pressure(p, s, s["objects"], 235))

    def test_sleeping_foes_still_add_no_approach_pressure(self):
        p, s = fixture()
        for e in s["objects"]:
            e["sleeping"] = True
        self.assertEqual(0, multi.approach_pressure(p, s, s["objects"], 235))

    def test_stationary_foe_does_not_gain_movement_from_hero_encumbrance(self):
        p, s = fixture()
        foe = dict(name="demon spawner", cell=360)
        self.assertEqual("stationary", p.unit_strategies.profile(foe).movement)
        self.assertEqual(0, multi.approach_pressure(p, s, [foe], 235))


if __name__ == "__main__":
    unittest.main()
