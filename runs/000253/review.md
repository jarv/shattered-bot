# ShatteredAI run 000253

Played commit: `799e906ab8ceaa6895d1769352e2d971bfeb6143`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a sewer snake under fly pressure

## Improvements since the last run

- After a crystal key is spent and the chosen chest opens, the bot no longer saves flight or gas-protection supplies for the unavailable alternative. It still treats that chest as uncollected and reconsiders it if another key appears.

## Incoming learnings

Unavailable crystal-choice alternatives must not reserve flight supplies after the last-key spend is publicly verified. Keep their loot uncollected, reopen eligibility when a new key is observed, and preserve reservations for independent mandatory rewards. Unknown potion colors remain unknown until observed identification.

## Analysis

The full terminal receipt identifies a sewer snake as the killer: decision 1141, log line 3285, records HP falling from two to zero and explicit snake death text. The compact packet omitted that text. Flies contributed sustained combat pressure, but proximity alone is not the basis for killer attribution. No planner incidents were recorded.

An earlier priority defect appears at decisions 1120–1123, log lines 3202–3210. With both damage wands empty, the bot twice throws clubs at an adjacent fly while an ordinary gnoll is also adjacent. The settled throws cost five HP without an observed reduction in the gnoll's health. They do not establish fly splitting. Once those clubs are gone, decisions 1124–1125 reach the existing rule that attacks the ordinary contact enemy instead. Actual splitting is subsequently observed after melee at decision 1126, followed by desperate fragment attacks.

The cause is the ordering in tools/unit_strategies.py: early fly dispatch includes thrown weapons and returns before the existing ordinary-contact alternative. The proposed correction shares that alternative's admission checks and lets existing escape, control and contact arbitration run before physical fly dispatch when it qualifies. Known magic, protected enemies, hazard checks, mandatory pickups and honest collection accounting remain unchanged.

A new public-evidence-derived regression fails on the original source with the expected wrong-action assertions and passes on the candidate. The complete unittest suite passes: 2,414 tests, four skipped. These are isolated selector tests, not a reconstructed runtime or gameplay replay. A fresh full-snapshot probe reaches an existing doorway tactic after the correction; the reduced fixture reaches the contact strike. Neither establishes the original mutable controller state, guaranteed safety, fewer realized losses or survival. Policy and regression changes are supplied through the trusted adapter; files is intentionally empty.

## Recommendations

- **000253-mixed-fly-thrown-priority — Prevent early physical fly dispatch from bypassing an admitted ordinary-contact alternative.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1120, log line 3202: empty wands, adjacent gnoll and fly, club selected against fly.; Decisions 1121–1123, log lines 3205–3210: settled throws reduce hero HP from 27 to 22 while gnoll remains at 8/16.; Decisions 1124–1125, log lines 3212–3217: existing contact rule becomes reachable after uncursed clubs leave inventory.; Played tools/unit_strategies.py:30–31,73–79,154–172; tools/survival_policy.py:629–684.
  - Disposition: implemented

## Lessons for the next run

Thrown weapons can split flies too. An early species-specific throw must not bypass an already admitted ordinary-contact alternative when magic is empty. Preserve escape and control precedence, and distinguish a corrected selection from proven survival.

Update: **accepted**.
