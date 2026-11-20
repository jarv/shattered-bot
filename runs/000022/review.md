# ShatteredAI run 000022

Played commit: `c74169b5c7a70bb5bb1ca010acd900330731e14d`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved to death after an unresolved fire-room upgrade pickup

## Improvements since the last run

- Before walking toward an unknown frost-potion test, the bot now checks whether it can protect its other potions. It declines an infeasible new approach while preserving recovery for an already-started stash.

## Incoming learnings

Check potion-protection feasibility before walking toward an unknown frost test. An infeasible unstarted approach should not consume floor-wide preparation availability. Continue to require real stash, effect and collection evidence; selecting another action does not establish retrieval or survival.

## Analysis

The accepted final transition confirms starvation death, not a skeleton kill: decision 3632, log line 10666, explicitly reports hunger death after HP falls from 1 to 0. The initiating impasse began earlier. Floor-seven starvation appears at decision 2683, line 7634, before the first observed magical fire. At decision 2756, line 7847, the bot sees an upgrade scroll at 1005 and food at 974 beyond the fire buffer, with HP 53/55 but no carried food. Source browsing resolves the selecting chain: priority_resources.py:118–136 already delegates inaccessible pickups to puzzle preparation before mapping. However, puzzle_supplies.py:390–392 declines while starving, before frost staging or identification. The recorded frost-preflight change therefore is not the demonstrated blocker. Decision 2909, lines 8278–8281, retains the mandatory pickup veto and spends healing; decision 2910, line 8283, waits at full HP while still starving. From decision 2909 to death the clock advances from 2856 to 3550, including 444 last-resort waits. No pre-death observation identifies a carried frost potion; its later revelation cannot justify earlier use. No patch or new regression is supplied because no safe replacement preparation is established: removing the starvation gate would relax unknown-test admission, and waiving the upgrade obligation would violate intended progression. A known identification/extinguishing resource or a validated, budgeted preparation alternative is needed. No policy-memory reconstruction or counterfactual gameplay was performed. The unchanged full suite passed 1,565 tests with four skipped; this does not establish a recovery solution.

## Recommendations

- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This recording does not establish a safe crab surprise alternative. The earlier case still needs recorded-input-validated doorway-attempt, pursuit and escape bookkeeping plus an admitted bounded surprise approach with a second exit under existing health and hazard checks.
  - Evidence: Run 000019: decisions 1708, 1718 and 1737, accepted log lines 4852, 4885 and 4938.; Run 000019: decisions 1774, 1805, 1863 and 1966, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish admitted preparation for mandatory progression loot instead of exhausting resources in fallback.** (high, deferred): The full helper chain is available and already delegates inaccessible pickups to guarded supplies. Here starvation blocks preparation before the frost preflight; a bandolier is present, so missing protection is not established as the blocker. A safe correction needs a contemporaneously known identification/extinguishing resource or a recorded-input-validated preparation alternative satisfying hunger, health, hazard, bank/protection and retrieval budgets. None is certified. Unknown potion identities revealed on death cannot supply that evidence, and neither relaxing test admission nor waiving mandatory pickup is justified.
  - Evidence: Run 000018: decisions 2826–2827 and 3903, retained backlog evidence.; Run 000020: decisions 3990, 3992, 4438 and 4553, retained backlog evidence.; Run 000022: decision 2683, log line 7634, starvation precedes fire-room discovery.; Run 000022: decision 2756, log line 7847, unreachable upgrade and food with HP 53/55.; Run 000022: decisions 2909–2910, log lines 8278–8283, mandatory veto, healing and fallback wait.; Run 000022: decision 3632, accepted log line 10666, explicit starvation death.
  - Disposition: deferred
- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): This recording does not establish a safe pool preparation alternative. The earlier case still needs recorded-input-validated dry test-bank and remote potion-protection admission plus a budgeted protected chest trip, or observed non-drinking identification.
  - Evidence: Run 000013: decisions 3014–3016 and 4063, retained backlog evidence.
  - Disposition: deferred

## Lessons for the next run

Distinguish inaccessible mandatory loot from completed loot. Healing to full health does not restore potion-test eligibility while starving. Check the actual preparation gate before blaming potion protection or extending fallback waits. Preserve public identification, hazard checks and mandatory progression; selecting preparation alone would not prove extinguishing or retrieval.

Update: **review-only**.
