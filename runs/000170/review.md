# ShatteredAI run 000170

Played commit: `2af43a5e869d2499d3a0decd7a720f7172a89c31`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A summoning chamber can create a levitation reservation while independently excluding every protected retrieval route. Before funding a puzzle meal or leaving its approach, establish an executable preparation and return contract. Unknown colors are not known protection; identification is not collection.

## Analysis

The run ended in planner exhaustion with the hero alive at 24/55 HP, not an observed death. The initiating defect was decision 2729 (log line 8144): caster flight selected door 981 although its already observed far-side banks were a wall and explosive traps. The controller checked travel to the door but deferred bank feasibility until arrival. Decisions 2730–2735 continued into that unusable threshold. Later skeleton combat and fallback attacks did not resolve ranged exposure; accepted transition 2742 (8189) reduced HP from 34 to 24, and decision 2743 (8191) exhausted the planner. Damage attribution is not established. Two remaining staff charges did not establish an admitted shot through the intervening wall. A focused candidate now rejects known unusable far-bank destinations while preserving unknown entrance scouting, fresh arrival checks, hazard exclusions, mandatory pickup and terminal exhaustion. The new regression fails on original policy and passes on the candidate; the full suite passes 2,037 tests with four skipped. A limited single-snapshot helper reconstruction matches the original recorded selection, but is not recovered full runtime memory. No changed commitment was continued. This does not establish that another doorway is safe, that the hero survives, or that any puzzle or pickup succeeds. The played-source comparison is empty, so no recorded improvements are attributed.

## Recommendations

- **000170-dm100-trapped-door-preflight — Reject caster-flight destinations whose fully observed far-side banks cannot satisfy existing cover admission.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2729, log line 8144: door 981 selected despite wall 934 and explosive traps 935–936 beyond its approach.; Decisions 2730–2735, log lines 8148–8168: committed flight reaches the unusable threshold.; Decision 2742, accepted transition line 8189: HP falls from 34 to 24 while the skeleton disappears.; Decision 2743, log line 8191: ranged-exposure planner exhaustion with the hero alive.; tools/dm100_escape.py:166–184,201–219; tools/test_shattered_dm100_trapped_door_preflight.py.
  - Disposition: implemented

## Lessons for the next run

Before committing caster flight to a known doorway, verify that its observed far side can support the required cover step. A reachable door is not itself a refuge. Unknown banks still require scouting and fresh arrival checks; available charges alone do not prove a clear shot.

Update: **accepted**.
