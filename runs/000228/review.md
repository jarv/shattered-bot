# ShatteredAI run 000228

Played commit: `81c4a4b4533cf236e90901912d20da2cbc0325d2`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now distinguishes an exposed skeleton key from skeletal remains when the visible item confirms it, while keeping the usual terrain and container safety checks.

## Incoming learnings

Distinguish a publicly exposed skeleton key item from skeletal remains, and verify actual collection afterward. Keep the separate sentry preparation obligation: a complete room can still lack an admitted testing bank. Do not infer haste, cross defended carpet, waive mandatory pickup or replace planner exhaustion with waiting.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. At decisions 281–283 (log lines 763–767), identified frost extinguished the fire, but cold remained across the approach to an observed upgrade scroll. The mandatory-pickup controller then selected mapping and exploration left for another room. Source inspection shows that mandatory targets bypassed the existing post-barrier return controller; that controller also lacked a safe observation hold when fresh cold blocked its entrance. Decisions 301 and 303 explicitly rejected the upgrade route at remembered cold cells, and the accepted blink did not collect it or produce a descent. The proposed focused repair delegates the existing return transaction from mandatory pickup and admits only bounded observation from freshly verified safe ground. A new regression fails on original source with mapping selected instead, passes on the candidate, and the full suite passes 2235 tests with four skips. This does not establish actual collection, puzzle completion, or improved survival.

## Recommendations

- **000228-frost-return-arbitration — Keep mandatory post-fire retrieval active through safe observation of temporary frost.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 281, log line 763: known frost selected for mandatory-resource preparation.; Decisions 282–283, log lines 765–767: fire extinguished, approach cold, mapping selected.; Decision 284, log line 770: exploration leaves the still-cold entrance.; Decisions 301 and 303, log lines 821 and 827–830: upgrade route excluded and planner exhaustion recorded.
  - Disposition: implemented

## Lessons for the next run

Extinguishing a barrier is not the same as opening a currently safe route. Keep the required return transaction active while freshly observed frost blocks the approach, reobserve only from safe ground, and require actual hazard clearance and pickup evidence before crediting progress. Do not reinterpret stale cold as safe or abandon mandatory upgrade collection.

Update: **accepted**.
