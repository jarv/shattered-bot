# ShatteredAI run 000216

Played commit: `64c184a376a60df98caa6d4cf724bcd9a360a447`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died fighting Tengu

## Improvements since the last run

- When magical fire still requires frost, the bot uses an already available intuition test to investigate frost rather than defaulting to strength. This does not identify the potion unless the test confirms it.

## Incoming learnings

Use already admitted identification opportunities to investigate recognized missing puzzle supplies before unrelated default guesses. An incorrect strength guess does not identify frost. Keep hungry recovery planning separate from unknown-drink admission, and retain mandatory discovery and pickup obligations.

## Analysis

The hero died during the Tengu fight. Decision 4623's accepted transition (log line 13393) records 7 to 0 HP and explicitly names Tengu in the death message; the exact final attack is not established. An earlier actionable defect is missing Shocker hazard recognition: at decision 4564 (13199), a described Shocker is diagonally adjacent, but the current tile has no effect and the bot starts another attack. The following target receipt (13202) leaves the hero stationary and reduces HP from 75 to 66, without uniquely identifying that damage source. Decision 4577 (13230) similarly holds beside another Shocker. The played Tengu telegraph helper models smoke bombs, but not the electrical machine's alternating radius-one footprint. The pinned game source establishes that footprint without requiring hidden orientation. A reduced public-evidence fixture and an isolated complete-snapshot helper probe reproduce the missed escape; these are not recovered original runtime memory or a replay. The proposed correction adds conservative Shocker avoidance to the existing boss escape checks and prevents bomb countdowns from authorizing electrical transit. Original-source regression: three expected assertion failures; candidate: four tests pass. The full Python suite passes 2,198 tests with four skips. This establishes local hazard recognition, not survival, boss victory, or a general repair of exhausted-combat fallback movement. No planner incidents were recorded; historical backlog items were not revalidated.

## Recommendations

- **000216-tengu-shocker-footprint — Recognize rotating Shocker exposure before attacking or holding beside it.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 4564, selection line 13199: adjacent Shocker with empty current hero effects and no rendered danger; attack selected.; Decision 4565, accepted transition line 13202: stationary attack reduces hero HP from 75 to 66.; Decision 4577, selection line 13230: bounded hold beside an observed Shocker.; tools/boss_strategies.py:390-440; tools/policy_nodes.py:71-82; pinned Tengu.java:975-1030.
  - Disposition: implemented

## Lessons for the next run

Treat a publicly described Shocker and all adjacent cells as electrical exposure even between visible pulses. Use existing checked escapes rather than waiting for damage to reveal the next orientation. Keep electrical exposure separate from smoke-bomb countdowns, and retain explicit refusal when no admitted immediate escape exists.

Update: **accepted**.
