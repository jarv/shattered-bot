# ShatteredAI run 000252

Played commit: `d7e401c6202b8826b9ce859e51aa0129a09e531e`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When a prolonged chase exhausts its lure budget, the bot can reconsider a limited wand shot even while healthy. It still checks enemy contact, cover, hazards and the shot’s path.

## Incoming learnings

Healthy HP does not establish that prolonged pursuit is making progress. When accepted pursuit exhausts its lure budget, permit the existing bounded known-charge reassessment without weakening contact, sight-break, hazard or projectile checks. Keep unseen potion identities and unfinished progression loot unresolved.

## Analysis

The recording ends in planner exhaustion, not death: decision 284 leaves the hero at full health and accepts no recovery action. Decision 279 spends the last crystal key on one chest; decision 280 observes the opened chest and missing key. The bot correctly recognizes the other chest as the unavailable alternative, but still counts it as an unreachable reward near a dart trap. That false flight requirement prevents mandatory potion discovery. The selecting chain runs through tools/keyed_rooms.py, tools/puzzle_supplies.py, tools/room_supplies.py and tools/descent_potions.py. Offline reconstruction from the pinned source and public observations matches every action through decision 283 and reproduces the original blocker. The proposed correction excludes only receipted crystal alternatives from flight-demand recognition, without claiming collection or changing hazard checks. The new regression fails on the original policy and passes on the candidate; the full suite passes 2406 tests with four skipped. On a validated terminal-state copy, the candidate selects the existing bank-reobservation route instead of exhausting. No action was dispatched and no observations after that changed decision were supplied. This establishes a preparation handoff, not successful testing, puzzle completion or descent.

## Recommendations

- **000252-resolved-crystal-flight — Exclude receipted crystal alternatives from flight-demand recognition so they cannot block mandatory potion discovery.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 279, log lines 781–782: last crystal key spent on chest 1039.; Decision 280, log line 784: opened ring chest, no key, other crystal chest still closed.; Decision 284, log lines 793–795: false missing-flight prerequisite and mandatory-preparation planner exhaustion.; tools/keyed_rooms.py:78–93; tools/puzzle_supplies.py:137–141; tools/descent_potions.py:350–392.; Offline reconstruction matches decisions 0–283; isolated candidate terminal selection admits existing bank reobservation.
  - Disposition: implemented

## Lessons for the next run

Unavailable crystal-choice alternatives must not reserve flight supplies after the last-key spend is publicly verified. Keep their loot uncollected, reopen eligibility when a new key is observed, and preserve reservations for independent mandatory rewards. Unknown potion colors remain unknown until observed identification.

Update: **accepted**.
