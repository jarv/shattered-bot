# ShatteredAI run 000174

Played commit: `84a853a4119f57c4dd022ec9bc95024fe8ec9c9f`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a skeleton after a blocked doorway retreat

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A puzzle-backed meal cannot resolve conflicting reward and movement admissions. Summoning-room preparation must agree with potion reservation, endpoint eligibility and the final movement guard before consuming supplies. A hypothetical flight route is not proof of safe remains interaction, successful collection or survival.

## Analysis

The full public death message confirms a skeleton killed the hero during the final zap. The actionable initiating defect in the last escape attempt precedes that shot: decision 3754 (selection line 10794) chooses door 425 through squares already adjacent to observed skeleton 424. The escape selector pools exposure, so leaving guard 647 offsets entering the different skeleton’s reach. The accepted move reaches 613 with 62 HP; at decision 3755 the route is unreachable and sustained combat follows. Isolated public-scene and reduced-fixture probes reproduce the original route without claiming recovered runtime memory. The proposed correction checks each observed non-DM attacker separately for new and committed door flights. The new regression fails twice as expected on original code and passes all four tests after the fix; the full suite passes 2,048 tests with four skipped. This prevents the evidenced route admission, not proof of a safe replacement or survival. Pre-death unidentified items were not assigned post-death identities.

## Recommendations

- **000174-cross-threat-door-flight — Prevent existing pursuer contact from funding new attacker contact along DM-100 door-flight routes.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3753, selection line 10789 and accepted line 10790: newly observed skeleton blocks the previous door; retreat reaches 646.; Decision 3754, selection line 10794: door-425 route approaches observed skeleton 424 while aggregate exposure remains equal to starting guard contact.; Decision 3754, accepted line 10795, and decision 3755, lines 10798-10800: movement reaches 613, flight becomes unreachable, and combat replaces retreat.; Decision 3766, accepted line 10836: HP falls from 10 to zero; the public death message names a skeleton.; tools/dm100_escape.py:86-94; new four-test regression reproduces original rejection failures and passes with the per-attacker route check.
  - Disposition: implemented

## Lessons for the next run

Do not treat escaping one attacker as permission to approach another along a committed escape route. Recheck opposing observed threats before starting or continuing doorway flight. Rejecting an obstructed route does not establish a safe alternative.

Update: **accepted**.
