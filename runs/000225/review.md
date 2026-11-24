# ShatteredAI run 000225

Played commit: `0db6dcdaff393a787a3d555226f3426224823d03`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a necromancer’s skeleton after breaking invisibility

## Improvements since the last run

- When a charged Talisman warns of danger near visible loot, the bot can inspect the approach before walking toward it. It limits these scans and still checks for threats and hazardous terrain.

## Incoming learnings

Respond to a public foresight warning before approaching nearby loot when a charged Talisman can inspect it. Preserve unidentified supplies without assuming their effects. A vanished potion is not a pickup receipt, and choosing reconnaissance does not prove a blocked puzzle is solved.

## Analysis

The hero died after sustained combat pressure. The complete public death receipt identifies a necromancer’s skeleton, resolving the compact report’s unknown attribution. The focused policy defect begins at decision 3044 (log line 8632): at 17/60 HP with invisibility active, the early caster-escape controller selected a zap against an adjacent DM-100 before protected withdrawal could run. The accepted target at decision 3045 (8635) removed invisibility; decision 3047 (8640) emptied the staff and reduced HP to 11. The final retreat at decision 3048 (8643) ended in death. This establishes an arbitration contradiction, not proof that preserving invisibility would guarantee survival. A focused proposed guard makes that early controller yield to existing survival selectors while protection is active below half health. A new reduced public-evidence regression fails on original policy and passes on the candidate; the full suite passes 2,228 tests with four skipped. Independent fresh-state probes reproduce the recorded original attack and select existing retreat on the candidate; they are not historical memory reconstruction or gameplay replay. The adapter derives the changed policy and regression files; files is intentionally empty.

## Recommendations

- **000225-invisible-caster-priority — Prevent the early DM-100 escape selector from bypassing low-health invisibility withdrawal.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3040, accepted log line 8615: invisibility is established at 17/60 HP.; Decision 3044, log lines 8632–8633: early caster escape selects ZAP while invisible.; Decision 3045, accepted log line 8635: targeting the caster removes invisibility.; Decisions 3047–3048, accepted log lines 8640 and 8643: staff depletion, HP loss, then lethal retreat.; tools/policy_tree.py:15–36; tools/policy_nodes.py:93–120; tools/dm100_escape.py:69–77; tools/combat_positioning.py:23–54.
  - Disposition: implemented

## Lessons for the next run

Do not let an early caster-escape controller cancel low-health invisibility before protected withdrawal is considered. Preserve existing movement checks and finite retreat budgets. Selecting a different retreat does not establish survival or successful loot recovery.

Update: **accepted**.
