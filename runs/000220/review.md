# ShatteredAI run 000220

Played commit: `cc7c77bc49a3776d65ba443ad096afc2870bdf7c`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now aims to recover closer to full health when an unfinished upgrade or strength reward requires testing a potion beside magical fire. Its existing limits on waiting, hunger and exposure still apply.

## Incoming learnings

Budget health for required potion preparation before exploring away from an unfinished upgrade room. Recovery should recognize the existing test threshold without extending waits or lowering safety requirements. Keep unknown potion identities unknown and require actual extinguishing and pickup receipts.

## Analysis

The recording ends in planner exhaustion, not death: the hero is alive at full health. Decision 671 enters a previously unexplored gas-room doorway; decision 672 escapes without observed HP loss (accepted log lines 1920 and 1923). At decision 673, mandatory strength discovery reserves a missing purity supply for that unfinished room, but every preparation alternative is excluded (lines 1925–1926). Source-pinned offline reconstruction matched all 673 earlier selected actions and reasons and reproduced the terminal failure. Hunger blocks gas testing, but it is not the only cause: an isolated hunger-free copy still selects no preparation. The only admitted visible test bank, 1186, lacks an admitted remote stash for the other unidentified potions; nearby storage-capable banks fail test-bank checks. The inventory has neither an identify scroll nor an intuition stone. No patch is supplied because no existing helper certifies the complete safe bank, storage and return transaction; adding gas meals alone would leave that contradiction unresolved. The unchanged full suite passed 2,212 tests with four skips. No new regression or candidate red/green comparison was produced. Hypothetical protected routes do not establish protection, potion identity or collection.

## Recommendations

- **000220-gas-bank-stash-handoff — Establish jointly executable gas-test staging and remote potion storage before mandatory discovery exhausts.** (high, deferred): Complete source and offline reconstruction resolved the selecting-state uncertainty, but no helper jointly certifies test-bank safety and remote protection of the actual three-color inventory. The only admitted bank has no storage candidate in the required distance interval of its door-excluding transit corridor. A gas meal alone still leaves preparation blocked; relaxing geometry, collateral checks or unknown-drink safety is unsupported. Next build a paired public-observation fixture from decisions 672/673 and prove departure-aware storage across a known ordinary door, including fresh arrival, bounded return and collection receipts. Only then add the executable gas-preparation handoff with an original-red/candidate-green regression. Preserve terminal exhaustion and mandatory pickup.
  - Evidence: Decision 671, log lines 1919–1920: exploration enters doorway 1150.; Decision 672, log lines 1922–1923: gas is observed and the full-health hero retreats to 1187.; Decision 673, log lines 1925–1926: missing purity reservation exhausts mandatory discovery without an accepted preparation action.; tools/descent_potions.py:350–392; tools/puzzle_supplies.py:743–806,968–1012; tools/potion_stash.py:95–133.; Validated offline reconstruction matches decisions 0–672; isolated terminal probes find bank 1186 safe but without admitted storage, even without hunger.
  - Disposition: deferred

## Lessons for the next run

Treat gas preparation as a complete prerequisite transaction, not merely a hunger problem. Before funding a puzzle meal, jointly establish a safe test bank, protection of every other unidentified potion, a protection-funded reward return and fresh arrival checks. Keep unknown colors unknown and preserve mandatory progression pickup and explicit planner exhaustion.

Update: **review-only**.
