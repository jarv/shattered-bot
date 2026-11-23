# ShatteredAI run 000204

Played commit: `3d7b9d38d46423f771864b448ed542746193771a`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died under multiple-enemy pressure

## Improvements since the last run

- When combat interrupts a recovery trip toward the stairs, the bot no longer counts those combat actions as failed navigation attempts. The overall recovery action limit still applies.

## Incoming learnings

Keep survival interruptions distinct from failed navigation attempts without granting unlimited recovery. Pool preparation still needs an executable, hunger-funded identification and protected retrieval plan; full health and unidentified potions alone do not establish one.

## Analysis

The hero died under multiple-enemy pressure; no unambiguous killer is recorded. Decision 365 (accepted log line 1060) activated a hidden alarm trap during frontier movement. Decisions 372–376 then approached door 705 and reached holding square 664. Decision 377 (line 1101) abandoned that newly established hold for another door; decision 382 reported no verified hold at door 669, followed by exhausted retreat options and damaging combat. The final accepted attack at decision 396 (line 1177) reduced HP from 5 to 0. There were no planner incidents. Source inspection traces the earlier handoff through tools/mage_policy.py:1126–1131 and tools/multi_enemy_tactics.py:68–110,147–151. An isolated public-input probe reproduces the retreat choice and finds that the existing hold helper offers a stationary entry attack instead. However, observed terrain contains a genuine long bypass around the gate: low immediate approach pressure does not establish a lasting choke. Offline reconstruction validated selections 0–126 only; the recorded tactical recovery at decision 127 remains unreconstructed. No patch or regression is supplied because neither indefinite hold retention nor a bounded replacement attack has established flank-arrival, damage and continuation safety. Next validate the recovery and subsequent prefix, then test a single fresh-entry interception with conservative bypass timing and explicit refusal cases. The leather armor's +1 identity was revealed only after death and cannot justify a pre-death equipment decision.

## Recommendations

- **000089-multi-rat-retreat-feasibility — Validate a bounded fresh-entry interception before abandoning a newly established hold for another doorway.** (high, deferred): No safe replacement is established. The public map has a genuine bypass from the queued rat around door 705 to the holding bank, so removing global choke admission could permit eventual flanking. The existing stationary entry attack is selectable in an isolated probe, but its bounded damage, flank-arrival and continuation contract is unvalidated. Source-pinned reconstruction matches selections 0–126; the recorded decision-127 tactical recovery and subsequent selecting memory remain unresolved. Next validate that recovery through decision 376, derive paired arrival/hold fixtures, and prove a single fresh-entry interception with refusal tests for short bypasses, actual flanks, ranged or accelerated enemies, unknown perimeter, low HP and stale holds. Do not infer later observations after a changed choice or weaken hazard and pickup checks.
  - Evidence: Decision 365, accepted log line 1060: frontier movement activates a hidden alarm trap.; Decision 376, selected line 1096 and accepted line 1097: the hero reaches holding square 664 behind door 705.; Decision 377, line 1101: another doorway commitment begins despite one immediate approach slot in the isolated public-input probe.; Decision 382, lines 1126–1127: door 669 has no verified hold, and another retreat starts.; Decisions 384–396: admitted retreat options disappear, magic is exhausted, and the final accepted attack ends in death.; tools/mage_policy.py:1126–1131; tools/multi_enemy_tactics.py:68–110,147–151; tools/doorway_tactics.py:42–68.
  - Disposition: deferred

## Lessons for the next run

Distinguish an immediate single-attacker opportunity from a permanent choke. A newly reached hold can be abandoned because of a distant bypass; before changing that handoff, validate a bounded stationary interception and fresh-observation reassessment rather than allowing indefinite holding or speculative retreat. This run did not exercise the recovery-accounting improvement.

Update: **review-only**.
