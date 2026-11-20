# ShatteredAI run 000012

Played commit: `5b55cf99ff5ec9bec3261dc466ec8346cb7a0099`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died while starving after potion preparation stalled

## Improvements since the last run

- Alchemy preparation tracks inventory charge/equipment changes and separates rendered global energy from toolkit charge.

## Incoming learnings

Finding one secret does not establish that an exit is reachable. Keep necessary bounded missing-exit search distinct from optional secret-room hunting. A search-vantage selection is preparation, not evidence of a door or successful progression.

## Analysis

The initiating defect was potion-test staging, not merely the final waits. Decision 556 approached the levitation room; at decision 557, a bank with no admitted remote potion stash triggered a preparation failure (log 1613). Recovery disabled all floor potion-supply work. Later, the uncollected piranha chest prevented descent (decision 596, logs 1732–1734), followed by extensive continuation waits. Offline reconstruction of the played selector matched recorded actions and reasons through decision 596. An isolated copy showed that another observed bank admitted both the test journey and stash preparation. The correction preflights existing stash requirements before selecting an unknown-potion test bank, declining infeasible preparation without weakening hazards or pickup obligations. The new regression fails on the original policy and passes on the candidate; the full suite passes 1529 tests with four skips. Candidate reconstruction stops at its first changed selection, decision 557. The final accepted wait reduced HP from 1 to 0 while starving (decision 2391, log 6961); no attacker is established. Post-death potion identities were not treated as prior knowledge. This establishes preparation selection, not puzzle success or survival improvement.

## Recommendations

- **000012-potion-stash-bank-preflight — Preflight remote potion protection before committing to an unknown-potion test bank.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 556, logs 1610–1611: levitation-room approach; Decision 557, logs 1613–1616: stash veto and recovery; Decision 596, logs 1732–1734: pending piranha chest blocks descent
  - Disposition: implemented

## Lessons for the next run

An admitted protected reward journey is insufficient for an unknown potion test: verify protection of other carried potions before choosing its staging bank. Local preparation infeasibility must not unnecessarily disable unrelated mandatory room work.

Update: **accepted**.
