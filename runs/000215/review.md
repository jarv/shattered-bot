# ShatteredAI run 000215

Played commit: `8b905d1d19838154e3511e52aaa4e6209591a762`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- After defeating Tengu, the bot now rechecks visible closed doors even if it crossed them earlier. It still uses its normal movement and loot checks before approaching them.

## Incoming learnings

A boss victory can replace the map without changing a previously crossed door's terrain value. Treat freshly observed closed doors as new work once after confirmed final Tengu victory, while preserving reward pickup and all existing movement safety checks. Selecting the route is not evidence of crossing it or reaching the exit.

## Analysis

The hero remained alive at 26/30 HP when mandatory potion preparation exhausted. Decision 687, log lines 2026–2028, identifies missing frost for the observed fire barrier. Hungry room testing was excluded, the puzzle meal required near-full health, and stationary recovery had no budget. Descent correctly remained blocked; no recovery action was accepted. Earlier, decision 665 spent an intuition stone on crimson after fire had been observed at decision 626. Decision 668 confirmed a strength hypothesis and received an incorrect result. The generic information fallback ignored the missing frost prerequisite. The proposed correction prioritizes that recognized frost hypothesis without changing when the stone may be used, guessing an effect, or permitting drinking or hazard entry. A new reduced public-evidence fixture fails on the original strength default and passes on the correction; all 2194 tests pass with four skips. This fixture reconstructs only minimal remembered fire, not the original full runtime state. Neither crimson's identity nor resolution of the terminal recovery contradiction is established.

## Recommendations

- **000215-frost-intuition-priority — Prioritize the recognized missing frost hypothesis in an already admitted generic intuition action.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 626, log line 1847: green fire is publicly observed.; Decision 664, accepted log line 1962: crimson potion is collected.; Decisions 665–668, log lines 1964–1971: intuition selects strength and the hypothesis fails.; Decision 687, log lines 2026–2028: missing frost blocks mandatory discovery.; tools/runestone_tactics.py:103–128; tools/mage_policy.py:1342,1413.
  - Disposition: implemented
- **000215-frost-recovery-handoff — Establish executable recovery before hungry, wounded frost preparation exhausts mandatory discovery.** (high, deferred): The separate terminal handoff is not repaired. Existing helpers lack an admitted food/healing-to-testing transaction: meal admission requires 95% HP, hungry testing declines, and stationary recovery is unfunded. Lowering either threshold would not prove safe preparation. Next derive paired terminal-state and full-health/fed public-map fixtures, preflight a bounded known-resource recovery chain through bank and inventory protection admission, and verify accepted recovery receipts before changing scheduling. Preserve the unknown-drink health threshold and mandatory pickup.
  - Evidence: Decision 687, log lines 2026–2028: hungry hero at 26/30 HP retains two rations, but missing frost preparation exhausts with no recovery inputs.; tools/puzzle_supplies.py:727–754,776–803,879–880.; tools/recovery_economy.py:8–19; tools/descent_potions.py:350–392.
  - Disposition: deferred

## Lessons for the next run

Use already admitted identification opportunities to investigate recognized missing puzzle supplies before unrelated default guesses. An incorrect strength guess does not identify frost. Keep hungry recovery planning separate from unknown-drink admission, and retain mandatory discovery and pickup obligations.

Update: **accepted**.
