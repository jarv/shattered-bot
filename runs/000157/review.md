# ShatteredAI run 000157

Played commit: `85a644da0bd1ea0a1da6f1741bf091fb033668d6`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When retreating from multiple enemies, the bot now avoids ordinary dead-end destinations without a safe onward exit. Verified chokepoints remain eligible.

## Incoming learnings

Low approach pressure alone does not make an ordinary retreat endpoint usable. Require observed, admitted onward space unless the endpoint is a verified choke. Keep escape protection, hazard checks, mandatory collection and explicit planner exhaustion; do not substitute eating or longer waits for a blocked route.

## Analysis

The hero remained alive at full health when mandatory potion discovery exhausted the planner (decision 502, log line 1431). The initiating problem was departure-view preparation that failed after arrival. Decision 460 selected water 1003 while standing in open door 969; at decision 461 the door had closed, invalidating the bank. Decisions 469–470 exposed a second contradiction: bank 1004 remained safe, but its admitted remote storage sites became invisible after moving there. Repeated returns consumed preparation work without resolving protected identification. The final blocker was not an observed death or stopped clock.

Source-pinned offline reconstruction matched actions, reasons, intents and controllers through decision 479, then stopped at the first divergence at decision 480, where recorded loop-guard recovery differed. Later findings use original public observations, not reconstructed continuation. The selecting chain runs through mandatory descent discovery, current bank admission and potion-storage protection. Complete source resolved the packet’s controller and arrival-geometry gaps.

No patch or new regression is supplied. A door-aware rejection alone does not establish useful progress, and allowing invisible storage would bypass inventory protection. The missing safety contract is an executable storage-first transaction from the actual departure position, with fresh arrival checks, accepted drops, interruption handling and complete retrieval. Existing stashing executes from its supplied hero position; invoking it with a hypothetical bank would use the wrong movement origin. The unchanged policy suite passed 2,000 tests with four skipped. No baseline-red/candidate-green result or safe replacement is claimed.

## Recommendations

- **000157-discovery-arrival-transaction — Establish departure-aware, storage-first potion preparation instead of repeatedly selecting banks that fail on arrival.** (high, deferred): Source browsing and validated reconstruction establish the contradiction, but not a safe complete replacement. Storage is admitted from the departure view and invisible at bank arrival; existing execution assumes its supplied hero position is real. Next derive paired decision-460/461 and decision-469/470 fixtures, account for door closure, and validate storage-first preparation from 1003 using bank 1004 and storage 1106. Require accepted movement/drop receipts, fresh arrival checks, interruption safety and actual retrieval before authorizing drinking. Do not fabricate visibility, relax enemy separation or waive carried-potion protection. No policy patch is certified.
  - Evidence: Decision 460, selection line 1288 and accepted line 1289: leave open door 969 for water 1003.; Decision 461, line 1291: door closure invalidates the bank and preparation returns toward the door.; Decisions 469–470, lines 1319–1322: bank 1004 loses visibility of admitted storage sites after arrival.; Decision 502, line 1431: protected potion discovery exhausts with the hero alive at full health.; tools/descent_potions.py:403–473; tools/puzzle_supplies.py:130–154; tools/potion_stash.py:103–160,185–205.
  - Disposition: deferred

## Lessons for the next run

A preparation bank admitted from a departure observation may become unusable after door closure or loss of storage visibility. Validate departure effects and an executable protected-storage transaction before committing transit. Keep unknown identities, hazard checks, mandatory pickup and explicit planner exhaustion intact.

Update: **review-only**.
