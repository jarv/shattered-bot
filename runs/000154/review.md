# ShatteredAI run 000154

Played commit: `fb5151b64ec7521063f9f1586fbc35a804594d89`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When hungry but healthy and safely out of combat, the bot can use a carried intuition stone to test whether an unknown potion is purity. An earlier failed strength guess no longer prevents this separate test.

## Incoming learnings

Separate hunger restrictions on unknown drinking from safe information actions. A failed strength hypothesis does not identify a potion or rule out a different declared intuition hypothesis. Keep gas-room rewards mandatory and require actual identity, protection and collection observations before proceeding.

## Analysis

The planner stopped with the hero alive at full health, not dead. Earlier great-crab doorway approaches failed, followed by prolonged retreat. Offline policy-bookkeeping reconstruction against this revision matches decisions 0–1725 and reproduces the terminal failure. Pursuit exhaustion then excluded even an immediate verified sight break at the doorway already occupied: decision 1721, line 4912, retreats from door 485 to 486 without retaining the doorway plan. The same departure passes the existing sight-line and second-exit checks. Subsequent enemy-memory pursuit conflicts with escape protection at decisions 1722 and 1724, ending in hungry recovery exhaustion at decision 1726, line 4931. The focused correction retains the existing doorway workflow only at the currently occupied door after exhaustion; travel to new setups remains forbidden. The new regression fails on original source and passes on the candidate; the full suite passes 1,990 tests with four skipped. This establishes selector/bookkeeping behavior, not a future surprise strike, quest completion or survival.

## Recommendations

- **000154-crab-current-door-exhaustion — Retain an admitted current-door sight-break transaction after the new-lure travel budget is exhausted.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1688, line 4781: an unsuccessful doorway approach falls back to ordinary enemy-memory pursuit.; Decision 1721, line 4912: the hero occupies door 485 with the crab at 394 and retreats to 486 without retaining a doorway plan.; Decisions 1722 and 1724, lines 4916 and 4923: enemy-memory pursuit is rejected as escape reversal.; Decision 1726, line 4931: hungry no-progress recovery exhausts with the hero alive at 45/45 HP.; tools/great_crab_tactics.py:153-180; tools/pursuit_budget.py:review_outcome; new current-door exhaustion regression.
  - Disposition: implemented

## Lessons for the next run

Distinguish exhausted lure travel from an immediately verified sight break at the current doorway. Preserve accepted-departure and fresh-entry evidence before attacking; an eligible departure alone does not prove surprise or quest success.

Update: **accepted**.
