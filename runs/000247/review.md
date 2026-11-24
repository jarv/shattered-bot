# ShatteredAI run 000247

Played commit: `d4afd714a32e3b2ffee285c4d83f33bdbce44910`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now accounts for naturally fast enemies, such as bats and crabs, when judging how quickly pursuers can close a short gap, even when no speed buff is visible.

## Incoming learnings

Use the existing fast-movement species capability consistently when evaluating short pursuit gaps; an empty buff list does not make a vampire bat slow. Keep pursuit risk separate from current melee contact, and verify actual damage, defeat and pickup receipts. The isolated fixture demonstrates a different admitted selection, not encounter success.

## Analysis

The hero remained alive at full health when the planner stopped. A confirmed earlier use of the floor’s liquid-flame supply enabled an early departure shortcut. At decision 655, that shortcut preempted ordinary exploration despite 16 recorded frontiers and three unopened doors; mandatory strength discovery then blocked on missing flight preparation. All preparation alternatives declined, and no recovery descent occurred. The focused repair makes this early shortcut yield while ordinary frontiers or unopened doors remain, leaving action admission to existing controllers. A reduced public-coordinate regression fails on the original policy and passes on the candidate; the full suite passes (2282 tests, four skipped). This is not a recovered runtime-memory replay: the precise flight-demand path exclusions remain uncertain. The repair does not certify puzzle completion, identify the unknown potion, credit collection or establish eventual survival. Changed files are supplied through the trusted adapter.

## Recommendations

- **000247-spent-supply-frontier — Prevent one exhausted room supply from preempting unfinished ordinary floor observation.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 469–470, log lines 1342–1346: confirmed liquid-flame consumption for another use.; Decision 632, log lines 1838–1839: missing-supply discovery blocker precedes a puzzle meal.; Decision 655, log lines 1898–1899: early exhausted-supply departure selected with remaining frontiers and doors; missing flight preparation blocks discovery.; tools/policy_tree.py:43,74; tools/room_supplies.py:291–315; tools/descent_potions.py:272–300,350–389.
  - Disposition: implemented

## Lessons for the next run

A spent supply defers its own room, not all remaining floor exploration. Preserve ordinary observation opportunities before invoking departure-only strength discovery; keep mandatory pickup, protection and actual collection receipts unchanged.

Update: **accepted**.
