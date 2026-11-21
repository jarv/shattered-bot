# ShatteredAI run 000045

Played commit: `56cff0cdb8441ccdcf33dd34d4ee6112a8b9f506`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Mandatory pool retrieval needs an executable preparation route. Check hunger admission, safe unknown-drink geometry, inventory protection, entrance readiness and the protected return budget together. A floor-supply expectation does not identify any potion. Preserve the chest obligation and terminal planner-failure label. Other backlog cases were not re-investigated here.

## Analysis

The hero stopped alive at full health because the planner exhausted recovery, not because the game clock froze. A completed pool-approach scout repeatedly preempted key collection: decision 470 reached cell 637, decision 471 resumed key work, and decision 472 restarted the same scout. Subsequent route-stall and loop exclusions accumulated before planner failure at decision 610. Offline source-pinned reconstruction matched original actions and reasons through decision 476. The proposed arrival-receipt correction matches through 471, then selects the existing key-progress step at 472; reconstruction stops there. The new regression fails by the expected assertion on original policy and passes on the candidate. The full suite passes. This establishes removal of a stale scouting detour, not successful key collection, pool preparation or survival. Potion identities, hazard admission, mandatory pickups and the terminal failure label remain unchanged.

## Recommendations

- **000024-pool-approach-receipt — Remember completed pool-approach scouting so it does not repeatedly interrupt key collection.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 470, lines 1388–1389: approach selection and accepted arrival at 637.; Decisions 471–472, lines 1391–1394: key work leaves the bank, then preparation immediately restarts the completed detour.; Decision 477, line 1409: interrupted key target exceeds bounded route progress; decision 482, line 1426: pool detour triggers the navigation-loop guard.; Decision 610, line 1832: hungry recovery exhaustion terminates the living hero's planner.; tools/puzzle_supplies.py:189–213,365–382; tools/test_shattered_pool_approach_receipt.py.
  - Disposition: implemented

## Lessons for the next run

Remember an actually observed scouting arrival separately from protection or collection. Returning to other floor work must not restart that completed detour. Pool supply feasibility remains a separate problem: validate an admitted entrance scout, return and inventory protection before any unknown drink. Other backlog cases were not re-investigated.

Update: **accepted**.
