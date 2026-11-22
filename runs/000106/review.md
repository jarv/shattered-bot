# ShatteredAI run 000106

Played commit: `f2861b9d55a5456dce3b05c692be42b818587d59`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A hypothetical protected chest route does not establish an executable potion experiment. Gas-room preparation needs a safe drink bank, protected inventory and a verified return using actual observed protection. Here flammable or unknown surroundings prevent bank admission independently of hunger. Preserve the supply obligation and terminal failure label rather than guess a potion, eat generally early or waive unresolved pickups.

## Analysis

The living hero exhausted the planner because mandatory discovery still reserved purity for unfinished gas-room loot. The initiating failure was earlier: decision 235 activated identified purity; decisions 236–240 followed its protected retrieval route. At decision 241 (selection line 689), 15 turns of publicly observed purification remained, but unconditional gas escape erased that route and retreated. Later departure was blocked at decision 654 (line 1998), with full health and two unidentified potions. Source-pinned offline bookkeeping matched all 654 recorded selections before the repair and reproduced exhaustion. The candidate instead continues the owned, budget-checked route at decision 241; investigation stops at that first changed selection. A reduced public-geometry regression fails on original source and passes on the candidate; the full suite passes 1,859 tests, with four skipped. This establishes corrected arbitration, not successful chest collection or survival. No recorded-run code difference was supplied, so improvements is empty.

## Recommendations

- **000106-protected-gas-arbitration — Preserve an owned gas retrieval while observed purification remains, letting its existing return-budget checks arbitrate movement.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 235, selection line 677 and accepted line 678: identified purity is consumed.; Decision 241, line 689: purification has 15 turns remaining, but gas escape cancels the protected route.; Decision 654, line 1998: missing purity for unfinished gas-room loot exhausts discovery.; tools/toxic_escape.py:20; tools/room_tactics.py:66–145; tools/mage_policy.py:1370–1372.
  - Disposition: implemented

## Lessons for the next run

An observed, active purification barrier on an owned gas retrieval must reach the existing protected-route validator rather than unconditional gas escape. Preserve duration, return-route, threat and pickup checks; never assume the reward was collected.

Update: **accepted**.
