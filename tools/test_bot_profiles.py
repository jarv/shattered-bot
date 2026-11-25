import copy
import unittest
from unittest.mock import Mock, patch

from tools.bot_profiles import resolve
from tools.mage_policy import MagePolicy
from tools.policy_decision import Decision, Intent, Finished
from tools.policy_runtime import Context, Leaf, Transaction
from tools.simple_navigation import observe, choose, loot, before_descent, dead_end_search, accepted, paths
from tools.test_survival_bot import state, fully_known
from tools.puzzle_supplies import demands
from tools.policy_geometry import distance


def ready():
    s = fully_known(state())
    s["hero"]["level"] = 2
    next(t for t in s["map"]["cells"] if t["cell"] == 25)["terrain"] = 8
    p = MagePolicy(profile="simple-bot")
    p.challenges_verified = True
    p.update(s)
    return s, p


class ProfileTests(unittest.TestCase):
    def test_default_is_legacy_and_invalid_profiles_are_rejected(self):
        self.assertEqual("legacy-bot", MagePolicy().profile.name)
        self.assertTrue(MagePolicy().reserve_floor_puzzle_supplies)
        self.assertFalse(resolve("simple-bot").quests)
        with self.assertRaises(ValueError):
            MagePolicy(profile="simple")

    def test_disabled_objective_leaf_does_not_run(self):
        s, p = ready()
        callback = Mock(return_value=Decision({"type": "wait"}, "quest"))
        self.assertIsNone(Leaf("quest", callback, requires="quests")(Context(p, s)))
        callback.assert_not_called()
        self.assertIsNotNone(Leaf("combat", callback)(Context(p, s)))

    def test_puzzle_reservations_and_quest_observers_are_disabled(self):
        s, p = ready()
        s["objects"] = [{"name": "sad ghost", "cell": 16}, {"name": "red sentry", "cell": 18}]
        p.update(s)
        self.assertFalse(p.reserve_floor_puzzle_supplies)
        self.assertEqual([], demands(p, s, distance))
        self.assertEqual("new", p.ghost_quest["stage"])
        self.assertEqual({}, p.wandmaker_quest)

    def test_combat_uses_same_shared_policy(self):
        s, simple = ready()
        s["objects"] = [{"name": "gnoll scout", "cell": 23, "health_bar": [1, 1]}]
        legacy = MagePolicy()
        legacy.challenges_verified = True
        for p in (legacy, simple):
            p.update(s)
        a, b = legacy.choose(copy.deepcopy(s)), simple.choose(copy.deepcopy(s))
        self.assertEqual(a.action, b.action)
        self.assertEqual(a.intent, b.intent)
        self.assertEqual(a.reason, b.reason)


class SimpleNavigationTests(unittest.TestCase):
    def test_simple_paths_do_not_propose_later_reversal_of_a_protected_retreat_edge(self):
        s, p = ready()
        for c, tile in p.tiles.items():
            tile["terrain"] = 1 if c in {23, 24, 25} else 4
        s["hero"]["cell"] = 25
        p.escape_commitment = {"edges": [(23, 24)], "hp": 20, "charges": 0, "age": 0}
        self.assertIn(24, paths(p, s))
        self.assertNotIn(23, paths(p, s))
        self.assertIn(23, paths(p, s, avoid_retreats=False))

    def test_quiet_escape_commitment_can_reobserve_without_a_current_enemy_memory(self):
        from tools.simple_navigation import reobserve_temporary_threats
        s, p = ready()
        p.escape_commitment = {"edges": [(25, 24)], "hp": 20, "charges": 0, "age": 0}
        p.recent_threats.clear()
        action = reobserve_temporary_threats(p, s, [], observe(p, s))
        self.assertEqual({"type": "wait"}, action.action)
        self.assertTrue(action.simple_threat_reobserve)

    def test_bounded_memory_reobservation_can_hold_closed_door_cover_at_noncritical_health(self):
        from tools.simple_navigation import reobserve_temporary_threats
        s, p = ready()
        s["hero"]["hp"] = 9
        p.recent_threats = {8: {"name": "dm-100", "cell": 8, "observations_ago": 5}}
        floor = observe(p, s)
        for c in list(p.tiles):
            if c != s["hero"]["cell"]:p.tiles[c]["terrain"] = 4
        p.tiles[25]["terrain"] = 8  # A known goal only in the counterfactual.
        with patch("tools.challenge_combat.exposure", return_value={"exposure": 0}), \
                patch("tools.simple_navigation.paths", return_value={24: None, 25: 24}), \
                patch("tools.dm100_escape.exposed_memory", return_value=False):
            action = reobserve_temporary_threats(p, s, [], floor)
            self.assertEqual({"type": "wait"}, action.action)
            self.assertEqual({}, floor["searches"])
            s["hero"]["hp"] = 6
            self.assertIsNone(reobserve_temporary_threats(p, s, [], floor))

    def test_missing_stairs_can_use_shared_mapping_resource_without_puzzle_objective(self):
        s, p = ready()
        p.tiles[25]["terrain"] = 1
        information = Decision({"type": "item", "id": "mapping", "action": "READ"}, "reveal")
        with patch("tools.preparation_prerequisites.reconnaissance", return_value=information) as scout:
            action = choose(p, s, [])
        self.assertIs(action, information)
        scout.assert_called_once_with(p, s)
        self.assertIn("mapping resource", action.reason)

    def test_known_stairs_do_not_trigger_optional_mapping(self):
        s, p = ready()
        with patch("tools.preparation_prerequisites.reconnaissance") as scout:
            self.assertEqual(Intent.DESCEND, choose(p, s, []).intent)
        scout.assert_not_called()

    def test_longer_lived_dm100_memory_constrains_navigation_after_recent_sighting_expires(self):
        from tools.public_evidence import bind_threat
        from tools.simple_navigation import remembered_threats
        s, p = ready()
        p.dm100_threat = {"cell": 8, "age": 7}
        bind_threat(p, s, p.dm100_threat, 8)
        p.recent_threats.clear()
        self.assertEqual("DM-100", remembered_threats(p, s)[0]["name"])
        with patch("tools.dm100_escape.sees", side_effect=lambda _p, _s, source, target: target == 25), \
                patch("tools.challenge_combat.exposure", return_value={"exposure": 0}):
            self.assertNotIn(25, paths(p, s))
            self.assertIn(25, paths(p, s, avoid_memories=False))

    def test_low_health_temporary_threat_reobservation_uses_safe_step_not_wait(self):
        from tools.simple_navigation import reobserve_temporary_threats
        s, p = ready()
        s["hero"]["hp"] = 12
        for tile in p.tiles.values():
            tile["observed"] = True
        p.recent_threats = {8: {"name": "prison guard", "cell": 8, "observations_ago": 6}}
        with patch("tools.challenge_combat.exposure", return_value={"exposure": 0}):
            action = reobserve_temporary_threats(p, s, [], observe(p, s))
        self.assertEqual("cell", action.action["type"])
        self.assertTrue(action.simple_threat_reobserve)

    def test_temporary_memory_reobservation_is_bounded_accepted_only_and_not_for_sleepers(self):
        from tools.simple_navigation import reobserve_temporary_threats
        s, p = ready()
        p.recent_threats = {8: {"name": "gnoll scout", "cell": 8, "observations_ago": 4}}
        floor = observe(p, s)
        with patch("tools.challenge_combat.exposure", return_value={"exposure": 0}):
            action = reobserve_temporary_threats(p, s, [], floor)
            self.assertEqual({"type": "wait"}, action.action)
            self.assertNotIn("threat_reobservations", floor)
            accepted(p, s, action, s)
            self.assertEqual(1, floor["threat_reobservations"])
            p.recent_threats[8]["sleeping"] = True
            self.assertIsNone(reobserve_temporary_threats(p, s, [], floor))
            p.recent_threats[8]["sleeping"] = False
            floor["threat_reobservations"] = 16
            self.assertIsNone(reobserve_temporary_threats(p, s, [], floor))

    def test_goo_defeat_preempts_remaining_frontiers_without_level_gain(self):
        s, p = ready()
        s["depth"] = 5
        p.update(s)
        p.keys["worn"] = 1
        p.tiles[25]["terrain"] = 21
        p.tiles[26]["terrain"] = 5
        action = choose(p, s, [])
        self.assertEqual(Intent.DESCEND, action.intent)
        self.assertIn("Goo defeated", action.reason)
        self.assertFalse(observe(p, s)["level_gained"])
        self.assertTrue(p.planner.report["simple_descent"]["doors"])
        p.loot[23] = {"name": "gold", "cell": 23, "top_item": {"name": "gold"}}
        self.assertEqual(Intent.LOOT, choose(p, s, []).intent)

    def test_worn_key_admits_boss_exit_as_descent_target(self):
        s, p = ready()
        p.tiles[25]["terrain"] = 21
        self.assertNotIn(25, paths(p, s))
        p.keys["worn"] = 1
        action = choose(p, s, [])
        self.assertEqual(Intent.DESCEND, action.intent)
        self.assertEqual(25, action.navigation_route[-1])

    def test_level_gain_and_final_descent_gate_do_not_skip_a_held_iron_key(self):
        s, p = ready()
        s["hero"]["level"] += 1
        p.tiles[26]["terrain"] = 10
        p.keys["iron"] = 1
        for action in (choose(p, s, []), before_descent(
                p, s, Decision({"type": "cell", "cell": 25}, "leave", Intent.DESCEND))):
            self.assertEqual(Intent.EXPLORE, action.intent)
            self.assertEqual(26, action.navigation_route[-1])
            self.assertIn("held key", action.reason)

    def test_unusable_key_is_reported_but_does_not_force_exhaustive_search(self):
        s, p = ready()
        p.keys["iron"] = 1
        action = Decision({"type": "cell", "cell": 25}, "leave", Intent.DESCEND)
        with patch("tools.descent_potions.begin", return_value=None):
            self.assertIs(action, before_descent(p, s, action))
        self.assertTrue(any(o["obligation"]["kind"] == "unspent floor keys"
                            for o in p.deferred_obligations))

    def test_iron_and_crystal_keys_admit_observed_matching_doors(self):
        from tools.simple_navigation import paths, ordinary_work
        s, p = ready()
        p.tiles[26]["terrain"] = 10
        p.keys["iron"] = 0
        self.assertNotIn(26, paths(p, s))
        p.keys["iron"] = 1
        self.assertIn(26, paths(p, s))
        self.assertIn(26, ordinary_work(p, s, paths(p, s))[0])
        action = choose(p, s, [])
        self.assertEqual(Intent.EXPLORE, action.intent)
        p.tiles[26]["terrain"] = 31
        p.keys["crystal"] = 1
        self.assertIn(26, paths(p, s))
        p.crystal_key_requirement = 3
        self.assertNotIn(26, paths(p, s))

    def test_golden_key_admits_locked_chest_without_special_room_controller(self):
        s, p = ready()
        s["objects"] = [{"name": "locked chest", "cell": 23}]
        s["keys"] = [{"name": "golden key", "quantity": 1, "depth": s["depth"]}]
        p.update(s)
        self.assertIn(23, loot(p, s)[0])
        self.assertEqual(Intent.LOOT, choose(p, s, []).intent)

    def test_exhausted_ordinary_frontiers_does_not_require_visiting_every_tile(self):
        s, p = ready()
        self.assertTrue(any(not p.visits[c] for c in p.paths(s)))
        action = choose(p, s, [])
        self.assertEqual(Intent.DESCEND, action.intent)
        self.assertFalse(p.descent_counts_as_clear())

    def test_one_level_gain_preempts_new_doors_but_not_observed_pickups(self):
        s, p = ready()
        next(t for t in s["map"]["cells"] if t["cell"] == 26)["terrain"] = 5
        p.update(s)
        self.assertEqual(Intent.EXPLORE, choose(p, s, []).intent)
        s["hero"]["level"] = 3
        s["objects"] = [{"name": "gold", "cell": 23, "top_item": {"name": "gold"}}]
        p.update(s)
        self.assertEqual(Intent.LOOT, choose(p, s, []).intent)
        p.loot.clear()
        p.unconfirmed_loot.clear()
        self.assertEqual(Intent.DESCEND, choose(p, s, []).intent)
        self.assertTrue(observe(p, s)["level_gained"])

    def test_level_baseline_is_per_floor_branch_and_survives_revisits(self):
        s, p = ready()
        s["hero"]["level"] = 3
        self.assertTrue(observe(p, s)["level_gained"])
        s["depth"] = 2
        self.assertFalse(observe(p, s)["level_gained"])
        s["branch"] = 1
        self.assertFalse(observe(p, s)["level_gained"])
        s.update(depth=1, branch=0)
        self.assertTrue(observe(p, s)["level_gained"])

    def test_known_loot_out_of_current_sight_still_blocks_departure(self):
        s, p = ready()
        p.loot[23] = {"name": "ration of food", "cell": 23, "top_item": {"name": "ration of food"}}
        p.tiles[23]["visible"] = False
        self.assertIn(23, loot(p, s)[0])
        self.assertEqual(Intent.LOOT, before_descent(p, s, Decision(
            {"type": "cell", "cell": 25}, "leave", Intent.DESCEND)).intent)

    def test_locked_chests_and_unsafe_loot_are_reported_not_pursued(self):
        s, p = ready()
        p.loot[23] = {"name": "locked chest", "cell": 23}
        action = choose(p, s, [])
        self.assertEqual(Intent.DESCEND, action.intent)
        self.assertTrue(p.planner.report["simple_excluded_pickups"])
        self.assertTrue(p.deferred_obligations)
        p.loot[23] = {"name": "potion of strength", "cell": 23}
        p.tiles[23].update(terrain=18, trap="summoning trap")
        self.assertNotIn(23, loot(p, s)[0])
        p.loot[23] = {"name": "gold", "cell": 23}
        self.assertNotIn(23, loot(p, s)[0])

    def test_newly_revealed_pickups_are_rechecked_on_descent(self):
        s, p = ready()
        action = choose(p, s, [])
        p.loot[23] = {"name": "gold", "cell": 23, "top_item": {"name": "gold"}}
        self.assertEqual(Intent.LOOT, before_descent(p, s, action).intent)

    def test_progression_keys_are_not_mistaken_for_special_containers(self):
        s, p = ready()
        for name in ("skeleton key", "crystal key"):
            p.loot[23] = {"name": name, "cell": 23, "top_item": {"name": name}}
            self.assertIn(23, loot(p, s)[0])

    def test_reobserved_absent_loot_does_not_resurrect_out_of_sight(self):
        s, p = ready()
        remembered = {"name": "dewdrop", "cell": 23, "top_item": {"name": "dewdrop"}}
        p.unconfirmed_loot[23] = remembered
        self.assertNotIn(23, loot(p, s)[0])
        s = copy.deepcopy(s)
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["visible"] = False
        p.tiles[23]["visible"] = False
        self.assertNotIn(23, loot(p, s)[0])
        self.assertIn(23, p.unconfirmed_loot)  # Never credited as collected.
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["visible"] = True
        s["objects"] = [remembered]
        self.assertIn(23, loot(p, s)[0])  # Fresh actual heap reopens pickup.

    def test_navigation_recovery_cannot_fall_back_to_endless_idle(self):
        from tools.policy_decision import TacticalBlocked
        s, p = ready()
        p.soft_failures["navigation-loop"] = 11
        with self.assertRaises(Finished):
            p.recover_tactical_block(s, TacticalBlocked("navigation-loop", "stalled pickup route"))

    def test_mapped_unobserved_space_uses_an_ordinary_visible_frontier(self):
        s, p = ready()
        p.tiles[26].update(mapped=True, observed=False)
        # The neighboring vantage has not yet been visited; no coverage sweep.
        p.exhausted.discard(19)
        action = choose(p, s, [])
        self.assertEqual(Intent.EXPLORE, action.intent)

    def test_remembered_threat_does_not_block_unexposed_navigation_everywhere(self):
        s, p = ready()
        # A far memory constrains exposure, not all ordinary floor navigation.
        p.recent_threats = {8: {"name": "gnoll scout", "cell": 8, "observations_ago": 1}}
        action = choose(p, s, [])
        self.assertEqual(Intent.DESCEND, action.intent)

    def test_sleeping_enemy_does_not_force_a_retreat_or_approach_wait(self):
        s, p = ready()
        s["objects"] = [{"name": "gnoll scout", "cell": 8, "sleeping": True}]
        p.update(s)
        p.loot[23] = {"name": "gold", "cell": 23, "top_item": {"name": "gold"}}
        action = choose(p, s, s["objects"])
        self.assertEqual(Intent.LOOT, action.intent)

    def test_shared_combat_never_conserves_magic_by_waiting_for_a_sleeper(self):
        from tools.policy_nodes import ordinary_combat
        for profile in ("legacy-bot", "simple-bot"):
            s, _ = ready()
            enemy = {"name": "gnoll scout", "cell": 26, "sleeping": True}
            s["inventory"][0]["status"] = "1/4"
            p = MagePolicy(profile=profile)
            p.update(s)
            context = Context(p, s, enemies=[enemy], active=[], engage=[enemy])
            attack = Decision({"type": "item", "id": "item-0", "action": "ZAP"}, "attack")
            with patch.object(p, "best_attack", return_value=attack) as choose_attack:
                self.assertIs(attack, ordinary_combat(context))
                self.assertFalse(choose_attack.call_args.kwargs["reserve"])
            with patch.object(p, "best_attack", return_value=None):
                self.assertIsNone(ordinary_combat(context))
            self.assertFalse(p.combat_waits)

    def test_shared_doorway_releases_hold_when_only_sleepers_remain(self):
        from tools.doorway_tactics import hold_doorway
        from tools.policy_geometry import neighbors, line_clear
        for profile in ("legacy-bot", "simple-bot"):
            s, _ = ready()
            p = MagePolicy(profile=profile)
            p.update(s)
            p.doorway_hold = {"depth": 1, "hide": 24, "door": 25, "inputs": 0, "quiet": 0, "waits": 0}
            enemy = {"name": "gnoll scout", "cell": 26, "sleeping": True}
            with patch.object(p, "best_attack", return_value=None):
                self.assertIsNone(hold_doorway(p, s, [enemy], distance, neighbors, line_clear))
            self.assertIsNone(p.doorway_hold)

    def test_discovery_and_owned_item_debt_remain_descent_gates(self):
        s, p = ready()
        action = Decision({"type": "cell", "cell": 25}, "leave", Intent.DESCEND)
        recovery = Decision({"type": "wait"}, "safe identification preparation")
        with patch("tools.descent_potions.begin", return_value=recovery):
            self.assertIs(recovery, before_descent(p, s, action))
        with patch.object(p.physical_ledger, "has_unresolved", return_value=True):
            with self.assertRaises(Finished):
                before_descent(p, s, action)

    def test_locked_boss_floor_and_immediate_threats_cannot_descend(self):
        s, p = ready()
        action = Decision({"type": "cell", "cell": 25}, "leave", Intent.DESCEND)
        s["hero"]["buffs"] = [{"name": "floor is locked"}]
        with self.assertRaises(Finished):
            before_descent(p, s, action)
        s["hero"]["buffs"] = []
        s["danger_cells"] = [24]
        with self.assertRaises(Finished):
            before_descent(p, s, action)

    def test_unknown_stairs_continue_ordinary_navigation_after_level_gain(self):
        s, p = ready()
        s["hero"]["level"] = 3
        p.tiles[25]["terrain"] = 1
        p.tiles[26]["terrain"] = 5
        action = choose(p, s, [])
        self.assertEqual(Intent.EXPLORE, action.intent)
        self.assertIn("downstairs", action.reason)

    def test_search_is_incidental_bounded_and_counts_only_accepted_inputs(self):
        s = fully_known(state())
        s["hero"]["cell"] = 25
        for t in s["map"]["cells"]:
            t["terrain"] = 1 if t["cell"] in {23, 24, 25} else 4
        p = MagePolicy(profile="simple-bot")
        p.update(s)
        p.tiles.pop(27)  # Unobserved space behind the corridor-end wall.
        floor = observe(p, s)
        decision = dead_end_search(p, s, floor, [])
        self.assertEqual({"type": "search"}, decision.action)
        self.assertEqual({}, floor["searches"])
        transaction = Transaction(p)
        accepted(p, s, decision, s)
        transaction.rollback()
        self.assertEqual({}, observe(p, s)["searches"])
        accepted(p, s, decision, s)
        accepted(p, s, decision, s)
        self.assertIsNone(dead_end_search(p, s, observe(p, s), []))
        s["hero"]["level"] += 1
        self.assertIsNone(dead_end_search(p, s, observe(p, s), [23]))
