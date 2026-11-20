# ShatteredAI run 000023

Played commit: `8faa5e26c98b34ed0d393ae9903dfa61a2de6a90`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved while mandatory piranha chest remained uncollected

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish inaccessible mandatory loot from completed loot. Healing to full health does not restore potion-test eligibility while starving. Check the actual preparation gate before blaming potion protection or extending fallback waits. Preserve public identification, hazard checks and mandatory progression; selecting preparation alone would not prove extinguishing or retrieval.

## Analysis

The run died from hunger: decision 2358, accepted log line 6921, explicitly reports starvation death. The initiating pool blockage preceded starvation. Invisibility was publicly identified at decision 553 (accepted line 1589), yet full-health fallback resumed at decision 564 (line 1616). Original-source offline reconstruction matched selections through 564. The only budgeted protected chest route started at closed entrance 1287; puzzle_supplies.stage_known_pool excluded doorway origins even for identified invisibility. The focused candidate permits guarded ordinary doorway staging, without changing unknown-potion tests, hazard exclusions, protection budgets or mandatory collection. Its first changed selection is decision 557, an observed approach step; reconstruction stops there. The new regression fails on original source and passes on the candidate; the full suite passes 1,569 tests with four skips. This does not establish successful opening, protection, chest retrieval or survival. The other backlog cases remain unresolved; their stated missing evidence is unchanged.

## Recommendations

- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This recording does not establish a safe crab surprise alternative. The earlier case still needs recorded-input-validated doorway-attempt, pursuit and escape bookkeeping plus an admitted bounded surprise approach with a second exit under existing health and hazard checks.
  - Evidence: Run 000019: decisions 1708, 1718 and 1737, accepted log lines 4852, 4885 and 4938.; Run 000019: decisions 1774, 1805, 1863 and 1966, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish admitted preparation for mandatory progression loot instead of exhausting resources in fallback.** (high, deferred): The full helper chain is available and already delegates inaccessible pickups to guarded supplies. Here starvation blocks preparation before the frost preflight; a bandolier is present, so missing protection is not established as the blocker. A safe correction needs a contemporaneously known identification/extinguishing resource or a recorded-input-validated preparation alternative satisfying hunger, health, hazard, bank/protection and retrieval budgets. None is certified. Unknown potion identities revealed on death cannot supply that evidence, and neither relaxing test admission nor waiving mandatory pickup is justified.
  - Evidence: Run 000018: decisions 2826–2827 and 3903, retained backlog evidence.; Run 000020: decisions 3990, 3992, 4438 and 4553, retained backlog evidence.; Run 000022: decision 2683, log line 7634, starvation precedes fire-room discovery.; Run 000022: decision 2756, log line 7847, unreachable upgrade and food with HP 53/55.; Run 000022: decisions 2909–2910, log lines 8278–8283, mandatory veto, healing and fallback wait.; Run 000022: decision 3632, accepted log line 10666, explicit starvation death.
  - Disposition: deferred
- **000013-pool-preparation-admission — Admit bounded ordinary doorway staging for identified pool invisibility.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Run 000013: decisions 3014–3016 and 4063, retained backlog evidence.; Run 000023: decision 553, accepted log line 1589, public identification.; Run 000023: decisions 557 and 564, log lines 1596 and 1616; original-source reconstruction validated through 564.; Run 000023: candidate first diverges at decision 557 and reconstruction stops.
  - Disposition: implemented

## Lessons for the next run

Distinguish unknown-potion test banks from staging identified invisibility. A guarded entrance doorway may be the only origin within the protected round-trip budget. Open and reobserve before spending protection; require actual buffs and collection evidence. Choosing preparation is not puzzle completion.

Update: **accepted**.
