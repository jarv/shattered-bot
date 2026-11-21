# ShatteredAI run 000072

Played commit: `9cd806ecc66aab77728abc8d9488661b4088fe7c`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Mandatory discovery needs an executable return plan before exploration leaves the verified testing area. A remembered bank is not current permission to drink: separate bounded transit, fresh visible safety checks, inventory protection, accepted consumption and retrieval receipts.

## Analysis

The run ended with a living, full-health hero and a stuck planner, not an observed death (decision 313, log line 970). Gas-room supplies remained unresolved, so mandatory potion discovery correctly refused to spend unknown colors as unrelated strength tests. An earlier supply opportunity was incorrectly excluded: crystal-branch valuation could not traverse ordinary closed doors, although normal navigation could. This hid already observed potion rewards behind doors 444/520 while a crystal key was held. Original-source offline bookkeeping reconstruction matched recorded actions 0–312 and reproduced the terminal blocker; this is reconstructed memory, not recorded memory. A focused correction makes branch valuation admit ordinary closed-door transit under the existing safety checks. The new regression failed on original source and passed with the correction; all 1,768 suite tests passed, with four skipped. Candidate reconstruction first changed decision 265 (log line 828), selecting an approach to the crystal branch; reconstruction stopped there. This establishes an available preparation choice, not potion acquisition, identity, gas-room success or survival.

## Recommendations

- **000072-remote-crystal-supply — Keep ordinary closed transit doors from hiding observed crystal-room supplies.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 109, log line 306: potion rewards observed beyond crystal door 444.; Decision 265, log line 828: first changed selection in the isolated candidate reconstruction.; Decision 313, log line 970: mandatory discovery blocked by missing room supplies despite a held crystal key.; tools/room_tactics.py:547-604; tools/survival_policy.py:431-463.
  - Disposition: implemented

## Lessons for the next run

Evaluate observed crystal-room rewards through ordinary closed transit doors before abandoning a held key. Keep supply conservation, fresh potion-test safety checks, actual protection verification and pickup receipts separate: choosing a supply approach is not completing the puzzle.

Update: **accepted**.
