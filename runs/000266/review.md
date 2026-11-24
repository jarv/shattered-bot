# ShatteredAI run 000266

Played commit: `b6979632b752dc9e8d46a33282b3af84cb068422`

Outcome: dead

Java build: `51bdb688a8fed22859aa80c5a30a841418fb3c1d6da0f7e728dd727d4914879c`

Outcome summary: Died during retreat from a mimic and sewer crabs

## Improvements since the last run

- The bot can now pause for fresh observations when brief roots prevent movement, but only at full health with no observed threats or nearby hazards. These pauses are bounded and do not count as collecting items.
- The bot can now use a carried stone of intuition to investigate a missing pool-room potion while hungry. Failed guesses about other potions do not automatically exclude this attempt.

## Incoming learnings

Hungry pool preparation should retain safely admitted intuition hypotheses even when earlier generic guesses canceled. Identification attempts must remain bounded and public-menu verified; they do not establish potion identity, protection, a safe return route or collection.

## Analysis

The hero died during retreat with a mimic and sewer crabs observed; the recording does not identify an unambiguous killer. The episode began with the suspicious-container test at decisions 929–930, followed by mimic kiting. At decision 935, the newly observed crab and mimic triggered a doorway retreat; its accepted first step lost 12 of 30 HP (log lines 2731–2735). Decision 936 canceled that route for excessive injury, then immediately restarted it with a lower health baseline (2736–2737). The pursuit injury limit was already exceeded, but tools/pursuit_budget.py:142–155 delayed its enforcement until the next four-move review. The proposed correction checks that existing injury limit immediately, without changing movement, hazard, collection or terminal safeguards. A reduced public-input regression validates the preceding selected step and reconstructs accepted feedback, not the full runtime memory. It fails on original policy and passes after correction; the full suite passes 2,461 tests with four skips. This establishes timely retirement of new unverified lures, not prevention of the first injury, a different next movement, successful collection or survival. Post-death item revelations were not treated as pre-death knowledge. There were no recorded planner incidents.

## Recommendations

- **000266-immediate-pursuit-injury-review — Enforce the existing accepted-injury budget before another doorway setup can reset its health baseline.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 935, log lines 2731–2735: doorway retreat loses 12 HP and records the fifth accepted retreat.; Decision 936, log lines 2736–2737: excessive-loss cancellation is followed by a new setup toward the same door.; tools/mage_policy.py:1172–1185; tools/pursuit_budget.py:142–155; tools/multi_enemy_tactics.py:135–166,234–277.
  - Disposition: implemented

## Lessons for the next run

Accepted injury must retire exhausted lure setups immediately, rather than waiting for the periodic movement review. Canceling and restarting a doorway plan must not erase the encounter’s accumulated health loss. Verified escapes remain eligible; retirement is not proof of safety or survival.

Update: **accepted**.
