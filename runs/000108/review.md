# ShatteredAI run 000108

Played commit: `c90ab0fceb10cc998d0966ed9f791cbdafde00a3`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot can use a known scouting stone or mapping scroll to investigate unseen space behind reachable bookshelves, even when ordinary paths show no unexplored edges. Scouting does not count as opening the room or collecting its rewards.

## Incoming learnings

Unknown space behind sight-blocking shelves can justify stationary known reconnaissance even when ordinary movement frontiers are exhausted. Keep flame reservation and mandatory collection unresolved until fresh public observations support further action.

## Analysis

The hero remained alive at 40/40 HP when the planner stopped. Decision 1464 selected a doorway retreat toward door 782; its accepted move closed door 914 behind the hero and hid the enemies. The retreat selector then discarded its plan because fewer than two enemies were visible, while escape protection correctly rejected exploration back through the same door. Decisions 1465–1468 alternated recovery and exploration instead of continuing the observed retreat route. A healing potion was consumed before the same contradiction ended in planner exhaustion at decision 1472. A local source-pinned reconstruction matched the original selecting helper at decision 1464, then confirmed cancellation on the recorded next input; this is not a reconstruction of all original runtime memory. The focused correction preserves an accepted retreat through temporary occlusion using recent sightings only as movement constraints, with fresh visible-step checks and existing hazard, health, pressure and input budgets intact. The new regression fails on the original policy and passes on the candidate; the full suite passes 1,865 tests with four skipped. No alternative gameplay was dispatched, and neither reaching the destination nor survival is established.

## Recommendations

- **000108-occluded-door-retreat — Preserve an accepted doorway retreat through temporary enemy occlusion instead of restarting exploration into its protected escape edge.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1464, selection line 4203: retreat objective 782 and route through 913, 912 and 869 are recorded.; Decision 1464, accepted transition line 4204: movement reaches 913 without HP loss; the next observation shows door 914 closed and no visible enemies.; Decisions 1465 and 1467, lines 4208–4218: escape-reversal vetoes lead to repeated generic recovery onto 912.; Decision 1469, accepted transition line 4225: healing changes 38 HP to 40 without resolving the route.; Decision 1472, line 4234: hungry no-progress exhaustion terminates the living planner.; tools/multi_enemy_tactics.py:97–178; tools/mage_policy.py:416–422; tools/tactical_recovery.py:100–165.
  - Disposition: implemented

## Lessons for the next run

Losing sight of pursuing enemies behind a closing door is not clearance evidence. Preserve an accepted retreat when its next observed step remains admissible, rather than letting exploration immediately reverse it. Continue to require fresh safety checks and real collection evidence.

Update: **accepted**.
