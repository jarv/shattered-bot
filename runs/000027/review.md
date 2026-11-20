# ShatteredAI run 000027

Played commit: `0bd10f7f3663e52797d14f7051479950e52e2e39`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died during the Goo fight

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Before funding pool preparation with food, establish a public, admissible identification or unknown-potion test plan, including inventory protection and a budgeted chest return trip. A meal is not proof that testing or retrieval becomes possible. Keep the chest pending until collection is verified.

## Analysis

The Mage died during the Goo fight. The initiating problem was an unfavorable engagement on healing water, before the withdrawal-budget failures: decisions 1460–1464 traded melee blows while four staff charges remained, and decisions 1469–1470 reduced hero health from 27 to 12. The full selector chain explains this: Goo first seeks an admitted immediate dry lure, then chooses the highest estimated attack; the inspected staff scores slightly higher in melee while the hero is healthy. Public bar increases corroborate water healing. Decision 1481 begins exhausted-magic withdrawal; later fallback retreats do not demonstrate a stopped clock or a safe alternative. Accepted terminal transitions at lines 4356 and 4360 show health falling from four to one to zero. The final damage source is not established. No policy memory was reconstructed and no counterfactual gameplay was executed. Source browsing resolved the selection-chain gap but did not establish a focused deterministic defect or an admitted replacement, so no patch or new regression is supplied. Existing tests pass: 1,569 tests, four skipped. Post-death potion identities were not treated as pre-death knowledge.

## Recommendations

- **000026-pool-preparation-feasibility — Resolve pool preparation feasibility before adding food spending or additional staging movement.** (medium, deferred): No safe focused replacement is established. The public geometry admits protected chest trips from some approaches, but not an unknown-drink bank satisfying the existing dry-surroundings gates; no carried known invisibility or safe identification supply is recorded at the block. A repair needs evidence of an admissible identification/test-and-inventory-protection route, or additional public observations establishing one. Merely adding a pool meal would not resolve the recorded post-meal failure, and speculative movement or weakened hazard checks is not justified.
  - Evidence: Decision 806, log line 2413: observed chest and piranhas.; Decision 1000, log line 2957: pool supplies declined while hungry.; Decision 1044, log lines 3087–3089: mandatory chest blocks descent; fallback waits begin.; Decisions 1076–1078, log lines 3183–3189: eating and healing do not restore progress.
  - Disposition: deferred
- **000025-scroll-discovery-readiness — Establish evidence-backed preparation criteria for unknown-scroll discovery that can cause displacement.** (high, deferred): The complete selecting source explains the risky read, but no validated preparation or replacement action is established. A minimum charge threshold would be arbitrary, and neither full charges nor a quiet origin guarantees a safe teleport destination. A focused repair needs bounded readiness criteria plus public-input-validated preparation or recovery alternatives that preserve discovery and mandatory progression; hidden potion identities cannot supply that evidence.
  - Evidence: Decision 833, selection line 2357 and accepted transition line 2358.; Decisions 834–836, lines 2359–2364.; Decisions 839–841, lines 2375–2386.; Decision 879, accepted transition line 2547.
  - Disposition: deferred
- **000024-pool-approach-receipt — Remember observed pool-approach arrivals instead of restarting completed scouting detours.** (medium, deferred): This encounter does not establish a corrected pool receipt lifecycle. The earlier rejected proposal still needs a regression demonstrating retained scouting evidence across interrupted preparation without crediting collection or bypassing potion-test admission. No such runtime reconstruction or replacement validation was performed here.
  - Evidence: Run 000024: decisions 845–848, selection lines 2413, 2416, 2419 and 2422.; Run 000024: decisions 851 and 855, selection lines 2431 and 2445.; Incoming backlog records that candidate validation failed and code was not promoted.
  - Disposition: deferred
- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This recording establishes no safe crab surprise alternative. The earlier case still needs public-input-validated doorway-attempt, pursuit and escape bookkeeping and a bounded surprise approach with a second exit under existing health and hazard checks. Current source browsing does not certify that replacement.
  - Evidence: Run 000019: decisions 1708, 1718 and 1737, accepted lines 4852, 4885 and 4938.; Run 000019: decisions 1774, 1805, 1863 and 1966, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish admitted preparation for mandatory progression loot instead of exhausting resources in fallback.** (high, deferred): The current fatal encounter supplies no validated mandatory-loot preparation alternative. The earlier case still requires a contemporaneously known identification or extinguishing resource, or validated preparation satisfying hunger, health, hazard, protection and retrieval budgets. Unknown potion identities and waived mandatory pickup cannot justify a repair.
  - Evidence: Run 000018: decisions 2826–2827 and 3903, retained backlog evidence.; Run 000020: decisions 3990, 3992, 4438 and 4553, retained backlog evidence.; Run 000022: decisions 2683, 2756, 2909–2910 and 3632, retained backlog evidence.
  - Disposition: deferred
- **000027-goo-water-engagement — Establish an admitted dry-engagement or charge-preservation alternative before changing Goo combat priorities.** (medium, deferred): Complete source explains the selection but establishes no discrete implementation defect or validated safe replacement. At decision 1460 the observed adjacent dry steps do not provide the separating landing required by the existing lure rule. A repair needs an admitted multi-turn dry-engagement route or a public-input-validated attack/resource alternative preserving warning escape and health/hunger budgets. Arbitrarily preferring magic, extending preparation, or guessing potion identities is not sufficient evidence.
  - Evidence: Decision 1453, selection line 4015: wakes Goo on water with full health and six staff charges.; Decisions 1460–1464, lines 4029–4046: melee trades on water consume health while four charges remain.; Decisions 1469–1470, lines 4055–4062: health falls from 27 to 12 during further melee trades.; Decision 1481, line 4087: exhausted-magic withdrawal starts; decision 1493, line 4136: fallback retreat follows.
  - Disposition: deferred

## Lessons for the next run

Investigate the water engagement before extending withdrawal or preparation limits. Establish a publicly supported dry approach or attack/resource plan that preserves charge-warning escape and health/hunger budgets. Do not infer a safe potion from its later revealed identity, and keep mandatory progression loot pending until collection is verified.

Update: **review-only**.
