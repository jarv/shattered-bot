# ShatteredAI run 000162

Played commit: `62de05aa8f44db289577ae3d9c75a349dc2cc377`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now remembers safe potion-preparation ground even before finding its first potion. Before returning with newly collected potions, it checks whether the carried inventory can be protected and still requires fresh checks on arrival.

## Incoming learnings

Remember safe preparation ground even before finding the first potion, but replan protection for the actual carried inventory and reobserve on arrival. An admitted return is not proof that the subsequent storage transaction will succeed.

## Analysis

The hero remained alive at full health when mandatory potion discovery exhausted the planner (decision 814, log 2268). The initiating contradiction was a return-route rule that excluded plain grass: decisions 810–812, logs 2257–2264, had just traversed water 362, water 329, grass 364 and floor 365. Offline bookkeeping reconstructed from the exact played source and public observations matches all 814 preceding selected actions and the terminal blocker; this is reconstructed state, not recorded memory. Every remembered bank was disconnected in the restricted return graph despite ordinary reachability. The proposed narrow correction admits plain observed grass only for preparation-return transit, retaining all hazard, visibility, inventory-protection, hunger and arrival gates. A copied validated terminal-state probe selects a return step to 364 without dispatch. The new regression fails by the expected assertion on original policy and passes on the candidate; the full suite passes 2020 tests with four skips. This establishes a preparation choice, not successful arrival, storage, drinking or progression.

## Recommendations

- **000162-grass-bank-transit — Allow hazard-checked plain-grass transit when returning to witnessed potion preparation ground.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 810, logs 2257–2258: the hero leaves water bank 362 for water 329.; Decisions 811–812, logs 2260–2264: accepted ordinary travel crosses plain grass 364 to floor 365.; Decision 814, log 2268: protected potion discovery and its return prerequisite exhaust with the hero at 30/30 HP.; tools/descent_potions.py:107–136: the return graph and route validator exclude plain grass.; Validated original-state reconstruction and an isolated candidate probe select return step 364 without authorizing a drink.
  - Disposition: implemented

## Lessons for the next run

Distinguish ordinary travel terrain from unknown-potion test terrain. Plain grass can connect a witnessed preparation area without becoming an admitted drinking site. Reobserve and validate storage on arrival; do not credit discovery or collection from a planned return.

Update: **accepted**.
