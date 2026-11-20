# ShatteredAI run 000028

Played commit: `38866c9ac2053bb942e730b1e7f9fba34e48c6fc`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died with a required upgrade still behind the fire barrier

## Improvements since the last run

- The bot now treats invisibility used to escape Goo's charged attack as emergency use of a potion that might also be needed for a special room.

## Incoming learnings

Investigate the water engagement before extending withdrawal or preparation limits. Establish a publicly supported dry approach or attack/resource plan that preserves charge-warning escape and health/hunger budgets. Do not infer a safe potion from its later revealed identity, and keep mandatory progression loot pending until collection is verified.

## Analysis

The initiating defect was preparation arbitration, not simply excessive waiting. Decisions 1203–1204 staged an unknown-potion test beside magical fire and began moving to a remote potion stash. At decision 1205 (log line 3548), required-loot priority sent the Mage back to the test square instead of advancing that stash. Decision 1206 then reported an incomplete stash (line 3551); recovery disabled further potion-supply preparation. By decision 1403 (lines 4093–4095), the observed upgrade remained unreachable behind fire, and fallback play began. The final accepted transition at decision 2946 (line 8664) reduced HP from 6 to 0 during a targeted zap; this alone does not identify the killer. A selector-only reconstruction of the short preparation episode matched the played actions and reasons at decisions 1203–1205. With the correction, the first difference is decision 1205: the existing stash controller advances instead of restarting staging. This reconstruction is not recorded runtime memory. The new deterministic regression fails on the played policy and passes on the candidate; the full suite passes 1,589 tests with four skips. The correction preserves hazard checks, unknown potion identities, drop receipts, and mandatory upgrade collection. It establishes continued preparation, not successful potion testing, fire removal, reward collection, or survival.

## Recommendations

- **000028-progression-stash-resume — Resume an active potion stash before required-loot priority restarts room staging.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1203, log line 3542: fire-test approach.; Decision 1204, log line 3545: remote stash approach.; Decision 1205, log line 3548: priority returns to the test bank while the stash remains active.; Decision 1206, log lines 3551–3553: incomplete-stash failure disables preparation.; Decision 1403, log lines 4093–4095: required upgrade blocks descent and fallback begins.
  - Disposition: implemented

## Lessons for the next run

When required loot depends on potion preparation already in progress, let the existing stash workflow advance before selecting another test approach. Keep potion identities unknown until publicly established, verify every drop and pickup, and retain the upgrade obligation until collection is observed.

Update: **accepted**.
