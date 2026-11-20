# ShatteredAI run 000024

Played commit: `af5840d7c12ec233390d6ff3662a645fa89738ed`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died while starving with the pool chest still unresolved

## Improvements since the last run

- The bot can now approach and open a guarded pool entrance before drinking identified invisibility when that doorway is the only starting point within the round-trip budget. It still waits for a fresh observation before spending the potion.

## Incoming learnings

Distinguish unknown-potion test banks from staging identified invisibility. A guarded entrance doorway may be the only origin within the protected round-trip budget. Open and reobserve before spending protection; require actual buffs and collection evidence. Choosing preparation is not puzzle completion.

## Analysis

The Mage died after prolonged unresolved pool-chest progression and starvation. The terminal accepted transition at decision 2359 (log line 6924) changes HP from 1 to 0 during a targeted staff zap; the nearby gnoll does not establish the killer. Potion identities revealed after death were not treated as prior knowledge.

A supported navigation defect preceded the later fallback symptoms: decisions 845–848 alternate between returning to the dry pool approach and leaving for ordinary loot, without remembering completed scouting. The source chain is rule preparation through prepare_supplies and revisit_pool, with pool observations maintained by piranha_tactics. A hypothetical protected trip does not admit an unknown-potion test. The correction records observed approach arrivals, including arrivals where preparation declines before reaching the revisit helper. It preserves test safety, real protection and collection verification, and mandatory progression pickup.

Offline bookkeeping reconstruction is not recorded runtime memory: original selected actions and reasons matched decisions 0–860. Candidate inputs matched through 854 and reconstruction stopped at the first differing input, decision 855. No subsequent observations were invented. The new regression fails by assertion on the original selector and passes all four tests on the candidate; the full suite passes 1,573 tests with four skipped. This establishes bounded scouting bookkeeping, not puzzle success or improved survival. The earlier hungry preparation gap and existing backlog remain unresolved.

## Recommendations

- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This recording does not establish a safe crab surprise alternative. The earlier case still needs recorded-input-validated doorway-attempt, pursuit and escape bookkeeping plus an admitted bounded surprise approach with a second exit under existing health and hazard checks.
  - Evidence: Run 000019: decisions 1708, 1718 and 1737, accepted log lines 4852, 4885 and 4938.; Run 000019: decisions 1774, 1805, 1863 and 1966, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish admitted preparation for mandatory progression loot instead of exhausting resources in fallback.** (high, deferred): The full helper chain is available and already delegates inaccessible pickups to guarded supplies. Here starvation blocks preparation before the frost preflight; a bandolier is present, so missing protection is not established as the blocker. A safe correction needs a contemporaneously known identification/extinguishing resource or a recorded-input-validated preparation alternative satisfying hunger, health, hazard, bank/protection and retrieval budgets. None is certified. Unknown potion identities revealed on death cannot supply that evidence, and neither relaxing test admission nor waiving mandatory pickup is justified.
  - Evidence: Run 000018: decisions 2826–2827 and 3903, retained backlog evidence.; Run 000020: decisions 3990, 3992, 4438 and 4553, retained backlog evidence.; Run 000022: decision 2683, log line 7634, starvation precedes fire-room discovery.; Run 000022: decision 2756, log line 7847, unreachable upgrade and food with HP 53/55.; Run 000022: decisions 2909–2910, log lines 8278–8283, mandatory veto, healing and fallback wait.; Run 000022: decision 3632, accepted log line 10666, explicit starvation death.
  - Disposition: deferred
- **000024-pool-approach-receipt — Remember observed pool-approach arrivals instead of restarting completed scouting detours.** (medium, rejected): Candidate validation failed; code was not promoted.
  - Evidence: Decisions 845–848, selection log lines 2413, 2416, 2419 and 2422.; Decisions 851 and 855, selection log lines 2431 and 2445.; Original-source offline selections matched decisions 0–860; candidate inputs first differ at decision 855.
  - Disposition: rejected

## Lessons for the next run

Treat arrival at a pool approach as completed scouting, not completed loot. Retain that receipt when preparation is interrupted or declines, while rechecking actual potion-test admission separately. Unknown potion identities and hypothetical protection cannot justify entering the pool.

Update: **rejected**.
