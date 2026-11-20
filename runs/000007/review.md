# ShatteredAI run 000007

Played commit: `32bc2515322697a9dab89125578625739f675040`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died after repeated retreat setups under poison and burning pressure

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

No new gameplay lesson is claimed by this operator disposition. Investigate the failed automated review separately. Continue with the unchanged bot policy and a separately configured audio-recording trial.

## Analysis

The Mage died after a deteriorating retreat under poison and burning pressure; the exact killing source is not established. A focused initiating defect occurs at decision 825: after door 739 lacked an observed holding square, the multi-threat controller began another unverified door setup even though its recorded pursuit report marked new doorway setups exhausted (four retreats, 11 cumulative HP lost). Decision 825, log line 2332, moved toward door 737; accepted transition 2333 records HP 19 to 12. Decision 827 continued that setup, followed by observed burning. The shared pursuit budget already blocks ordinary doorway lures, but tools/multi_enemy_tactics.py bypassed it. The correction blocks only new unverified setups after exhaustion, preserving revalidated commitments and ordinary retreat checks. Offline baseline bookkeeping matched all 840 recorded selections; candidate bookkeeping matched through 824 and stopped at its first divergence, 825. Its alternative is not certified safe. Terminal transitions 2376 and 2380 record HP 5 to 1 to 0 during committed cover movement. Unknown potion effects and post-death revelations were not used. The new regression fails by assertion on original policy and passes on the candidate; the full suite passes 1,423 tests with four skips. This establishes budget consistency, not survival or quest success. Files is empty as required for adapter-derived changes.

## Recommendations

- **000007-doorway-staging-budget — Make new multi-threat doorway staging honor the existing exhausted-pursuit budget.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 824, log lines 2326-2327; Decision 825, log lines 2331-2333; Decision 827, log line 2340 and accepted transition
  - Disposition: implemented

## Lessons for the next run

Honor exhausted pursuit budgets across every controller that starts an unverified doorway setup. Reaching a door without an observed holding square is not successful cover. Preserve honest unfinished-loot accounting and do not treat an offline alternative as proven safe.

Update: **accepted**.
