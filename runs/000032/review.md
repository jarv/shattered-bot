# ShatteredAI run 000032

Played commit: `4e45053d8e10cbdf126305a5d33fbf619ebf7f9c`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved to death after entrance-shop scouting stalled

## Improvements since the last run

- The bot now finishes reachable scouting within the entrance chamber before checking its door branches. It still requires nearby shop goods or a shopkeeper before counting a shop visit.

## Incoming learnings

Finish reachable scouting within the entrance-side chamber before exploring its door branches. Keep shop visitation dependent on actual nearby stock or a shopkeeper, preserve mandatory progression pickups, and do not mistake an admitted scouting move for finding the shop or surviving the floor.

## Analysis

The Mage defeated Goo, then starved to death after entrance-shop scouting exhausted its budget. The terminal public message explicitly confirms starvation (decision 3351, accepted transition line 9720; terminal observation line 9723), rather than a skeleton kill. An earlier initiating defect is visible at decisions 2054–2056: scouting reaches cell 931 (lines 5968–5969), loot preparation immediately sends the hero back toward 892 (lines 5970–5971), and shop scouting selects 931 again (lines 5973–5974). This repeats through decision 2064. The selecting source only marks the current scouting position exhausted inside peaceful preparation; an earlier preparation selection bypasses that bookkeeping. The shop then keeps treating an already reached frontier as untried. The shop-budget failure appears at decision 2180, line 6252, followed by advancing fallback waits. The proposed correction records a visibly observed arrival following the specific shop-scouting step during observation update, before another controller can preempt peaceful preparation. It changes neither the search budget nor shop-visitation, loot, hazard, or mandatory progression requirements. A condensed deterministic fixture fails on original policy source and passes with the correction; all 1601 Python tests pass, with four skips. No original runtime memory was reconstructed and no replacement decision on the actual run is certified. This establishes the receipt defect and its narrow repair, not that this change would find the shop or prevent starvation.

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
- **000032-shop-frontier-arrival — Retain observed entrance-scouting arrivals across preparation interruptions.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2054, lines 5968–5969: entrance scouting moves from 892 to 931.; Decision 2055, lines 5970–5971: earlier loot preparation moves back toward 892.; Decisions 2056–2064, lines 5973–5993: scouting and loot repeatedly reverse the same approach.; Decision 2180, line 6252: entrance-shop search budget is exhausted.; Decision 3351, lines 9720 and 9723: terminal transition and public message confirm starvation.
  - Disposition: implemented

## Lessons for the next run

Remember visibly reached entrance-scouting positions even when loot or safety interrupts the next preparation step. Keep scouting receipts separate from actual shop visitation and collection, and retain all mandatory progression pickups. Removing this repeated approach does not establish shop discovery or survival.

Update: **accepted**.
