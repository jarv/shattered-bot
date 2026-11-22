# ShatteredAI run 000149

Played commit: `a03452776a0d1d81eb2cd1760357122c02220639`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a sewer crab after prolonged mixed-enemy pressure

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

No review performed; no new learnings claimed.

## Analysis

The full terminal observation at log line 4962 explicitly identifies a sewer crab as the killer; accepted decision 1649 (line 4959) lowers HP from 1 to 0. Earlier, a concrete avoidable attrition defect occurs in doorway combat: decision 1456 successfully surprise-strikes a wraith, but decisions 1457–1466 (lines 4322–4345) repeatedly use ordinary melee against the next evasive wraith despite 4–5 staff charges. Repeated dodges and unchanged wraith counts accompany HP falling from 36 to 19. The early rule-preparation controller calls the established-hold selector before the dedicated wraith controller; its ordinary damage scoring overlooks evasion. A focused correction now prefers an already-admitted magic attack against a wraith in that established hold, while preserving the initial surprise attempt, existing fallback and safety checks. A reduced public-evidence fixture fails with two expected assertions on original source and passes all six tests after correction. All 1,970 Python tests pass, with four skipped. Local reconstructed preparation state matches the recorded selections at decisions 1456 and 1457 on original source; the candidate first differs at 1457, where investigation stops without subsequent simulated observations. This is not a full-run reconstruction or evidence that the later fly pressure, retreat failures or death would be prevented. Four potion colors remain unidentified before death; the subsequently revealed healing potion was not known emergency healing.

## Recommendations

- **000149-doorway-wraith-magic — Preserve admitted magic priority against evasive wraiths after an established doorway surprise strike.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1455, accepted line 4316 and movement receipt 4317: the hero retreats from door 1268 to holding square 1267.; Decision 1456, lines 4320–4321: the initial surprise strike defeats one wraith without spending a staff charge.; Decisions 1457–1466, lines 4322–4345: ten established-hold melee attempts retain 4–5 charges while HP falls from 36 to 19 and three wraiths remain.; Decisions 1467–1472, lines 4347–4358: subsequent zaps are followed by observed wraith defeats.; Selecting chain: tools/policy_tree.py:26; tools/mage_policy.py:1180–1182; tools/doorway_tactics.py:111–122; tools/survival_policy.py:618–688.
  - Disposition: implemented

## Lessons for the next run

An established doorway limits approach lanes but does not remove wraith evasion after the first surprise strike. Preserve admitted magic priority there instead of comparing nominal melee damage alone. Do not treat post-death potion identities as resources the living bot knew how to use.

Update: **accepted**.
