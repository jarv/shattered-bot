# ShatteredAI run 000161

Played commit: `82da440ee9f545eeb63765de265f57857a97014a`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot no longer reserves every unidentified potion for an optional distant-well drop. It still requires verified fall protection for that drop and leaves it unfinished until completed.

## Incoming learnings

An optional distant-well project must not monopolize unidentified potions needed for mandatory discovery. Keep its protection and loot unfinished until verified. Removing that contradictory reservation does not prove that a safe preparation bank can currently be reached.

## Analysis

The hero remained alive at full health when mandatory potion discovery exhausted the planner (decision 358, log 991). Amber had just been identified as haste; magenta remained unknown. Earlier visible water preparation ground, including bank 240 at decision 223 (log 613), was discarded because no potion was yet carried. The first potion arrived only at decision 337. Source-pinned offline reconstruction matches all 358 preceding selections and reproduces the terminal blocker with no remembered bank. The proposed narrow correction retains genuinely witnessed preparation ground with an empty potion signature. Later pickup must still pass existing inventory-aware storage, safe transit, hunger and fresh arrival checks. Candidate reconstruction first changes decision 358 to an admitted return step toward bank 240 and stops there without dispatch. The new regression fails on the original missing witness and passes on the correction; the full suite passes 2018 tests with four skipped. This establishes preparation selection, not successful arrival, drinking, retrieval or descent.

## Recommendations

- **000161-pre-potion-bank-witness — Retain witnessed preparation banks before the first potion pickup, requiring inventory-aware validation before returning.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 223, logs 613–614: visible preparation ground near water 240 before any potion is carried.; Decision 337, log 940: first carried potion appears; decision 348, log 967 adds magenta.; Decision 358, log 991: mandatory discovery exhausts with the hero alive and no retained bank witness.; Offline original-source reconstruction matches decisions 0–357 and the blocker; candidate first changes decision 358 to preparation-only return.
  - Disposition: implemented

## Lessons for the next run

Remember safe preparation ground even before finding the first potion, but replan protection for the actual carried inventory and reobserve on arrival. An admitted return is not proof that the subsequent storage transaction will succeed.

Update: **accepted**.
