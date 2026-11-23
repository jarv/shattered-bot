# ShatteredAI run 000213

Played commit: `b363b365b828fe05eee387064b3a6ab2fce00e14`

Outcome: blocked

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Blocked alive in toxic gas

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A required key on a toxic gas plate needs its own safely bounded preparation plan. Do not reuse a chilling trap's radius check, assume levitation from an unidentified potion, or treat a throwable container as proof of safe gas clearance. Preserve the unfinished pickup until an actual collection receipt.

## Analysis

The run stopped with the hero alive at full health, not an observed death. Decisions 759–765 committed to a doorway retreat while a mimic and gnoll pursued. The accepted transition at decision 765, log line 2297, entered door 1024; the next observation revealed toxic gas and a mimic occupying the clear exit. Earlier public observations did not reveal that gas room, so rejecting the door using later knowledge would be unjustified. The initiating planner defect was treating walking and transport exhaustion as total exhaustion: tools/toxic_escape.py stopped before considering the identified, throwable potion of purity already carried. The pinned game source supports self-splash gas clearance. The proposed correction selects that emergency action only after existing escape options fail and preserves item eligibility, impact safety, terminal stops and honest pickup receipts. A new evidence-derived regression fails on the original selector and passes on the candidate; the final full suite passes 2185 tests with four skipped. A fresh-state probe also reproduces the original stop on the complete terminal observation. No original runtime memory or subsequent gameplay was reconstructed. Selecting clearance does not establish successful throwing, gas removal, loot collection or survival.

## Recommendations

- **000213-boxed-gas-purity — Consider verified purity self-splash before declaring boxed toxic-gas escape exhausted.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 759, log line 2266: doorway retreat commitment.; Decision 765, log lines 2296–2297: accepted entry into door 1024.; Decision 766, log line 2301: gas emergency, occupied clear exit, identified throwable purity, and unrecovered planner incident.
  - Disposition: implemented

## Lessons for the next run

When gas escape routes are exhausted, consider an identified purity self-splash on a verified safe impact tile before declaring planner failure. Reobserve the result; never infer clearance, protection or collection from selecting the action. Unknown rooms must not be judged using later revelations.

Update: **accepted**.
