# ShatteredAI run 000208

Played commit: `722f29979fad3a2219c38c6039971c912641db0a`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- Before approaching an ambush doorway, the bot now avoids choosing a hiding spot that would require immediately reversing its final approach step.

## Incoming learnings

Before approaching an ambush doorway, ensure its hiding bank does not require immediately reversing the protected approach edge. Preserve fresh hazard checks, mandatory discovery and pickup obligations, honest collection receipts, and explicit planner exhaustion. A different selected bank is preparation, not proof that the ambush succeeds.

## Analysis

The hero remained alive at full health when the planner stopped. Decision 220's accepted arrival revealed the pool chest; decision 221 could neither prepare its supplies nor descend. Offline bookkeeping reconstruction matched all 221 earlier selected actions and reasons against the complete recording, then reproduced the chest blocker. Fresh safe testing banks existed, and potion-storage feasibility passed, but none admitted the required protected round trip. Doorway 570 admitted a seven-step chest route but failed unknown-potion testing admission; safe bank 606 was one step farther away and exceeded the unchanged symmetric return budget. Both carried potions remained unidentified. Floor abandonment also correctly refused to bypass mandatory potion discovery. No patch is supplied: separating the testing bank from the protected return endpoint requires a new execution and recovery contract, not merely a larger allowance or weaker bank checks. The source and reconstruction resolved the packet's geometry and bookkeeping gaps, but no safe replacement transaction was validated.

## Recommendations

- **000208-pool-test-return-endpoint — Resolve the pool preparation contradiction between a safe testing bank and a protection-funded return endpoint.** (high, deferred): The demonstrated blocker is the same-bank return contract: fresh testing bank 606 has storage feasibility but needs a 21-turn symmetric plan; doorway 570 permits a 19-turn journey but is not admitted for an unknown drink. Journey execution, duration checks and completion currently assume return to the starting bank. No safe asymmetric replacement was validated, so changing only planning would contradict execution. Next derive a deterministic fixture for bank 606, doorway 570 and chest 318, then validate a distinct safe return endpoint with unchanged reserve, actual-buff checks, door costs, failed-hypothesis recovery, stash retrieval and pickup receipts before changing the selector. Do not relax testing admission or skip mandatory discovery.
  - Evidence: Decision 220, selected line 614 and accepted line 615: arrival at doorway 570 reveals chest 318.; Decision 221, lines 617–618: the uncollected pool chest blocks descent with the hero at 25/25 HP.; Result line 619: recovery accepts no actions because mandatory potion discovery remains.; Source-pinned offline reconstruction matches decisions 0–220 and reproduces the decision-221 blocker.; tools/puzzle_supplies.py:142–191,285–324,969–1007; tools/room_tactics.py:70–115,234–357; tools/mage_policy.py:456–458; tools/floor_abandonment.py:35–48.
  - Disposition: deferred

## Lessons for the next run

Plan unknown-potion testing and protected reward retrieval as distinct prerequisites when their safe locations differ. Preserve fresh bank checks, inventory protection, actual protective-effect verification, mandatory discovery, pickup receipts and explicit planner exhaustion. A feasible route calculation alone does not establish successful retrieval.

Update: **review-only**.
