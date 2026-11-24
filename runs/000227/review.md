# ShatteredAI run 000227

Played commit: `1e69e5fa207c09134a76f581dbb6c670f9c73b7f`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Keep mandatory keys distinct from already collected upgrade resources. Large aquariums need a separately justified preparation plan: a charged staff and a visible fish do not satisfy the current whole-enclosure visibility requirement. Preserve shore exclusion, honest pickup receipts, potion identification and the terminal stuck-planner label.

## Analysis

The run ended in planner failure with a living, full-health hero, not an observed death. Decision 276 (log lines 806–808) opened a locked chest and revealed a skeleton key item without collecting it. At decision 277 (lines 809–811), substring-based crypt recognition incorrectly excluded that exposed heap from ordinary pickup routes. Source-pinned offline reconstruction matched all 277 preceding selected actions and reasons; an isolated candidate probe then selected the item pickup without dispatch. The proposed correction narrowly distinguishes the corroborated item heap from unopened remains and retains hazard checks and honest collection receipts. Independently, mandatory potion discovery remained blocked by missing haste for the recognized sentry room. Its geometry was complete, but no reachable bank satisfied the current distance-five staging envelope; geometry-revelation fallbacks therefore offered no progress. The pickup correction does not establish a sentry solution or successful descent.

## Recommendations

- **000227-skeleton-key-heap — Do not classify a corroborated skeleton key item heap as an unopened crypt container.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 276, log lines 806–808: opening chest 148 reveals a skeleton key top_item without pickup.; Decision 277, log lines 809–811: the item remains visible when planning exhausts.; tools/special_rooms.py:95; tools/survival_policy.py:444–450; tools/region_navigation.py:141 in the played source.; Source-pinned offline reconstruction matches indices 0–276; an isolated corrected terminal selection chooses pickup at 148.
  - Disposition: implemented
- **000227-sentry-staging-envelope — Provide executable preparation for a complete sentry room whose safe entrance lies outside the testing envelope.** (high, deferred): This independent preparation defect is not repaired by the single heap-classification change. The concrete safety blocker is the absence of a validated outside-envelope testing and return transaction: ordinary entrance water is six rows from the sentry, while nearer access crosses defended carpet. Complete source and reconstruction resolved the missing-state gap, not replacement safety. Next derive paired entrance and terminal fixtures proving inventory isolation, unknown-effect recovery, fresh arrival and an actual-haste-funded reward return before changing staging. Do not simply remove the proximity check, infer protection or abandon the obligation.
  - Evidence: Decisions 232 and 242, log lines 674 and 704: chest 1236 and red sentry 1447 are observed.; Decision 277, log line 809: missing haste reservation and all four preparation prerequisites remain blocked.; Validated original terminal reconstruction: complete sentry geometry, but no reachable cell within the distance-five test envelope.; tools/puzzle_supplies.py:574–605,977–1014; tools/descent_potions.py:350–392.
  - Disposition: deferred

## Lessons for the next run

Distinguish a publicly exposed skeleton key item from skeletal remains, and verify actual collection afterward. Keep the separate sentry preparation obligation: a complete room can still lack an admitted testing bank. Do not infer haste, cross defended carpet, waive mandatory pickup or replace planner exhaustion with waiting.

Update: **accepted**.
