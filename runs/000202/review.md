# ShatteredAI run 000202

Played commit: `d53be7ad92bd04398c4df425a6fd43b233a841af`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a prison guard after a slowed doorway retreat

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Investigate preparation feasibility when the gas room is first observed, before blaming later hunger. A hypothetical protected chest route does not establish a safe unknown-potion bank. Keep unknown colors unknown, preserve mandatory pickup and inventory protection, and retain explicit planner exhaustion rather than waiting or bypassing the obligation.

## Analysis

The complete public death receipt identifies a prison guard as the killer, although the compact packet omitted that message. The initiating retreat defect appears earlier: decision 3713 selected closed doorway 840 while the hero wore publicly identified bulk armor and the guard could see that doorway. Its accepted transition advanced about 2.27 turns, recorded a chain pull, and reduced HP from 17 to 2. Decision 3717 then selected another doorway transit and died. The cover selector checked destination concealment and target melee reach but omitted the known doorway slowdown. A focused correction rejects exposed doorway cover routes against pull-capable enemies while wearing known bulk armor, for both new and committed routes. A public-terrain fixture reproduces the unsafe admission on original source and selects the already-admitted ordinary-ground alternative after correction. The final regression has four expected baseline assertion failures and passes all five tests after correction; the full suite passes 2,159 tests with four skips. The fixture's optional plan is synthetic, not recovered original memory. This does not establish survival, future enemy movement, or loot completion. No recorded-code improvements are attributed because the supplied source comparison is empty.

## Recommendations

- **000202-bulk-guard-cover — Reject exposed bulk-slowed doorway transit when selecting or continuing cover against a pull-capable enemy.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3713, selection line 10763: equipped bulk armor, guard at 807, and movement from 805 toward closed door 840.; Decision 3713, accepted transition line 10764: prolonged movement, explicit guard pull, displacement to 806, and HP 17 to 2.; Decision 3717, selection line 10776 and accepted transition line 10777: another doorway transit ends in explicit prison-guard death.; tools/ranged_tactics.py:123-146: transit admission and focused bulk-door correction.; tools/test_shattered_bulk_guard_cover.py: original-source assertion failures and candidate passing regressions.
  - Disposition: implemented

## Lessons for the next run

Treat known bulk armor as a doorway-specific retreat constraint. A hidden destination does not make exposed transit safe against a guard's pull. Recheck committed routes without assuming chains are spent, and retain all ordinary hazard and mandatory-pickup checks.

Update: **accepted**.
