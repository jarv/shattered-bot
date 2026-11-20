# ShatteredAI run 000025

Played commit: `ca4452863e8f9e149bacf86256f677a53adf3588`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died under multi-enemy pressure after an unidentified scroll caused teleportation

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Treat arrival at a pool approach as completed scouting, not completed loot. Retain that receipt when preparation is interrupted or declines, while rechecking actual potion-test admission separately. Unknown potion identities and hypothetical protection cannot justify entering the pool.

## Analysis

The initiating disruption was an unidentified-scroll experiment, not the final fly fallback. Decision 833 (selection line 2357, accepted line 2358) read ODAL at full health with a staff at 1/5. The accepted transition moved the hero from 538 to 842; the next public observation explicitly reported teleportation and showed an awake crab and sleeping enemies. The remaining cast was spent, followed by physical combat, retreats and escalating multi-enemy pressure. Decision 879's accepted transition at line 2547 reduced HP from 2 to 0; the evidence does not identify the fatal attacker. The selecting chain reaches tools/consumable_tactics.py:58-104 through the combat-consumable controller. Its quiet-location and health checks admit deliberate unknown-scroll discovery, but do not establish readiness for random displacement. An isolated fresh-policy helper probe matches decision 833; this is not reconstructed runtime memory or validation of earlier selections. Post-death item identities were not used. No patch or regression is supplied: the source explains the initiating choice, but this recording does not establish a justified charge threshold, admitted preparation sequence or safe replacement identification/escape action. Adding such a threshold or disabling discovery globally would be speculative. Mandatory progression and hazard checks remain unchanged. The unchanged-source suite passed 1569 tests with 4 skipped; there is no candidate or red/green regression claim. The recorded source diff is empty.

## Recommendations

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

## Lessons for the next run

A quiet starting square does not make unknown-scroll discovery safe: displacement can expose a nearly depleted Mage to fresh enemies. Evaluate bounded discovery readiness and preparation using public resources, without assuming potion identities or certifying survival from a larger charge reserve alone.

Update: **review-only**.
