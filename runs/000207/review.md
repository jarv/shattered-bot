# ShatteredAI run 000207

Played commit: `d6095a5d3e84d35bc54e25b2609ff0aef035ba3f`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A remembered discovery bank is not sufficient for a reserved pool potion: testing and the protected chest return must share executable preparation. Diagnose the entrance transaction before spending more travel or waiting. Preserve unknown identities, habitat exclusions, mandatory progression pickup and explicit planner exhaustion.

## Analysis

The Mage stopped alive at full health because the planner could not proceed, not because an enemy killed it. D659 (selection line 1831, acceptance 1832) began a doorway lure whose hiding bank was its own approach origin. Accepted retreat protection then prohibited the return step. D660, D663 and D665 report escape-reversal failures; recovery repositioning did not resolve the contradiction, and D667 exhausted recovery (lines 1861–1863). Source-pinned offline reconstruction matches all 667 recorded actions and intents and establishes this bookkeeping; it is not originally recorded memory. Mandatory potion discovery independently prevented fallback descent and remains enforced. The proposed focused correction excludes the final approach bank when selecting a fresh ordinary doorway lure, without weakening retreat protection or hazard checks. A new regression fails on the original source and passes on the candidate. An isolated validated-state probe selects an already observed alternative bank, but no changed-policy continuation, successful ambush, potion discovery, collection or survival gain is established. The recorded source comparison is empty, so there are no recorded improvements to attribute.

## Recommendations

- **000207-doorway-approach-bank — Reject fresh doorway hiding banks that contradict protection of the accepted approach edge.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D659, lines 1831–1832: doorway approach from 946 to 979.; Validated offline reconstruction: the fresh D659 plan chooses hiding bank 946; the accepted approach protects edge 946→979.; D660, D663 and D665, lines 1835, 1846 and 1853: escape-reversal failures followed by recovery repositioning.; D667, lines 1861–1863: terminal navigation exhaustion with the hero alive; mandatory potion discovery vetoes fallback descent.; tools/survival_policy.py:717–797; tools/doorway_tactics.py:275–296; tools/escape_commitment.py:14–37; tools/tactical_recovery.py:100–166.
  - Disposition: implemented

## Lessons for the next run

Before approaching an ambush doorway, ensure its hiding bank does not require immediately reversing the protected approach edge. Preserve fresh hazard checks, mandatory discovery and pickup obligations, honest collection receipts, and explicit planner exhaustion. A different selected bank is preparation, not proof that the ambush succeeds.

Update: **accepted**.
