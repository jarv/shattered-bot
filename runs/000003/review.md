# ShatteredAI run 000003

Played commit: `537625d829b698f520495e53fca7c46b8eac7bd4`

Outcome: dead

Java build: `2d6e7b4f2433e84e361a92fd80e6540d95a663e43b9269b59cc5fa6a7724cce8`

Outcome summary: Died to a slime after prolonged retreats with exhausted magic

## Improvements since the last run

- Kept the legacy systematic frontier planner active when only explicitly sleeping enemies are visible; enemy occupancy and active-threat admission remain unchanged.

## Incoming learnings

Do not let visibility of an explicitly sleeping foe alternate frontier planners. Preserve committed navigation while retaining enemy occupancy, active-threat arbitration, hazard checks, and mandatory progression obligations. Validate selector repairs separately from claims of successful exploration or survival.

## Analysis

The complete recording confirms death to a slime: decision 1197 (log line 3561) moved at 1 HP, and accepted transition 3562 reached 0 HP with explicit public death attribution. An earlier avoidable arbitration issue starts at decision 1135 (3310): at 18/40 HP with an empty staff, the hero withdrew from an adjacent caustic slime displaying 1/19 health. The existing two-attempt weak-enemy exception included slime but omitted caustic slime, although the unit-profile chain treats it as ordinary melee. Nine retreat inputs followed before decision 1144; its accepted transition (3347) records a melee defeat of that still-weakened foe at 15 HP. This does not prove an earlier attack would hit or prevent death. The candidate adds only this species to the existing bounded exception, allowing downstream combat arbitration rather than forcing an attack. A reduced public-input leaf fixture failed two assertions on original policy and passes all four tests on the candidate; the full suite passes 1406 tests with four skips. No full runtime-memory reconstruction or counterfactual gameplay continuation was performed. Earlier cursed-ring equipment, starvation and later multi-enemy pressure remain contributors, not repaired by this change. Unidentified carried potions are not treated as known healing from post-death revelations.

## Recommendations

- **000003-caustic-finisher — Include caustic slime in the existing bounded nearly-dead ordinary-enemy finisher exception.** (medium, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1135, log lines 3310-3311; Decision 1138, accepted transition 3323; Decision 1144, log lines 3346-3347; Decision 1197, accepted transition 3562
  - Disposition: implemented

## Lessons for the next run

Recognized ordinary enemy variants should receive the same bounded weak-target arbitration when their public observations satisfy its gates. Preserve hazard, healing, crowding, attack-admission and mandatory progression-pickup precedence. A selector regression is not evidence of a guaranteed kill or survival.

Update: **accepted**.
