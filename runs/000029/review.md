# ShatteredAI run 000029

Played commit: `83df557a4ee7029a255fca33bcd571025766655b`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died while starving after repeated preparation and combat stalls

## Improvements since the last run

- When required loot needs potion preparation already underway, the bot now continues its existing stash-and-return routine instead of starting another approach to the same loot.

## Incoming learnings

When required loot depends on potion preparation already in progress, let the existing stash workflow advance before selecting another test approach. Keep potion identities unknown until publicly established, verify every drop and pickup, and retain the upgrade obligation until collection is observed.

## Analysis

The Mage died while starving after prolonged preparation and combat stalls. The final accepted wait at decision 4562 (lines 13161-13162) changes health from 1 to 0; a particular enemy killer is not established. An earlier mandatory-pool block at decision 3021 already caused fallback while hungry. A separate, reproducible preparation defect then repeatedly reopened entrance 732 after returning to dry bank 731 (decisions 3176-3187), eventually reaching the navigation-loop guard at decision 3204. Ordinary doors close on departure, but the played helper required another opening each time. Source inspection and an offline helper reconstruction from public geometry and inventory bookkeeping reproduce the earlier opening and return inputs. The proposed correction first changes decision 3178 to a guarded unknown-potion test; investigation stops there, without using later observations as its continuation. A new deterministic regression fails on original policy copies with the expected assertion and passes on the candidate. All 1,593 Python tests pass, with four skips. This establishes a receipt repair, not chest retrieval, potion identity, or improved survival. Other backlog cases remain unresolved.

## Recommendations

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
- **000029-pool-entrance-reclosure — Retain verified pool-entrance scouting when an ordinary door closes behind the hero.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3176, selection line 9050 and accepted transition 9051: enter entrance 732.; Decision 3177, lines 9053-9054: return to dry bank 731; the door closes normally.; Decision 3178, lines 9056-9057: reopen the same entrance instead of proceeding with preparation.; Decision 3204, line 9124: repeated staging reaches the navigation-loop guard.
  - Disposition: implemented

## Lessons for the next run

An ordinary door closing behind the hero does not erase an observed successful scouting arrival. Retain that receipt, but replan the full protected round trip and verify the actual potion effect before entering danger. Do not treat preparation as collection or infer unknown potion identities.

Update: **accepted**.
