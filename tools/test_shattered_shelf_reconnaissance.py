"""Stationary scouting of the unseen shelf backs in recording 000107."""
import unittest
from tools.preparation_prerequisites import reconnaissance
from tools.policy_decision import Intent
from tools.policy_runtime import Transaction
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


class ShelfReconnaissanceTests(unittest.TestCase):
    def fixture(self):
        s = state()
        s["hero"].update(cell=1342, hp=25, max_hp=25, buffs=[])
        # A reduced observed shelf edge: paths end at floor 1495, while
        # shelf 1494 separates the reachable floor from unknown cell 1493.
        terrain = {1342: 14, 1495: 14, 1494: 27}
        for c in (1342, 1495):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    terrain.setdefault(c + dy * 39 + dx, 4)
        terrain.pop(1493, None)
        s["map"] = dict(width=39, height=50, cells=[
            dict(cell=c, terrain=t, observed=True, visible=True)
            for c, t in terrain.items()])
        s["objects"] = []
        s["inventory"] = [dict(id="scry", name="stone of clairvoyance",
                               identified=True, quantity=1, actions=["THROW", "DROP"])]
        p = verified()
        p.update(s)
        # Isolate the frontier classification, not pathfinding across the
        # omitted middle of the floor. Both cells were publicly reachable.
        p.paths = lambda *args, **kwargs: {1342: None, 1495: 1342}
        return p, s

    def test_shelf_back_gap_admits_one_stationary_known_reveal(self):
        p, s = self.fixture()
        d = reconnaissance(p, s)
        self.assertIsNotNone(d, "Shelf-blocked unknown space needs nonconsumptive reconnaissance")
        self.assertEqual(dict(type="item", id="scry", action="THROW"), d.action)
        self.assertEqual(1342, p.target)
        self.assertEqual(Intent.REPOSITION, d.intent)
        self.assertFalse(p.strength_identified)
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.mapped_floors)
        self.assertIsNone(reconnaissance(p, s))

    def test_no_scout_without_local_unseen_shelf_back_or_safe_resource(self):
        for case in ("known-back", "mapped-back", "wall", "remote",
                     "no-stone", "danger", "recent", "effects",
                     "invisible", "complete", "outside-radius", "damage", "unobserved-shelf"):
            with self.subTest(case=case):
                p, s = self.fixture()
                if case in {"known-back", "mapped-back"}:
                    for c in list(p.tiles):
                        if p.tiles[c]["terrain"] == 27:
                            for dy in (-1, 0, 1):
                                for dx in (-1, 0, 1):
                                    n = c + dy * 39 + dx
                                    p.tiles.setdefault(n, dict(cell=n, terrain=4,
                                        observed=case == "known-back", mapped=case == "mapped-back"))
                elif case == "wall": p.tiles[1494]["terrain"] = 4
                elif case == "remote": p.paths = lambda *a, **kw: {1342: None}
                elif case == "no-stone": s["inventory"] = []
                elif case == "danger": s["danger_cells"] = [1342]
                elif case == "recent": p.recent_threats[1343] = dict(name="marsupial rat", cell=1343)
                elif case == "effects": p.tiles[1342]["effects"] = ["fire"]
                elif case == "invisible": s["hero"]["buffs"] = [dict(name="invisible")]
                elif case == "complete": p.mapped_floors.add((s["depth"], s.get("branch", 0)))
                elif case == "outside-radius":
                    s["hero"]["cell"] = 40
                    p.tiles[40] = dict(cell=40, terrain=1, visible=True, observed=True)
                elif case == "damage": p.unseen_damage_turns = 1
                elif case == "unobserved-shelf":
                    p.tiles[1494]["observed"] = False
                    p.tiles[1494]["mapped"] = True
                self.assertIsNone(reconnaissance(p, s))

    def test_rejected_proposal_can_be_rolled_back(self):
        p, s = self.fixture()
        tx = Transaction(p)
        self.assertIsNotNone(reconnaissance(p, s))
        tx.rollback()
        self.assertIsNotNone(reconnaissance(p, s))


if __name__ == "__main__":
    unittest.main()
