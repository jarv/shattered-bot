# ShatteredAI run 000031

Played commit: `7828de022fb468ca8a6652213efb91bb69b801ce`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved after entrance-shop scouting stalled

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish exhausted ordinary frontiers from a verified completed floor. Investigate resource-funded missing-exit search admission when hunger reduces a cumulative search ceiling. Validate the actual safe route and work budget before changing admission; further searching is not proof of finding the exit. Preserve mandatory progression pickups, hazard exclusions and honest potion-effect receipts.

## Analysis

The Mage defeated Goo, then starved after entrance-shop scouting stalled. At decision 2240 (selection line 6539), the shop controller chose a door branch while observed, reachable entrance frontiers remained. Subsequent branch exploration consumed the visit budget; decision 2373 (lines 6846–6848) begins fallback waiting after the shop-search veto. Decision 2812 (lines 8131–8132) records the final wait from 1 HP to zero, with an explicit starvation message. This is advancing-time failure, not an execution deadlock. The initiating ordering defect is in tools/shop_tactics.py: entrance doors are considered before unfinished entrance frontiers. The proposed correction reverses that ordering only for existing admitted paths wholly inside the observed entrance-side component. It does not claim the shop was found, credit unfinished loot, raise budgets, or identify unknown potions. A condensed public-geometry regression fails on the original policy and passes on the candidate; all 1596 Python tests pass, with four skipped. Full historical policy memory at decision 2240 was not recovered; a separate public-map fixture admits the alternative without claiming recorded runtime memory or a successful counterfactual run.

## Recommendations

- **000030-missing-exit-search-admission — Establish an admitted missing-exit search alternative at the eight-search hunger transition.** (high, deferred): Source establishes the cumulative search-ceiling gate, not a safe replacement. The concrete blocker is validating a remaining target with its safe approach/return, current threat bookkeeping, hunger cost, and bounded search receipts. The incomplete observed map does not prove where progression lies; the known trap-blocked connection also lacks a validated protected traversal. A larger search or waiting bound, speculative movement, or guessed potion effect would not supply that evidence. No policy or test changes are proposed.
  - Evidence: Decision 4547, line 12920: ordinary region tasks are exhausted and wall searching begins.; Decision 4645, lines 13203-13204: the eighth search leaves health full but changes hunger phase.; Decision 4646, lines 13205-13206: no reachable exit is reported and fallback waits begin.; Decision 5799, lines 16655-16656: a starving hero falls from 1 HP to zero while waiting.
  - Disposition: deferred
- **000027-goo-water-engagement — Establish an admitted dry-engagement or charge-preservation alternative before changing Goo combat priorities.** (medium, deferred): Complete source explains the selection but establishes no discrete implementation defect or validated safe replacement. At decision 1460 the observed adjacent dry steps do not provide the separating landing required by the existing lure rule. A repair needs an admitted multi-turn dry-engagement route or a public-input-validated attack/resource alternative preserving warning escape and health/hunger budgets. Arbitrarily preferring magic, extending preparation, or guessing potion identities is not sufficient evidence.
  - Evidence: Decision 1453, selection line 4015: wakes Goo on water with full health and six staff charges.; Decisions 1460–1464, lines 4029–4046: melee trades on water consume health while four charges remain.; Decisions 1469–1470, lines 4055–4062: health falls from 27 to 12 during further melee trades.; Decision 1481, line 4087: exhausted-magic withdrawal starts; decision 1493, line 4136: fallback retreat follows.
  - Disposition: deferred
- **000026-pool-preparation-feasibility — Resolve pool preparation feasibility before adding food spending or additional staging movement.** (medium, deferred): No safe focused replacement is established. The public geometry admits protected chest trips from some approaches, but not an unknown-drink bank satisfying the existing dry-surroundings gates; no carried known invisibility or safe identification supply is recorded at the block. A repair needs evidence of an admissible identification/test-and-inventory-protection route, or additional public observations establishing one. Merely adding a pool meal would not resolve the recorded post-meal failure, and speculative movement or weakened hazard checks is not justified.
  - Evidence: Decision 806, log line 2413: observed chest and piranhas.; Decision 1000, log line 2957: pool supplies declined while hungry.; Decision 1044, log lines 3087–3089: mandatory chest blocks descent; fallback waits begin.; Decisions 1076–1078, log lines 3183–3189: eating and healing do not restore progress.
  - Disposition: deferred
- **000025-scroll-discovery-readiness — Establish evidence-backed preparation criteria for unknown-scroll discovery that can cause displacement.** (high, deferred): The complete selecting source explains the risky read, but no validated preparation or replacement action is established. A minimum charge threshold would be arbitrary, and neither full charges nor a quiet origin guarantees a safe teleport destination. A focused repair needs bounded readiness criteria plus public-input-validated preparation or recovery alternatives that preserve discovery and mandatory progression; hidden potion identities cannot supply that evidence.
  - Evidence: Decision 833, selection line 2357 and accepted transition line 2358.; Decisions 834–836, lines 2359–2364.; Decisions 839–841, lines 2375–2386.; Decision 879, accepted transition line 2547.
  - Disposition: deferred
- **000024-pool-approach-receipt — Remember observed pool-approach arrivals instead of restarting completed scouting detours.** (medium, deferred): This proposal verifies a specific door-opening receipt, not the earlier approach-scouting lifecycle. The earlier rejected case still needs its own public-input validation across interrupted approach scouting, without collection credit or weakened potion-test admission.
  - Evidence: Run 000024: decisions 845–848, selection lines 2413, 2416, 2419 and 2422.; Run 000024: decisions 851 and 855, selection lines 2431 and 2445.; Incoming backlog records that candidate validation failed and code was not promoted.
  - Disposition: deferred
- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This recording establishes no safe crab surprise alternative. The earlier case still needs public-input-validated doorway-attempt, pursuit and escape bookkeeping and a bounded surprise approach with a second exit under existing health and hazard checks. Current source browsing does not certify that replacement.
  - Evidence: Run 000019: decisions 1708, 1718 and 1737, accepted lines 4852, 4885 and 4938.; Run 000019: decisions 1774, 1805, 1863 and 1966, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish admitted preparation for mandatory progression loot instead of exhausting resources in fallback.** (high, deferred): The current fatal encounter supplies no validated mandatory-loot preparation alternative. The earlier case still requires a contemporaneously known identification or extinguishing resource, or validated preparation satisfying hunger, health, hazard, protection and retrieval budgets. Unknown potion identities and waived mandatory pickup cannot justify a repair.
  - Evidence: Run 000018: decisions 2826–2827 and 3903, retained backlog evidence.; Run 000020: decisions 3990, 3992, 4438 and 4553, retained backlog evidence.; Run 000022: decisions 2683, 2756, 2909–2910 and 3632, retained backlog evidence.
  - Disposition: deferred
- **000031-entrance-scout-before-branches — Reveal remaining admitted entrance frontiers before spending shop-search movement on door branches.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2240, selection line 6539: door-directed movement while entrance frontiers remain.; Decisions 2244–2355, selection lines 6547–6806: successive door branches dominate shop scouting.; Decision 2373, lines 6846–6848: exhausted entrance-shop budget triggers fallback waiting.; Decision 2812, lines 8131–8132: final wait ends in explicitly reported starvation.
  - Disposition: implemented

## Lessons for the next run

Finish reachable scouting within the entrance-side chamber before exploring its door branches. Keep shop visitation dependent on actual nearby stock or a shopkeeper, preserve mandatory progression pickups, and do not mistake an admitted scouting move for finding the shop or surviving the floor.

Update: **accepted**.
