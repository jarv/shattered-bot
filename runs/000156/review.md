# ShatteredAI run 000156

Played commit: `bff6c71236acb576ea37378a0763a5f3f873daaa`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot keeps fighting at an established choke when a normal-speed rat is already attacking through the doorway, rather than assuming it can sidestep to let another rat attack simultaneously.

## Incoming learnings

Do not count a normal-speed rat already attacking from an established choke as simultaneously sidestepping to make room for another attacker. Keep prospective movement and fast-enemy pressure conservative, and require fresh geometry and existing combat admission before retaining a hold.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. Decision 1107 (selection line 3191, accepted line 3192) retreated from 666 into 636: the recorded report calls it a non-choke endpoint, yet its only onward door, 606, was locked without a matching key. The multi-enemy selector mistook low immediate pressure for a usable retreat destination. After attacks from the pocket, decisions 1112–1113 rejected reversal along the only ordinary exit while recovery also excluded its dropped spear. Accepted waits advanced the clock; decision 1114 exhausted hungry recovery. Source inspection and isolated public-state probes reproduce the initiating retreat, without claiming recovered runtime memory. The proposed correction requires admitted onward space for non-choke retreat endpoints while preserving verified chokes and all existing safety and pickup gates. The new regression fails against the original selector and passes on the candidate; the full suite passes 2000 tests with four skips. An isolated candidate probe selects existing staff combat instead, but establishes neither combat success nor future survival.

## Recommendations

- **000156-nonchoke-retreat-pocket — Reject ordinary multi-enemy retreat endpoints that have no admitted onward exit.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1107, selection line 3191 and accepted line 3192: non-choke retreat 666 to 636 ends beside keyless locked door 606.; Decisions 1112–1113, lines 3208–3213: escape-reversal vetoes and accepted recovery waits leave the hero in the pocket.; Decision 1114, line 3214: hungry recovery exhausts with the hero alive at 35/35 HP.; tools/multi_enemy_tactics.py:141–161; tools/retreat_geometry.py:8–39; tools/tactical_recovery.py:105–165.
  - Disposition: implemented

## Lessons for the next run

Low approach pressure alone does not make an ordinary retreat endpoint usable. Require observed, admitted onward space unless the endpoint is a verified choke. Keep escape protection, hazard checks, mandatory collection and explicit planner exhaustion; do not substitute eating or longer waits for a blocked route.

Update: **accepted**.
