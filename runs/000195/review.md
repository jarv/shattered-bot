# ShatteredAI run 000195

Played commit: `cbdf19ec8d0033af6100049fa4dfc693189f2281`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- While retrieving stashed potions, the bot now uses an available clear magic shot against a lone snake before starting a new doorway lure. Existing lures and combat safety checks still apply.

## Incoming learnings

Do not let an optional new snake lure displace owned potion retrieval when an existing charged, permitted clear shot is available. Preserve the stash obligation, unknown potion identities, hazard checks and explicit planner exhaustion. A changed attack choice does not prove collection or eventual progress.

## Analysis

The hero was alive at 30/30 HP when mandatory potion preparation exhausted; this was a bot failure, not a death. The initiating defect occurred earlier: decision 574 (selection line 1651, accepted line 1652) tested a purity hypothesis that instead produced observed cold effects. Decisions 575–581 recovered to cell 595, outside the planned gas tour. At decision 582, line 1669, an unstarted RewardTrip incorrectly demanded a protection-funded return because recovery had left its bank. Line 1670 records the resulting unfinished room obligation. The recovery disables room-journey planning, while mandatory discovery still reserves missing purity for the unfinished gas room. Decision 810, lines 2326–2327, consequently exhausts preparation rather than descending. Source chain: tools/puzzle_supplies.py:983–1035, tools/room_tactics.py:228–287, tools/protected_rewards.py:143–167, tools/mage_policy.py:1408–1435, tools/tactical_recovery.py:47–49, tools/descent_potions.py:350–392. Offline reconstruction on the played source matched original actions and reasons through decision 809; reconstructed tour memory is not originally recorded memory. The candidate first changes decision 582 and no later observations were supplied to that changed state. The focused repair cancels an unstarted, unprotected hypothesis outside its planned route and interior without clearing rewards or disabling their controller. Started tours, interior/route exposure, actual protection return checks, branch checks and mandatory pickup remain enforced. The new five-test regression fails with the expected assertion on original source and passes on the candidate; the full suite passes 2143 tests with four skips. This establishes removal of the false obligation, not successful gas-room collection, strength discovery, descent or survival.

## Recommendations

- **000195-failed-gas-tour-hypothesis — Cancel an unstarted failed gas-tour hypothesis after recovery outside its route instead of disabling room preparation.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 574, log lines 1651–1652: unknown purity hypothesis and accepted consumption.; Decisions 575–581, log lines 1653–1668: observed cold-effect recovery leaves the staging bank.; Decision 582, log lines 1669–1671: false protected-return failure becomes an unfinished room obligation.; Decision 810, log lines 2326–2327: missing purity preparation exhausts with the hero alive.; Source-pinned offline reconstruction matches original selections 0–809; candidate stops at its first divergence, decision 582.
  - Disposition: implemented

## Lessons for the next run

Separate an unstarted protection hypothesis from an actual protected trip. Failed potion-effect recovery can leave the staging bank without creating a protected return obligation. Keep unresolved rewards and mandatory discovery honest; never infer potion identities or waive return safety. Stop offline continuation at the first changed selection.

Update: **accepted**.
