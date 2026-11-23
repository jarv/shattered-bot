# ShatteredAI run 000192

Played commit: `7b1589953a4d252e1698d738086cf0045ae94dd3`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died after prolonged retreats while starving; exact cause unconfirmed

## Improvements since the last run

- When escaping toxic gas, the bot now avoids gas-free ground that it already recognizes as part of a hazardous special room, rather than treating every clear tile as a safe destination.

## Incoming learnings

Gas-free ground is not necessarily a safe exit: preserve recognized piranha-bank and other special-room exclusions when choosing a gas escape. Reobserve after each step, retain unfinished loot honestly, and keep terminal exhaustion rather than restoring repeated waits. A corrected selection does not establish successful escape or puzzle completion.

## Analysis

The hero died after a loot-directed move at one HP; decision 1266's accepted transition confirms death but not an unambiguous killer. Starvation was public, and potion identities revealed afterward were not available beforehand. There were no planner incidents. Earlier, repeated doorway retreats failed to establish a flight-aware hold. The focused defect is decision 1116: the bot committed to door 299 even though its observed surroundings already failed every existing holding-square check against the two flies. Decisions 1116–1118 reached that door, and decision 1119 reported the predicted missing hold. The proposed narrow preflight rejects such fully observed, unusable flying-enemy setups while retaining unknown-perimeter reconnaissance and arrival checks. An isolated public-geometry fixture reproduces the original commitment; the candidate chooses the existing ordinary retreat without claiming a choke. The new regression fails as expected on original source and passes on the candidate; the full suite passes 2104 tests with four skipped. This does not establish successful escape or that this defect alone caused death.

## Recommendations

- **000192-known-flying-door-hold — Reject new flying-enemy doorway commitments when complete local observations already rule out every holding square.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 1035 and 1037, log lines 3087 and 3098: earlier doorway arrivals fail hold verification.; Decision 1116, log line 3381: commits to door 299 despite observed geometry rejecting every flight-aware hold.; Decisions 1116–1118, accepted log lines 3382, 3387 and 3392: travel reaches door 299.; Decision 1119, log lines 3396 and 3398: no hold is verified; subsequent retreat loses one HP.; tools/multi_enemy_tactics.py:190–264: new-route selection precedes arrival-only hold validation.
  - Disposition: implemented

## Lessons for the next run

Before committing to a doorway against flying pursuers, use already observed geometry to rule out doors with no viable holding square. Keep unknown-side reconnaissance distinct from verified refuge, preserve mandatory pickups and hazard gates, and do not equate a corrected plan with successful escape.

Update: **accepted**.
