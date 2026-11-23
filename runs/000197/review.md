# ShatteredAI run 000197

Played commit: `903dfc51ea161d9c6196b7ae56500688063982d7`

Outcome: blocked

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Blocked in a shop selling-menu loop

## Improvements since the last run

- The bot now reviews the results of its retreats before emergency movement interrupts preparation. This lets it retire exhausted, unverified doorway setups while keeping its existing retreat safety checks.

## Incoming learnings

Review accepted pursuit outcomes before yielding preparation to emergency retreat. Retiring unverified doorway setups must leave existing hazard-filtered retreats and verified holds available. Do not infer that a changed retreat resolves pursuit or prevents death; stop offline continuation at the first changed selection.

## Analysis

The run ended blocked, not dead, with the hero at full health. The initiating defect was incomplete selling-menu navigation: identified goo was eligible for sale, but the selector searched only the backpack and ignored the visible Velvet Pouch tab. Decisions 1748–1751 (lines 5050–5057) show the first offer/open/backpack/cancel cycle. Repeated unchanged attempts culminated in the execution-failure incident at decision 1777 (line 5108). Accepted transitions show no elapsed game time during this menu cycle. Source confirms that the pouch can contain goo. A local helper-chain reconstruction, not recorded policy memory, matches original actions and reasons for decisions 1748–1751. The candidate matches through 1750 and selects the observed pouch tab at 1751; investigation stops there without supplying later observations. The focused correction adds once-only pouch navigation while retaining candidate validation, quote checks, receipt verification and terminal loop protection. The new regression has two expected assertion failures on original policy and passes all four tests after correction; the full suite passes 2,150 tests with four skipped. No actual sale, purchase or improved survival is established.

## Recommendations

- **000197-sale-pouch-navigation — Support the observed Velvet Pouch tab when locating an already-admitted sale candidate.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1748, lines 5050–5051: keeper interaction begins the sale attempt; public inventory contains identified goo and a velvet pouch.; Decisions 1750–1751, lines 5054–5057: backpack navigation is followed by cancellation despite a visible Velvet Pouch tab.; Decision 1777, line 5108: repeated selling-menu attempts terminate as an execution failure with the hero alive.; tools/inventory_tactics.py:142–179: the original sale selector searches only Backpack before cancelling.
  - Disposition: implemented

## Lessons for the next run

Sale candidates need supported navigation to their observed containers. Browse the visible pouch tab without guessing item slots, and require a matching item title, live quote and inventory-removal-plus-gold receipt before recording a sale. Stop offline investigation at the first changed decision.

Update: **accepted**.
