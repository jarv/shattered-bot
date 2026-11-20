"""Runs 16/18: protected inventory and discovery before unreachable loot fallback."""
import copy
import unittest
from unittest.mock import patch

from tools.test_challenge_rules import verified
from tools.test_regular_feedback import arena
from tools.policy_geometry import distance, neighbors
from tools.potion_stash import can_protect_potions, protect_potions
from tools.puzzle_supplies import safe_test_bank
from tools.piranha_tactics import choose as pool, pending
from tools.priority_resources import choose as priority
from tools.mapping_knowledge import observe, complete
from tools.policy_runtime import Transaction


def potion(name="jade potion", quantity=1):
    return dict(id=name, name=name, quantity=quantity, identified=False, actions=["DROP", "THROW", "DRINK"])


def bandolier():
    return dict(id="bag", name="potion bandolier", identified=True, quantity=1,
                description="While inside the bandolier, your potions should be protected from the cold.",
                actions=["DROP", "THROW"])


def pool_approach(stack=False, bag=False):
    s, _ = arena()
    s["depth"] = 7
    s["hero"].update(cell=101, hp=65, max_hp=65, buffs=[])
    s["map"] = dict(width=11, height=13, cells=[
        dict(cell=c, terrain=4 if c % 11 in {0, 10} or c // 11 in {0, 12}
             else 29 if 1 <= c % 11 <= 3 and 3 <= c // 11 <= 7 else 1,
             visible=True, observed=True) for c in range(143)])
    s["objects"] = [dict(cell=57, name="giant piranha"), dict(cell=24, name="Chest")]
    s["inventory"] = [i for i in s["inventory"] if "potion" not in i["name"]]
    s["inventory"].append(potion(quantity=3 if stack else 1))
    if bag:
        s["inventory"] += [bandolier(), potion("azure potion")]
    p = verified()
    if bag:
        before = copy.deepcopy(s)
        before["inventory"] = [i for i in before["inventory"] if i["name"] != "potion bandolier"]
        p.update(before)  # Public acquisition, not assumed storage from a standalone bag snapshot.
    p.update(s)
    p.room_actors.clear()  # The observed habitat/chest persists, not a hidden fish location.
    s["objects"] = []
    return s, p


class PoolBandolierTests(unittest.TestCase):
    def test_seven_cell_chest_distance_uses_the_actual_trip_budget(self):
        s, p = pool_approach()
        self.assertEqual(7, distance(101, 24, 11))
        self.assertTrue(safe_test_bank(p, s, 101, distance, neighbors, allow_dry=True, pool_bank=True))
        d = pool(p, s, [])
        self.assertIsNotNone(d, "An arbitrary five-cell reward radius must not exclude an admitted trip")
        self.assertEqual("DRINK", d.action.get("action"))
        self.assertIn(24, pending(p))
        self.assertIsNone(p.room_journey.advance(p, s, [], neighbors))  # Still requires the actual buff.
        self.assertIn(24, pending(p))

    def test_bandolier_allows_a_stacked_candidate_without_remote_drops(self):
        s, p = pool_approach(stack=True, bag=True)
        before = copy.deepcopy(s)
        candidate = next(i for i in s["inventory"] if i["name"] == "jade potion")
        self.assertTrue(can_protect_potions(p, s, candidate, distance, neighbors, lambda *a, **k: False))
        self.assertIsNone(protect_potions(p, s, candidate, distance, neighbors, lambda *a, **k: False))
        d = pool(p, s, [])
        self.assertEqual("DRINK", d.action.get("action"))
        self.assertEqual("jade potion", d.action["id"])
        self.assertIsNone(p.potion_stash)
        self.assertEqual(before, s)  # No fabricated identity, consumption, or collection.

    def test_missing_or_overfull_bandolier_still_requires_ordinary_protection(self):
        for case in ("absent", "overfull"):
            with self.subTest(case=case):
                s, p = pool_approach(stack=True, bag=case == "overfull")
                if case == "overfull":
                    s["inventory"] += [potion("extra potion " + str(n)) for n in range(19)]
                candidate = next(i for i in s["inventory"] if i["name"] == "jade potion")
                self.assertFalse(can_protect_potions(p, s, candidate, distance, neighbors, lambda *a, **k: False))

    def test_waterskin_and_liquid_metal_count_toward_bandolier_capacity(self):
        s, p = pool_approach(stack=True, bag=True)
        s["inventory"] += [potion("extra potion " + str(n)) for n in range(16)]
        candidate = next(i for i in s["inventory"] if i["name"] == "jade potion")
        self.assertTrue(can_protect_potions(p, s, candidate, distance, neighbors, lambda *a, **k: False))
        s["inventory"] += [dict(id="water", name="waterskin"), dict(id="metal", name="liquid metal")]
        self.assertFalse(can_protect_potions(p, s, candidate, distance, neighbors, lambda *a, **k: False))

    def test_bandolier_is_not_itself_a_potion_to_drop(self):
        from tools.potion_stash import potions
        s, p = pool_approach(stack=True, bag=True)
        self.assertNotIn("potion bandolier", [i["name"] for i in potions(s)])

    def test_previous_overflow_is_not_erased_by_consumption_or_floor_change(self):
        from tools.potion_stash import observe_bandolier, bandolier_protected
        s, p = pool_approach(stack=True, bag=True)
        self.assertTrue(bandolier_protected(p,s))
        before = copy.deepcopy(s)
        s["inventory"] += [potion("overflow potion " + str(n)) for n in range(20)]
        observe_bandolier(p,s)
        p.memory.reset_floor(8)
        observe_bandolier(p,before)
        self.assertFalse(bandolier_protected(p,before))

    def test_initial_bag_snapshot_is_not_a_container_receipt(self):
        from tools.potion_stash import observe_bandolier, bandolier_protected
        s, _ = pool_approach(stack=True, bag=True)
        p = verified()
        observe_bandolier(p,s)
        self.assertFalse(bandolier_protected(p,s))

    def test_unprotected_stack_can_still_be_identified_without_drinking(self):
        s, p = pool_approach(stack=True)
        s["inventory"].append(dict(id="identify", name="scroll of identify", identified=True, actions=["READ"]))
        d = pool(p, s, [])
        self.assertEqual(dict(type="item", id="identify", action="READ"), d.action)
        self.assertIsNone(p.room_journey)

    def test_unknown_testing_does_not_bypass_health_or_hazard_checks(self):
        for case in ("health", "trap", "enemy"):
            with self.subTest(case=case):
                s, p = pool_approach(stack=True, bag=True)
                if case == "health": s["hero"]["hp"] = 50
                if case == "trap": p.tiles[101]["trap"] = "poison dart trap"
                d = pool(p, s, [dict(name="gnoll scout", cell=100)] if case == "enemy" else [])
                self.assertTrue(d is None or d.action.get("action") != "DRINK")
                self.assertIsNone(p.room_journey)

    def test_closed_entrance_is_opened_before_a_protected_stack_test(self):
        s, p = pool_approach(stack=True, bag=True)
        for cell,terrain in ((89,4),(90,5),(91,4)):
            p.tiles[cell]["terrain"] = terrain
            next(t for t in s["map"]["cells"] if t["cell"] == cell)["terrain"] = terrain
        d = pool(p, s, [])
        self.assertEqual(dict(type="cell", cell=90), d.action)
        self.assertFalse(p.puzzle_drinks)
        self.assertIsNone(p.room_journey)

    def test_trip_budget_and_observed_protection_still_control_entry_and_chest_use(self):
        s, p = pool_approach(stack=True, bag=True)
        pool(p, s, [])
        journey = p.room_journey
        self.assertIsNotNone(journey)
        s["hero"]["buffs"] = [dict(name="invisible", description="Turns remaining: 20")]
        self.assertEqual(dict(type="cell", cell=journey.route[1]), journey.advance(p,s,[],neighbors).action)
        # Separate chest-arrival fixture, not evidence of an accepted game move.
        s["hero"].update(cell=24, buffs=[dict(name="invisible", description="Turns remaining: 13")])
        self.assertEqual(dict(type="cell", cell=24), journey.advance(p,s,[],neighbors).action)
        self.assertIn(24,pending(p))  # Opening/clicking is not a collection receipt.
        s, p = pool_approach(stack=True, bag=True)
        s["hero"]["cell"] = 112  # A longer trip must stage closer, not spend protection here.
        d = pool(p,s,[])
        self.assertTrue(d is None or d.action.get("action") != "DRINK")
        self.assertIsNone(p.room_journey)


class StrengthRouteDiscoveryTests(unittest.TestCase):
    def fixture(self):
        s, _ = arena()
        s["depth"] = 6
        s["hero"].update(hp=40, max_hp=59, buffs=[dict(name="hungry")])
        s["inventory"].append(dict(id="map", name="scroll of magic mapping", quantity=1,
                                  identified=True, actions=["READ", "DROP"]))
        p = verified()
        p.update(s)
        p.loot[41] = dict(cell=41, name="potion of strength",
                          top_item=dict(name="potion of strength", identified=True))
        p.room_blocked.add(41)  # Independent unreachable-reward fixture, not inferred safe terrain.
        return s, p

    def test_unreachable_strength_uses_known_mapping_before_two_searches(self):
        s, p = self.fixture()
        self.assertEqual(0, p.searches)
        d = priority(p, s, [])
        self.assertIsNotNone(d)
        self.assertEqual(dict(type="item", id="map", action="READ"), d.action)
        self.assertFalse(complete(p, s))  # Proposal is not a mapping receipt.
        self.assertIn(41, p.loot)

    def test_reachable_strength_is_collected_without_spending_mapping(self):
        s, p = self.fixture()
        p.room_blocked.clear()
        d = priority(p, s, [])
        self.assertEqual(dict(type="cell", cell=41), d.action)
        self.assertFalse(p.mapping_attempts)

    def test_admitted_room_preparation_is_preferred_to_spending_mapping(self):
        s, p = self.fixture()
        preparation = p.cell(25,"room: existing verified preparation")
        with patch("tools.puzzle_supplies.prepare_supplies",return_value=preparation):
            self.assertIs(preparation,priority(p,s,[]))
        self.assertFalse(p.mapping_attempts)

    def test_mapping_not_repeated_or_used_under_threat_or_for_optional_food(self):
        for case in ("mapped", "attempted", "enemy", "recent", "food", "immune"):
            with self.subTest(case=case):
                s, p = self.fixture()
                if case == "mapped": p.mapped_floors.add((6, 0))
                if case == "attempted": p.mapping_attempts.add(6)
                if case == "recent": p.recent_threats[25] = dict(name="gnoll scout")
                if case == "food": p.loot[41] = dict(cell=41, name="ration of food")
                if case == "immune": s["hero"]["buffs"].append(dict(name="magic immune"))
                d = priority(p, s, [dict(name="gnoll scout", cell=25)] if case == "enemy" else [])
                self.assertTrue(d is None or d.action.get("id") != "map")

    def test_rejected_mapping_proposal_rolls_back_and_receipt_is_still_required(self):
        s, p = self.fixture()
        transaction = Transaction(p)
        d = priority(p, s, [])
        self.assertIn(6, p.mapping_attempts)
        transaction.rollback()
        self.assertFalse(p.mapping_attempts)
        self.assertFalse(complete(p, s))
        after = copy.deepcopy(s)
        after["inventory"] = [i for i in after["inventory"] if i.get("id") != "map"]
        self.assertTrue(observe(p, s, d, after))
        self.assertTrue(complete(p, s))


if __name__ == "__main__":
    unittest.main()
