# ShatteredAI run 000199

Played commit: `0d05e4ae6ced5cd29fcd75508fc47aa6e113501a`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish complete sentry geometry from executable potion preparation. A hypothetical protected chest route does not make flammable entry flooring a safe unknown-potion bank. Preserve unidentified colors, inventory protection and mandatory pickup until a preparation transaction is actually admitted.

## Analysis

The hero remained alive at full health when mandatory preparation exhausted. Decision 262 (selection 740, accepted transition 741) entered the sentry doorway; decision 263 (743–745) stopped without recovery or descent. Earlier mapping at decision 108 (304–306) exposed terrain without surveying it. The sentry geometry helper treated mapped but unobserved interior and perimeter cells as a complete enclosure, suppressing the existing safe observation prerequisite while no protected reward trip was established. Offline bookkeeping reconstruction matches all 263 earlier selections and reproduces the original blocker. The focused correction requires observed enclosure geometry; the same terminal input then selects ordinary-floor reconnaissance, not drinking or descent. The new regression fails by assertion on original source and passes on the candidate; the full suite passes 2,154 tests with four skips. This establishes an admitted observation step, not chest discovery, potion safety, collection or survival.

## Recommendations

- **000199-mapped-sentry-survey — Do not let mapped but unobserved sentry geometry suppress safe reconnaissance.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 108, selection 304 and accepted transition 305; mapping confirmation 306.; Decision 262, selection 740 and accepted transition 741: arrival at the sentry doorway.; Decision 263, records 743–745: missing haste exhausts mandatory discovery with the hero alive.; Source-pinned offline reconstruction matches selections 0–262; original geometry suppresses reconnaissance despite unobserved interior 1313 and perimeter gaps.; tools/room_tactics.py:179–221; tools/preparation_prerequisites.py:83–144; tools/descent_potions.py:348–387.
  - Disposition: implemented

## Lessons for the next run

Mapped terrain is not a completed sentry survey. Reobserve missing enclosure cells from admitted ordinary ground before exhausting preparation. Keep unknown potion identities, inventory protection, fresh arrival checks and mandatory progression pickup intact; choosing reconnaissance does not prove retrieval.

Update: **accepted**.
