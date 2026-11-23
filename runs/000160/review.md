# ShatteredAI run 000160

Played commit: `1efb313771b75c306f32deb0f8f648f29fd48aa2`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- If a trial potion fails to grant the needed protection, the bot now abandons the unstarted room trip before checking its route. Recovery movement no longer makes that failed experiment look like a displaced protected journey.

## Incoming learnings

Check whether experimental protection actually appeared before treating a dry-run route as an active journey. Failed-effect recovery can legitimately leave that route. Keep mandatory progression loot pending and retain hazard vetoes; electrical traps near water need a separately verified clearing and expiry plan, not a cold-trap shortcut.

## Analysis

The hero was alive at full health when planning exhausted. A distant well first observed at decision 68 became a missing levitation reservation. At decision 208, that optional drop preparation blocked mandatory strength discovery, although the drop controller requires verified feather fall or cleansing rather than levitation alone. All preparation providers declined. Offline reconstruction matched recorded actions and reasons through decision 207 and reproduced the terminal blocker. The proposed narrow correction separates optional well preparation from the unknown-color discovery veto while retaining known-supply reservations, unfinished-room reporting, hazard checks and mandatory progression pickup. The new six-test regression fails on the original policy and passes on the candidate. Complete per-file isolated suite validation ran 2015 tests with four skips and no failures; the single-process attempt was killed. This does not resolve the entire terminal state: an isolated alternative probe still found no admitted discovery-bank return. No changed action was dispatched or followed with invented observations.

## Recommendations

- **000160-optional-well-discovery — Separate optional distant-well preparation from mandatory unknown-potion discovery.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 68, log line 200: distant well 309 is publicly observed.; Decision 207, log lines 610–612: accepted movement from 426 to 427.; Decision 208, log lines 613–614: missing fall supply blocks discovery with the hero alive at 25/25 HP.; tools/puzzle_supplies.py:83–84; tools/room_supplies.py:31–46; tools/drop_tactics.py:30–49; tools/descent_potions.py:344–378.
  - Disposition: implemented
- **000061-descent-bank-return — Reserve mandatory discovery preparation before exploration disconnects every admitted bank return.** (high, deferred): Not addressed by the single reservation correction. Historical feasibility does not establish a currently safe transit route or fresh arrival admission, and the existing bank-return provider declines. Next derive a decision-208 fixture from the validated state, enumerate each historical bank's transit exclusions, and establish a funded allowed-graph return with fresh visibility and inventory-protection checks. No safe movement replacement is certified.
  - Evidence: Decision 208, log line 613: the recorded terminal observation has no immediately admitted discovery bank.; Validated offline reconstruction through decision 207 retains earlier witnessed bank receipts.; An isolated decision-208 probe without the optional fall veto still rejects remembered-bank return and reconnaissance.
  - Disposition: deferred

## Lessons for the next run

An optional distant-well project must not monopolize unidentified potions needed for mandatory discovery. Keep its protection and loot unfinished until verified. Removing that contradictory reservation does not prove that a safe preparation bank can currently be reached.

Update: **accepted**.
