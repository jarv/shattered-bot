"""Public decision 776 geometry: preparation movement must reach loop accounting."""
import unittest

from tools.test_regular_feedback import arena
from tools.test_challenge_rules import verified
from tools.policy_geometry import distance, neighbors
from tools.puzzle_supplies import prepare_supplies, open_journey_entrance
from tools.room_tactics import Journey
from tools.policy_decision import Intent, TacticalBlocked
from tools.survival_policy import NavigationLoopGuard


def entrance():
    s, _ = arena()
    s['depth'] = 3
    s['hero'].update(cell=394, hp=30, max_hp=30, buffs=[])
    groups = {
        (4, True): [96,97,98,99,100,133,140,170,177,207,214,244,251,
                    318,355,393,395,432,469,506,537,543,574,575,576,577,578,579,580],
        (4, False): [101,102,103,288,325,362,392,396,397,399],
        (1, True): [134,135,136,137,138,139,282,283,284,285,286,287,
                    319,320,322,323,356,357,358,359],
        (29, True): [171,172,174,175,176,208,209,211,212,213,245,246,
                     248,249,250,538,539,540,541,542],
        (14, True): [173,210,247], (5, True): [281], (7, True): [321],
        (1, False): [324,361], (20, False): [360], (6, True): [394],
        (5, False): [398],
        (18, True): [429,430,431,465,466,467,468,501,502,503,504,505],
    }
    s['map'] = {'width':37, 'height':47, 'cells':[
        dict(cell=c, terrain=t, visible=v, observed=True)
        for (t,v), cells in groups.items() for c in cells]}
    s['objects'] = [dict(cell=540, name='Chest')]
    s['inventory'] = [
        dict(id=str(n), name=name, quantity=1, identified=False,
             actions=['DROP','THROW','DRINK'])
        for n,name in enumerate(('azure potion','indigo potion','magenta potion'))]
    p = verified()
    p.update(s)
    return s,p


class PuzzleNavigationIntentTests(unittest.TestCase):
    def assert_accounted(self, s, d):
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertTrue(d.navigation)
        self.assertFalse(d.tracks_movement)  # Not a loot/exploration receipt.
        # Isolated accounting probe, not a sequence of game observations:
        # repeated identical no-progress proposals must reach the existing guard.
        guard = NavigationLoopGuard()
        with self.assertRaises(TacticalBlocked):
            for _ in range(guard.repetitions):
                guard.check(s,d)

    def test_unknown_test_staging_is_navigation_not_other(self):
        s,p = entrance()
        d = prepare_supplies(p,s,[],distance,neighbors)
        self.assertEqual({'type':'cell','cell':356},d.action)
        self.assert_accounted(s,d)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)
        self.assertIsNone(p.potion_stash)
        self.assertIn(540,p.loot)
        self.assertFalse(p.completed_room_rewards)

    def test_entrance_opening_is_navigation_without_spending_protection(self):
        s,p = entrance()
        # Independent helper fixture matching the public decision 777 entrance.
        # No observations are generated or fed after a changed selector decision.
        s['hero']['cell'] = 356
        p.tiles[394]['terrain'] = 5
        ready,d = open_journey_entrance(
            p,s,Journey('flight',[356,394,430,466,502,540],3))
        self.assertFalse(ready)
        self.assertEqual({'type':'cell','cell':394},d.action)
        self.assert_accounted(s,d)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)


if __name__ == '__main__':
    unittest.main()
