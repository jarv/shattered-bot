# ShatteredAI run 000218

Played commit: `c405efbdc3e116ac4c980785e3eb54bbedcf80d0`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- After a food pickup is refused because the pack is full, the bot now tries its guarded inventory cleanup before retrying, even while starving. It still requires observed collection before counting the food as acquired.

## Incoming learnings

A publicly refused food pickup needs inventory relief before another attempt, even while starving. Keep refusal evidence tied to the current inventory and correct bag; preserve guarded disposal and require actual receipts before crediting either a drop or collection. A stopped game clock is not continuing starvation damage.

## Analysis

The run ended in planner exhaustion, not an observed death: decision 414 shows a ready, living Mage at 17/25 HP with vertigo. Decision 413 (log lines 1215–1217) pursued the observed upgrade scroll; its accepted move from 785 to 819 triggered a previously hidden confusion-gas trap. The pre-move observation did not expose that trap. At decision 414 (lines 1218–1220), the vertigo controller rejected escape because its terrain model treated the passable depth exit at 784 as an unsafe landing and the solid storage barrel at 855 as a possible landing. Both independently invalidate the original all-direction check. Pinned game source confirms that random movement can land on exits but bumps against these barrels. Waiting in renewing gas is intentionally excluded; known purity, blink and teleport supplies were absent, and healing at this health does not satisfy the rescue rule. Mandatory upgrade pickup is correctly preempted by vertigo safety, not completed or waived. Earlier unfinished dewdrop obligations remain distinct from this immediate-safety failure. The proposed focused terrain-classification correction retains all landing hazard checks and excludes stairs from requested escape destinations. A reduced public-observation fixture and an independent fresh-memory terminal-observation probe reproduce the original failure and select one bounded escape input after correction; neither is a reconstruction of original runtime memory. The new regression fails on original source and passes on the candidate; the full suite passes 2,208 tests with four skipped. This establishes selector behavior, not actual gas escape, scroll collection or survival.

## Recommendations

- **000218-vertigo-terrain-outcomes — Correct vertigo random-outcome classification for depth exits and solid storage barrels.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 413, log lines 1215–1217: upgrade approach triggers hidden confusion gas at 819.; Decision 414, log lines 1218–1220: living hero exhausts immediate-safety planning with exit 784 and barrel 855 adjacent.; tools/vertigo_tactics.py:41–112; tools/priority_resources.py:229–255; tools/policy_tree.py:16,39.; Pinned game Char.move, Terrain flags and Hero action selection distinguish random landings, solid bumps and requested transitions.
  - Disposition: implemented

## Lessons for the next run

For vertigo, distinguish impassable bump directions from possible random landings using observed terrain semantics. Landing on stairs is not the same as requesting a stair interaction. Reobserve after each escape input; retain mandatory loot and require real movement and collection receipts.

Update: **accepted**.
