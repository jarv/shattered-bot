# ShatteredAI run 000002

Played commit: `35b055cb715e75f7943eb61d78f87d96b5a538a9`

Outcome: dead

Java build: `2d6e7b4f2433e84e361a92fd80e6540d95a663e43b9269b59cc5fa6a7724cce8`

Outcome summary: Died after repeated frontier reversals and recovery stalls

## Improvements since the last run

- Refused underfoot dewdrop pickups defer the loot attempt instead of marking the occupied floor blocked; uncollected loot remains outstanding.

## Incoming learnings

Separate a refused underfoot pickup from failed movement. Keep uncollected loot outstanding, and do not blame a frontier for a room-loot override loop. This repair does not prove exit discovery.

## Analysis

The run ended in death: decision 1198's accepted transition (log line 3417) drops HP from 2 to 0 after melee input. Nearby enemies alone do not establish the killer. An earlier initiating navigation defect is supported by decisions 1056-1057 (lines 2966-2971): persistent region planning moves from 119 to 155 toward frontier 722, then visibility of an explicitly magically sleeping crab switches exploration to the legacy global frontier selector, which returns to 119. Repetition precedes the systematic-route-stall at decision 1062, line 2984. MagePolicy.systematic_exploration_enabled rejects any enemy list, including sleepers; SurvivalPolicy.explore then bypasses the committed region target. Later continuation waits advance game time, rather than demonstrating a frozen clock. One focused selector correction and a new reduced deterministic regression are supplied for independent validation: preserve region planning when all visible foes are explicitly sleeping, without changing occupancy or hazard admission. Original source fails the reversal assertion; the candidate passes all three new tests and the full 1402-test suite (four skips). The fixture is synthetic, derived from public evidence, not reconstructed original runtime memory or a gameplay replay. This establishes selector consistency, not a safe real-run route, puzzle success, collected loot, or prevention of death. The files array is empty because the trusted adapter derives workspace changes.

## Recommendations

- **000002-R1 — Keep persistent region exploration when only explicitly sleeping foes are visible.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1056, log lines 2966-2968; Decision 1057, log lines 2969-2971; Decisions 1058-1062, log lines 2972-2986; tools/mage_policy.py:1240; tools/survival_policy.py:985-995,1049-1054
  - Disposition: implemented

## Lessons for the next run

Do not let visibility of an explicitly sleeping foe alternate frontier planners. Preserve committed navigation while retaining enemy occupancy, active-threat arbitration, hazard checks, and mandatory progression obligations. Validate selector repairs separately from claims of successful exploration or survival.

Update: **accepted**.
