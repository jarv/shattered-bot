# ShatteredAI run 000205

Played commit: `e7579bdf8bdedf7a1476619a88d93c0da9f71ab6`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish an immediate single-attacker opportunity from a permanent choke. A newly reached hold can be abandoned because of a distant bypass; before changing that handoff, validate a bounded stationary interception and fresh-observation reassessment rather than allowing indefinite holding or speculative retreat. This run did not exercise the recovery-accounting improvement.

## Analysis

The hero was alive at full health when mandatory preparation exhausted. The terminal message mentioned upgrade/strength loot, but the complete veto identified an iron key beside an aquarium, not the upgrade scroll: decision 379 collected that scroll and decision 382 used it. The key was observed at decision 491; a matching locked door appeared at decision 589. Aquarium water and its melee bank remained excluded, while the room-supply planner deliberately offered no pool-potion experiment for this chestless aquarium. Earlier observations offered a different preparation opportunity: a charged, identified magic-missile staff could target the visible ordinary piranha from outside its water reach. The proposed correction admits only that stationary shot under fresh geometry, line-of-fire, health, hunger and threat checks. It neither moves onto the bank nor credits a kill or pickup. A reduced public-evidence fixture fails on the original selector and passes on the candidate. The full suite passed 2,168 tests with four skips. This does not establish fish defeat, key retrieval, puzzle completion or improved survival; original runtime memory was not fully reconstructed.

## Recommendations

- **000205-aquarium-key-clearance — Prepare aquarium-guarded keys with admitted stationary magic missiles instead of overlooking them until mandatory pickup blocks descent.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 491, log line 1460: iron key first observed beside the aquarium.; Decisions 523–540, log lines 1544–1595: visible piranha and charged staff during exterior exploration.; Decision 589, log line 1741: matching iron-key door observed.; Decision 644, log lines 1897–1899: key at cell 1687 excluded by room safety; mandatory preparation terminates planning.
  - Disposition: implemented

## Lessons for the next run

A chestless aquarium is not evidence of an invisibility-potion supply. Preserve its water and shore exclusions, but consider a known stationary magic-missile shot from a fully observed safe exterior when it guards a key. Reobserve actual defeat and collection before advancing the obligation.

Update: **accepted**.
