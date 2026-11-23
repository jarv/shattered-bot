# ShatteredAI run 000214

Played commit: `6352e6e42b7d78886e238943e736d8595fdef79b`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When toxic gas blocks every observed escape, the bot can throw an identified potion of purity at its own safe tile to clear the cloud. It still refuses unknown potions and unsafe impact tiles.

## Incoming learnings

When gas escape routes are exhausted, consider an identified purity self-splash on a verified safe impact tile before declaring planner failure. Reobserve the result; never infer clearance, protection or collection from selecting the action. Unknown rooms must not be judged using later revelations.

## Analysis

The hero remained alive at 26/80 HP when the planner stopped. The initiating defect was stale door bookkeeping after Tengu's final arena replacement. Door 746 had already been crossed at decisions 4489–4490 (accepted log lines 13133 and 13135). Decision 4586's accepted transition (line 13391) records the defeat and relocation; decision 4587 observes the same door closed and visible. The bot correctly collected the mask in decisions 4587–4588, but decision 4589 reported no unopened doors and exhausted planning (lines 13398–13399). The door retained the same closed terrain value, so the terrain-change refresh missed it, while historical visits excluded it from exploration. The pinned game source confirms final victory replaces this map. A focused correction rearms publicly observed closed doors once on confirmed final victory, retaining normal route, hazard, failed-movement and pickup checks. A reduced evidence-derived fixture, not recovered runtime memory, fails with two expected assertions on original policy and passes all five tests with the correction. No gameplay was replayed. This establishes door admission, not successful exit discovery, descent or survival.

## Recommendations

- **000214-tengu-victory-door — Rearm observed closed doors after final Tengu victory even when their terrain value is unchanged.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 4489–4490, accepted log lines 13133 and 13135: door 746 is crossed.; Decision 4586, accepted log line 13391: final defeat relocates the hero and reveals the mask reward.; Decision 4587, log line 13392: reused door 746 is closed and visible.; Decisions 4587–4588, accepted log lines 13393 and 13396: reward pickup precedes exhaustion.; Decision 4589, log lines 13398–13399: no unopened doors admitted; living hero cannot proceed.; tools/survival_policy.py:340–355,878–879,1105–1109; tools/boss_strategies.py:TenguStrategy.victory.
  - Disposition: implemented

## Lessons for the next run

A boss victory can replace the map without changing a previously crossed door's terrain value. Treat freshly observed closed doors as new work once after confirmed final Tengu victory, while preserving reward pickup and all existing movement safety checks. Selecting the route is not evidence of crossing it or reaching the exit.

Update: **accepted**.
