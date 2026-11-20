# ShatteredAI run 000016

Played commit: `e1bc621ea34aa162ad61c87b7a98084b5723bb80`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved after unresolved mandatory pool preparation and prolonged fallback waits

## Improvements since the last run

- When carrying known invisibility, the bot can approach a piranha room through ordinary water outside the pool. It checks the approach for hazards and opens the entrance before drinking, while keeping the stricter rules for testing unknown potions.

## Incoming learnings

Separate identified protection staging from unknown-potion testing. Ordinary approach water outside the remembered piranha habitat can be considered only with observed hazard checks, a visible arrival recheck, an actionable entrance and a verified protection budget. Preparation is not collection.

## Analysis

The run starved to death, confirmed by the terminal public message, not inferred from nearby enemies. The initiating progression failure was unresolved unknown-supply preparation for the mandatory piranha chest. Decision 3014 (lines 8669–8671) returned from entrance 303 to dry approach 337. Decision 3015 then hit the mandatory chest descent veto (line 8672); its recorded inventory contained multiple unidentified potion types but no identified invisibility or scroll of identify. The continuation drank waterskin at 63/65 HP (lines 8673–8674), then began waiting. There were 864 depth-7 continuation waits overall, not 864 separate failures. Later combat, food use and teleportation occurred, so this was not one uninterrupted stationary episode. Ultimately decisions 4061–4063 waited at cell 319 while starving; accepted transitions show the clock advancing to 3969 and the final HP change from 1 to 0 (line 11757). The terminal observation explicitly reports starvation. Source inspection connects the pool supply leaf to piranha_tactics.choose and puzzle_supplies.prepare_supplies, then mage_policy.py:416–417's mandatory pickup veto and until_death.recover's best-effort continuation. Unknown supplies still require a visible dry test bank, protected reward round trip and feasible potion protection; the recorded improvement applies only to identified invisibility. No patch is supplied: neither the recorded preparation report nor a snapshot-only helper probe establishes a replacement satisfying all these gates. Relaxing proximity or selecting another bottle alone would not establish safe preparation. Full selecting runtime memory was not reconstructed, and no alternative decision was dispatched. Existing source tests passed: 54 targeted tests and 1535 full-suite tests, with four skips. These are not baseline-red/candidate-green evidence for a repair.

## Recommendations

- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): Complete source browsing resolves the selector and fallback chain, but does not establish a safe replacement. The actual initiating inventory has unknown supplies, and no validated alternative simultaneously demonstrates visible dry-bank safety, a budgeted protected trip, and remote protection of the other carried potions. A reduced snapshot probe admitted a hypothetical reward route but did not admit the corresponding test bank or stash. Needed follow-up is an offline, recorded-input-validated preparation state and a fixture demonstrating all three admissions, or observed access to a non-drinking identification resource. Changing only the distance filter, candidate ordering or wait bound would leave independent safety gates unresolved.
  - Evidence: Decision 3014, log lines 8669–8671: return to the dry pool approach; Decision 3015, log lines 8672–8674: mandatory chest veto and near-full-HP waterskin use; Decision 3016, log lines 8675–8677: fallback waiting begins; Decision 4063, log lines 11755–11758: final wait, HP loss and explicit starvation message
  - Disposition: deferred

## Lessons for the next run

Known-protection staging does not solve unknown-supply preparation. Establish a publicly justified identification or jointly feasible test-bank, inventory-protection and reward-trip plan before changing admission. Preserve mandatory progression pickup and actual receipt verification; do not infer potion identities from floor generation or post-death revelations.

Update: **review-only**.
