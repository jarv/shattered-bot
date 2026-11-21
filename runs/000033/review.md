# ShatteredAI run 000033

Played commit: `337e812d10754bb99af399d9367709ef2ce34e8d`

Outcome: blocked

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Stopped alive after repeated puzzle preparation and fallback waits

## Improvements since the last run

- The bot now remembers reaching an entrance-scouting position even when loot or danger interrupts its next step. This does not count as finding a shop or collecting its items.

## Incoming learnings

Remember visibly reached entrance-scouting positions even when loot or safety interrupts the next preparation step. Keep scouting receipts separate from actual shop visitation and collection, and retain all mandatory progression pickups. Removing this repeated approach does not establish shop discovery or survival.

## Analysis

The run stopped alive at full health after 128 fallback waits; elapsed turns continued advancing. An initiating preparation defect appears at decisions 654–657 (selection lines 1870, 1873, 1876 and 1879): the bot alternates between a flight-room door and its potion-test bank. Leaving the door closes it normally, but only pool entrances retain scouting receipts, so flight preparation repeatedly demands another opening. The navigation guard rejects this loop at decision 665, line 1903. Later preparation and collection conflicts precede fallback at decision 901; the final accepted wait at line 3031 leaves the hero alive.

Complete source browsing identifies the entrance lifecycle defect. A reduced deterministic fixture, not recovered runtime memory, reproduces the three earlier helper selections and stops at the first changed selection, decision 657. The correction remembers visibly entered flight entrances and permits existing inventory-protection preparation rather than another scouting lap. The new regression fails on original source with two expected assertions and passes all five tests on the candidate. The full candidate suite passes 1606 tests, with four skipped. No existing tests were changed.

This establishes neither completed inventory protection nor successful potion testing, flight, chest collection or survival. Unknown potions remain unknown; actual protection, hazard checks, trip budgets and mandatory progression pickups remain required. Later collection conflicts and older backlog alternatives remain unresolved. The proposed correction is for the next run, not an improvement present in this recording.

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
- **000033-flight-entrance-reclosure — Retain verified flight-entrance scouting when the door closes after leaving it.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 654–657, selection lines 1870, 1873, 1876 and 1879; accepted transitions at lines 1871, 1874, 1877 and 1880.; Decision 665, lines 1903–1905: entrance repetition reaches navigation-loop recovery.; Decision 901, lines 2648–2650, and decision 1028, line 3031: fallback advances time and ends without death.
  - Disposition: implemented

## Lessons for the next run

Remember publicly verified flight-entrance scouting after normal door reclosure, separately from collection and protection. Recheck the protected round trip and inventory safety before testing any unknown potion. Selecting preparation does not prove puzzle completion.

Update: **accepted**.
