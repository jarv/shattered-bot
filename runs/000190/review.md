# ShatteredAI run 000190

Played commit: `cffdbcc2fee632406b5cfe7a230cfc6ceb95f732`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Keep failed unidentified-potion scouting separate from the bounded return enabled by a newly acquired identified extinguisher. Search for a safe route before rejecting a destination because its ordinary shortest route crosses a hazard. Preserve mandatory key pickup and the terminal stuck-planner label.

## Analysis

The hero stopped alive after a planner failure, not an observed death. Decisions 2483–2488 show the initiating contradiction: seeing sleeping flies beside a ration selected shopping away, while losing sight of them restarted the cached food approach. Accepted transitions at log lines 7343 and 7346 confirm the reversal. Navigation recovery subsequently exhausted; the final healing action raised HP to full without resolving progress. The known downstairs had no route admitted by the recovery checks. Source inspection identified separate remembered-sleeper bookkeeping that the food selector ignored. A focused correction now withholds optional food priority beside a remembered sleeper without removing the loot obligation or weakening mandatory pickups or hazards. A reduced public-evidence fixture fails on original source and passes on the candidate; the full suite passes 2,098 tests with four skips. This is not recovered runtime memory or proof of subsequent purchase, descent or survival.

## Recommendations

- **000190-guarded-food-visibility — Prevent remembered sleeping guards from triggering food-versus-shopping reversals when visibility changes.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 2483–2485, log lines 7336–7340: visible sleeping flies veto food priority and shopping moves away.; Decisions 2486–2488, log lines 7342–7347: hidden food approach reverses visible-enemy shopping; accepted lines 7343 and 7346 confirm movement.; Decision 2496, log line 7367: navigation-loop recovery begins.; Decision 2575, log lines 7583–7585: planner exhaustion with the hero alive.
  - Disposition: implemented

## Lessons for the next run

Losing sight of a known sleeping enemy must not restart optional food collection that reverses existing shopping. Keep unfinished loot honest, preserve mandatory progression pickups, and clear remembered guards only through fresh public evidence.

Update: **accepted**.
