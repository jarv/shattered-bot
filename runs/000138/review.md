# ShatteredAI run 000138

Played commit: `86ef3207339dbb65cf055d46552b1d1b501a6c80`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot no longer revisits gardens just to wait for their permanent ambience to disappear. Smoke, unfamiliar effects and mixed hazards still receive the usual checks.

## Incoming learnings

Do not schedule expiry observation for permanent garden ambience. Preserve uncertainty for every other effect. Investigate the summoning quarantine as the initiating progression blocker rather than treating the final search ceiling or healing fallback as its cause.

## Analysis

The living hero exhausted mandatory potion discovery, not combat or the game clock. Decision 709 (selected line 2065, accepted line 2066) follows the final gold route from grass 623 to grass 622, disconnecting remembered preparation banks under the stricter return rules. Decision 711 actually collects the gold; decision 712 then has no admitted protected test bank or preparation return. Source-pinned offline reconstruction matched all 712 earlier selections, reasons, intents and controllers. Detached earlier-state probes could select preparation before disconnection, but did not establish safe early activation, complete stash/effect recovery, and resumption of unfinished pickup. No patch or new regression is supplied: those transaction guarantees remain unvalidated, and admitting grass would weaken the existing safety restriction. Source browsing resolved the missing selecting-state uncertainty. The existing suite passed 1,955 tests with four skips; this is not repair validation.

## Recommendations

- **000061-descent-bank-return — Reserve mandatory discovery preparation before ordinary collection disconnects every admitted bank return.** (high, deferred): Complete selecting source and matching reconstruction establish preparation disconnection, but not a safe early-discovery transaction. Earlier helper proposals do not validate the global progression gate, accepted stash/effect recovery, or restoration of still-uncollected gold. Allowing grass would weaken the return safety filter. Next derive paired decision-708/709/710 fixtures and validate bounded preparation reservation at 709, preserving room supplies and the collection objective, with accepted transit/drop/drink/retrieval receipts, interruption handling and fresh pickup-route resumption. Require a new baseline-red/candidate-green regression before changing arbitration; do not waive pickup or restore death waits.
  - Evidence: Decision 708, lines 2062–2063: collection leaves door 624 for grass 623.; Decision 709, lines 2065–2066: collection moves to grass 622; copied validated-state probes change from an admitted return to no return after this move.; Decision 711, lines 2071–2072: the gold is actually collected.; Decision 712, lines 2074–2075: the living hero exhausts mandatory discovery.; tools/descent_potions.py:103–149,403–452; tools/mage_policy.py:445–495; tools/region_navigation.py:168–225.
  - Disposition: deferred

## Lessons for the next run

Reserve an executable preparation return before the last collection route disconnects it. A feasible bank or proposed preparation move is not proof of completed identification or retrieval. Preserve unfinished loot, reserved puzzle supplies, fresh arrival checks and accepted collection receipts. The previous summoning-quarantine diagnosis does not establish this recording's cause.

Update: **review-only**.
