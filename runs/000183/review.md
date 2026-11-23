# ShatteredAI run 000183

Played commit: `108fa9c75a72fbc6c0ebbda361763314ae47f713`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot avoids retreating through a closed doorway when toxic gas is still remembered behind it. It can consider that doorway again after fresh observations confirm the gas has cleared.

## Incoming learnings

A clear closed doorway does not establish that the gas behind it has cleared. Check remembered neighboring gas before choosing a combat refuge, and require fresh clearance evidence before readmitting that entrance.

## Analysis

The run ended in planner exhaustion, not death: decision 1454 reports the hero alive at 40/40 HP. The initiating defect was conflicting potion-staging goals. Decisions 1225–1226 dropped other potion colors at 451; decision 1229 returned to the admitted dry test bank 562. Decision 1230 then preferred water 525, while decision 1231 sent the hero back to stash bank 562. Accepted transitions at log lines 3617, 3620 and 3623 confirm movement and advancing time, not a frozen game clock. Later staging loops and interruptions consumed the bounded preparation budget. In tools/descent_potions.py, bank selection ranked water again after tools/potion_stash.py had committed to returning to its original bank. Source-pinned offline reconstruction matched all recorded actions and reasons through decisions 0–1230. An isolated candidate probe on a copy of the validated state selected the existing unknown-potion test at bank 562 instead; no changed action was dispatched or followed with fabricated observations. The focused correction retains the stash bank and freshly rechecks bank and inventory protection. This establishes removal of the conflicting staging choice, not successful identification, retrieval, descent or survival. Potion identities remain unknown until publicly observed.

## Recommendations

- **000183-stash-bank-commitment — Keep pre-descent potion discovery at its committed stash bank, with fresh safety and collateral checks.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 1225–1226, log lines 3606–3609: other potion colors are dropped at 451.; Decisions 1229–1231, log lines 3616–3623: return to 562, preferred-water staging to 525, then return to 562.; Decisions 1316–1324, log lines 3868–3894: the staging contradiction repeats at another bank.; Decision 1454, log lines 4335–4337: preparation budget exhaustion with the hero alive.; Offline reconstruction matches decisions 0–1230; copied-state candidate probe selects testing at the committed bank.
  - Disposition: implemented

## Lessons for the next run

Keep potion storage and its test bank as one preparation transaction. A preference for water must not override the bank whose collateral footprint admitted storage. Revalidate current bank safety and potion protection before testing; retain mandatory pickup, honest receipts and explicit planner exhaustion.

Update: **accepted**.
