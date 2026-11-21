# ShatteredAI run 000086

Played commit: `285daea9d532eaeeb394e534b9c73728f1fcf835`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now postpones reading identification scrolls while blinded, then allows another attempt once sight returns without treating blindness as a failed inventory choice.

## Incoming learnings

A listed item action is not proof that it can execute under current impairments. Check observed blindness before creating identification menu intent, and retain retry eligibility for a fresh sighted observation without erasing genuine failed-inventory exclusions.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. Decision 403 (log line 1141) followed three accepted quiet doorway waits; the last wait advanced the clock (line 1139). Earlier escape-reversal failures at decisions 353, 355, 389 and 391 consumed recovery options. Offline reconstruction pinned to the played source and recorded public inputs matched all 403 selected actions, reasons and intents. It showed that the final distant threat memory expired during selection, but escape protection was only released by earlier accepted-action feedback, when that memory still existed. The normal food-pickup route through door 398 was consequently vetoed. Recovery rolled back the fresh observation, excluded that reversal and the exhausted alternate edge, then stopped while hungry. The correction rechecks the existing quiet-release prerequisites after threat expiry, without changing waiting limits, hazard admission, pickup obligations or the terminal label. A new regression failed on the original policy with the expected retained-reversal assertion, then passed on the candidate. The full suite passed 1,828 tests with four skips. An isolated candidate probe on the validated terminal state selected the existing food-route step; this does not establish subsequent collection or survival.

## Recommendations

- **000086-expired-threat-escape-release — Release already-quiet escape protection when the final stale threat expires before selection.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 353 and 355, log lines 1001–1009: earlier escape-reversal recovery.; Decisions 389 and 391, log lines 1102–1110: repeated reversal vetoes consume alternate recovery edges.; Decisions 396–402, log lines 1124–1139: doorway retreat, interception and accepted quiet waits.; Decision 403, log line 1141: planner exhaustion with a living full-health hero.; Validated offline terminal-state probe: existing food route selects door 398 after obsolete protection is released.
  - Disposition: implemented

## Lessons for the next run

Accepted quiet recovery and fresh threat-memory expiry must be reconciled before route arbitration. Releasing obsolete escape protection is not evidence of an enemy kill or completed loot; retain ordinary movement safety and pickup verification.

Update: **accepted**.
