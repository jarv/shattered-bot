# ShatteredAI run 000186

Played commit: `bf34548c232a555c939f00767cdd8f38cdb6f4a4`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- On the return from a gas room, the bot can take a short, freshly observed dry detour around an occupied square to the same safe bank, provided its remaining gas protection covers the trip.

## Incoming learnings

A protected return should not insist on an occupied waypoint when a freshly observed dry detour reaches the same bank within the actual immunity budget. Recheck each subsequent observation; never reuse the earlier empty destination after a new enemy appears, invent collection, or replace planner exhaustion with waiting.

## Analysis

The hero remained alive at 30/30 HP when planning stopped. D362 and D392 (log lines 1041 and 1124) observed an upgrade scroll behind eternal fire. D371 used the bounded puzzle meal; D372-375 guessed frost for golden unsuccessfully, and D391 tested golden without clearing the fire. Later bistre potions remained unidentified. At D689 (lines 2001-2003), the scroll was still blocked by the fire safety buffer, while the hungry hero carried usable intuition and bistre x2. The selecting chain reaches priority_resources.choose and puzzle_supplies.prepare_supplies: its hungry information-action exception allowed gas but not frost, then the hunger veto excluded further preparation. Exploration proposed descent, correctly rejected by the mandatory progression guard. The correction extends only that guarded stationary intuition exception to frost, with a new reduced public-evidence regression. Baseline: two expected assertion failures; candidate: three tests pass; full suite: 2081 tests pass, four skipped. This is not a recovered complete runtime state or a gameplay replay. It establishes an available information action, not bistre identity, successful fire removal, collection, or improved survival.

## Recommendations

- **000186-hungry-frost-information — Allow guarded frost intuition while hungry before declaring mandatory pickup planning exhausted.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D362, log line 1041; D371-375, log lines 1066-1075; D391-392, log lines 1121-1124; D624, log line 1815; D688-689, log lines 1998-2003
  - Disposition: implemented

## Lessons for the next run

Hunger restrictions on unknown potion drinking must not exclude a separately guarded intuition hypothesis for an observed fire barrier. Track each floor, room type and color independently; a failed golden guess says nothing about bistre. Require public identification, safe extinguishing and actual pickup evidence afterward.

Update: **accepted**.
