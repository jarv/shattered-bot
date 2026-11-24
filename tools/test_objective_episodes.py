"""Coordination transitions and synthetic multi-input contracts, not replays."""
import copy
import itertools
import json
import unittest

from tools.objective_episodes import (
    EpisodeRegistry, Status, Evidence, EvidenceKind, Scope,
)
from tools.objective_planning import (
    PREPARATION, exhaust_preparation, preparation_allowed,
)
from tools.policy_decision import Decision, Intent, TacticalBlocked
from tools.policy_runtime import Transaction
from tools.policy_geometry import distance, neighbors, line_clear
from tools.room_supplies import observe
from tools.tactical_recovery import recover
from tools.test_shattered_stash_supply_rearming import fixture


SUPPLY = EvidenceKind.NEW_UNTESTED_SUPPLY


class EpisodeContracts(unittest.TestCase):
    def test_explicit_retry_reopens_only_matching_context(self):
        r = EpisodeRegistry()
        scope = Scope(2)
        r.exhaust("preparation", scope, "blocked stash", retry_on=(SUPPLY,))
        r.exhaust("probe", scope, "budget exhausted")
        for other in (Scope(3), Scope(2, 1)):
            self.assertFalse(r.accept(Evidence(SUPPLY, other, "ivory potion", 1)))
            self.assertFalse(r.allowed("preparation", scope))
        self.assertEqual(["preparation"],
                         r.accept(Evidence(SUPPLY, scope, "ivory potion", 1)))
        self.assertTrue(r.allowed("preparation", scope))
        self.assertFalse(r.allowed("probe", scope))
        self.assertEqual(2, r.episodes["preparation", scope].attempt)
        json.dumps(r.records())

    def test_old_or_duplicate_evidence_cannot_restart_another_attempt(self):
        r = EpisodeRegistry()
        scope = Scope(2)
        event = Evidence(SUPPLY, scope, "ivory potion", 9)
        r.accept(event)  # Evidence predating the exhaustion is not new later.
        r.exhaust("preparation", scope, "blocked", retry_on=(SUPPLY,))
        self.assertFalse(r.accept(event))
        self.assertFalse(r.allowed("preparation", scope))
        self.assertTrue(r.accept(Evidence(SUPPLY, scope, "ivory potion", 10)))
        r.exhaust("preparation", scope, "blocked again", retry_on=(SUPPLY,))
        self.assertFalse(r.accept(Evidence(SUPPLY, scope, "ivory potion", 10)))
        self.assertFalse(r.allowed("preparation", scope))

    def test_short_event_sequences_match_reference_transition_table(self):
        # Exhaustive short sequences cover hard failure overwriting retryable
        # failure, repeated evidence, and new evidence without another failure.
        for events in itertools.product(("soft", "hard", "one", "two"), repeat=5):
            r = EpisodeRegistry()
            scope = Scope(2)
            allowed, retry, seen = True, False, set()
            for event in events:
                if event in ("soft", "hard"):
                    retry = event == "soft"
                    allowed = False
                    r.exhaust("p", scope, event, retry_on=(SUPPLY,) if retry else ())
                else:
                    if event not in seen and not allowed and retry:
                        allowed, retry = True, False
                    seen.add(event)
                    r.accept(Evidence(SUPPLY, scope, "ivory potion", event))
                self.assertEqual(allowed, r.allowed("p", scope), events)

    def test_rollback_restores_episodes_evidence_and_reports_together(self):
        p, s, d, after = fixture()
        tx = Transaction(p)
        observe(p, s, d, after)
        self.assertTrue(preparation_allowed(p, s))
        tx.rollback()
        self.assertFalse(preparation_allowed(p, s))
        self.assertEqual("exhausted", p.planner.report["objective_episodes"][0]["status"])
        self.assertFalse(p.room_supply_pickups)
        observe(p, s, d, after)
        self.assertTrue(preparation_allowed(p, s))

    def test_floor_reset_does_not_resolve_physical_obligations(self):
        p, s, _, _ = fixture()
        unfinished = copy.deepcopy(p.deferred_obligations)
        s["depth"] += 1
        p.update(s)
        self.assertFalse(p.objective_episodes.records())
        self.assertTrue(preparation_allowed(p, s))
        self.assertEqual(unfinished, p.deferred_obligations)

    def test_failure_modes_do_not_acquire_a_new_supply_retry(self):
        for mode in ("drop", "pending", "budget", "wrong-branch", "wrong-floor"):
            with self.subTest(mode=mode):
                plan = dict(depth=2, branch=0, cell=1198, bank=1195,
                            candidate="turquoise potion", phase="retrieve",
                            dropped={"azure potion": 1}, pending=None, steps=9)
                if mode == "drop": plan["phase"] = "drop"
                elif mode == "pending": plan["pending"] = ("azure potion", 1)
                elif mode == "budget": plan["steps"] = 49
                elif mode == "wrong-branch": plan["branch"] = 1
                else: plan["depth"] = 1
                # Alternative initial failure, not a second owner taking over
                # an already deferred stash at the same physical location.
                p, s, d, after = fixture(plan)
                observe(p, s, d, after)
                self.assertFalse(preparation_allowed(p, s))
                episode = p.objective_episodes.episodes[PREPARATION, Scope.of(s)]
                self.assertEqual(Status.EXHAUSTED, episode.status)
                self.assertFalse(episode.retry_on)

    def test_duplicate_pickup_does_not_rearm_later_exhaustion(self):
        p, s, d, after = fixture()
        after["observation_id"] = 10
        observe(p, s, d, after)
        exhaust_preparation(p, after, "another failure", new_supply_can_retry=True)
        observe(p, s, d, after)
        self.assertFalse(preparation_allowed(p, after))

    def test_migrated_failure_pickup_and_real_provider_keep_obligations(self):
        # Synthetic continuation through the real pool preparation provider.
        # This establishes equipment preparation selection, not a successful
        # potion test, protected crossing, stash return, or chest collection.
        from tools.test_shattered_pool_armor_preparation import fixture as pool_fixture
        from tools.piranha_tactics import choose, pending
        p, before = pool_fixture()
        potion = before["inventory"].pop()
        cell = before["hero"]["cell"]
        before["objects"].append(dict(cell=cell, top_item=potion, name=potion["name"]))
        p.potion_stash = dict(depth=6, branch=0, cell=9999, bank=cell,
                              candidate="turquoise potion", phase="retrieve",
                              dropped={"azure potion": 2}, pending=None, steps=9)
        recover(p, before, [], TacticalBlocked("obligation:potion-stash",
                "blocked old return"), distance, neighbors, line_clear)
        self.assertFalse(preparation_allowed(p, before))
        self.assertIsNone(choose(p, before, []))
        unfinished = copy.deepcopy(p.deferred_obligations)
        after = copy.deepcopy(before)
        after["inventory"].append(potion)
        after["objects"] = [o for o in after["objects"] if not o.get("top_item")]
        after["observation_id"] = 8
        observe(p, before, Decision(dict(type="cell", cell=cell), "pickup", Intent.LOOT), after)
        p.update(after)
        self.assertTrue(preparation_allowed(p, after))
        action = choose(p, after, [])
        self.assertIsNotNone(action)
        self.assertEqual(dict(type="item", id="cloth", action="EQUIP"), action.action)
        self.assertEqual(unfinished, p.deferred_obligations)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.descent_counts_as_clear())
        self.assertIn(2040, pending(p))
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.puzzle_drinks)

    def test_stash_cannot_advance_on_another_branch(self):
        from tools.potion_stash import advance_stash
        p, s, _, _ = fixture()
        p.potion_stash = dict(depth=2, branch=1, bank=459, cell=422,
                              phase="retrieve", dropped={}, pending=None, steps=0)
        with self.assertRaises(TacticalBlocked):
            advance_stash(p, s, [], distance)
        self.assertIsNotNone(p.potion_stash)


if __name__ == "__main__":
    unittest.main()
