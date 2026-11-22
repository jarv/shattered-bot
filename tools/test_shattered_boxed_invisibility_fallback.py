"""Reduced public decision-857 geometry: protection is real, exits are occupied."""
import unittest
from unittest.mock import patch

from tools.mage_policy import MagePolicy
from tools.continuation import best_effort
from tools.combat_positioning import invisible_withdrawal, CombatPositioningBlocked
from tools.policy_geometry import distance, line_clear
from tools.test_survival_bot import state


def boxed():
    s = state()
    s.update(depth=3, branch=0)
    s["hero"].update(cell=720, hp=14, max_hp=30,
                     buffs=[{"name": "invisible"}])
    terrain = {691: 4, 692: 1, 693: 4, 719: 4, 720: 1,
               721: 4, 747: 1, 748: 1, 749: 4}
    s["map"] = dict(width=28, height=40, cells=[
        dict(cell=c, terrain=t, visible=True, observed=True, effects=[])
        for c, t in terrain.items()])
    s["objects"] = [
        dict(name="marsupial rat", cell=692),
        dict(name="gnoll scout", cell=747),
        dict(name="swarm of flies", cell=748, health_bar=[3, 21]),
    ]
    s["inventory"] = [dict(
        name="staff of magic missile +2", id="item-0", status="0/6",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE"],
        description="This _tier-1_ melee weapon deals _3-10 damage_ "
                    "and requires _9 strength_ to use properly.")]
    p = MagePolicy()
    p.update(s)
    return p, s


class BoxedInvisibilityFallbackTests(unittest.TestCase):
    def test_failed_withdrawal_does_not_authorize_breaking_protection(self):
        p, s = boxed()
        with self.assertRaises(CombatPositioningBlocked):
            invisible_withdrawal(p, s, s["objects"], distance, line_clear)
        self.assertEqual([720], list(p.paths(s, {692, 747, 748})))
        self.assertIsNone(best_effort(p, s, s["objects"]))

    def test_fly_last_resort_is_not_a_protection_bypass(self):
        p, s = boxed()
        with patch("tools.fly_tactics.desperate_attack") as attack:
            self.assertIsNone(best_effort(p, s, s["objects"]))
            attack.assert_not_called()

    def test_unprotected_last_resort_remains_available(self):
        p, s = boxed()
        s["hero"]["buffs"] = []
        result = best_effort(p, s, s["objects"])
        self.assertIsNotNone(result)
        self.assertEqual({"type": "cell", "cell": 692}, result.action)


if __name__ == "__main__":
    unittest.main()
