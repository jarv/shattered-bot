# ShatteredAI run 000034

Played commit: `9616d2706449b2f2a475b8f925926efa0f5beb5d`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died from a skeleton's bone explosion after guard and summoner pressure

## Improvements since the last run

- After visibly entering a flight-room doorway, the bot remembers that scouting even if the door closes again. It still checks potion protection and the planned round trip before preparing to cross.

## Incoming learnings

Remember publicly verified flight-entrance scouting after normal door reclosure, separately from collection and protection. Recheck the protected round trip and inventory safety before testing any unknown potion. Selecting preparation does not prove puzzle completion.

## Analysis

The initiating episode was a mixed guard and necromancer encounter, not the final fallback alone. Decisions 3005–3007 (lines 8570–8575) attack the guard while the summoner is visible; the melee transition loses 15 HP. After healing and retreat, decisions 3010–3019 retain a doorway and attack its summoned skeleton. Decision 3020 (lines 8610–8611) loses the choke through displacement with a public guard-pull announcement. At decision 3024 (lines 8620–8622), ranged survival finds no admitted action despite six charges in a separate wand; a charged wand does not prove a clear shot. Fallback spends the last dew, then retreat and combat exhaust health and charges. Decision 3050 (lines 8707–8708) attacks an adjacent wounded skeleton at 1 HP; the accepted after-observation explicitly confirms death by bone explosion. The source chain is early preparation through tools/mage_policy.py:1098 and tools/doorway_tactics.py:42–129, then tools/ranged_tactics.py:196–250, with later summoner dispatch and eventual tools/continuation.py:34–64 fallback. Full source and logs resolve the selecting order and omitted resource observations, but do not establish an admitted replacement for the supported doorway encounter. No policy memory was reconstructed, no alternative was dispatched, and no post-death identities were treated as earlier knowledge. No patch or new regression is supplied: simply changing target priority or yielding to a route generator would not validate guard-control exposure and escape safety. The unchanged full Python suite passed 1,606 tests with four skips; this does not establish a safe alternative.

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
- **000034-supported-doorway-admission — Establish an admitted alternative to sustained doorway fighting against a supported skeleton.** (high, deferred): The full selecting source explains early doorway retention and ranged preemption, but no validated safe replacement is established. A focused repair needs a contemporaneous admitted caster shot, bounded approach, or contact-breaking route accounting for guard pull, current and remembered threats, impairment, hazards, health and hunger costs. Existing summoner approach scoring counts melee adjacency and does not itself certify safety against guard control. Validate earlier selections in a source-pinned reconstruction before probing alternatives on copies; stop at the first divergence. Neither extra charges, unknown potion identities, nor simply moving summoner priority earlier supplies that evidence.
  - Evidence: Decisions 3005–3007, lines 8570–8575: guard attacks while a necromancer is visible; melee loses 15 HP.; Decisions 3010–3019, lines 8584–8609: preparation retains the doorway and repeatedly attacks the summon.; Decision 3020, lines 8610–8611: guard-pull announcement accompanies displacement and loss of the choke.; Decisions 3024–3025, lines 8620–8626: no admitted ranged action, last dew consumed, then exposed retreat.; Decision 3050, lines 8707–8708: terminal attack and publicly confirmed bone-explosion death.
  - Disposition: deferred

## Lessons for the next run

Separate a retained doorway from a resolved summoner encounter. Validate a bounded caster attack or contact-breaking alternative under guard-pull pressure before changing priorities. Known charges are not proof of a clear shot, and choosing preparation is not proof of puzzle completion.

Update: **review-only**.
