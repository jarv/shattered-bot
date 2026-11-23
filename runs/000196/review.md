# ShatteredAI run 000196

Played commit: `74c9f26007467c97e9ca28dddff409c9dd06c754`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a slime after prolonged fly pursuit and multi-enemy pressure

## Improvements since the last run

- The bot now cancels an unstarted protected-room trip when a failed potion test leaves it outside the planned route. It still requires protection and a verified return once the hero enters the route or room.

## Incoming learnings

Separate an unstarted protection hypothesis from an actual protected trip. Failed potion-effect recovery can leave the staging bank without creating a protected return obligation. Keep unresolved rewards and mandatory discovery honest; never infer potion identities or waive return safety. Stop offline continuation at the first changed selection.

## Analysis

The full terminal observation explicitly says a slime killed the hero (decision 1382, accepted log line 4071); this resolves the compact packet’s unknown attribution. The earlier failure was prolonged fly pursuit, not the final melee alone. With the staff empty, decisions 1288–1289 used a physical throw and two fly swarms were then observed. Retreat began at decision 1290. Accepted pursuit reached 12 moves at decision 1303 (line 3732), yet preparation returned early whenever multiple fronts needed retreat, bypassing its pursuit-outcome review. This left new, unverified doorway setups eligible; decision 1304 selected another setup, and decision 1331 began one after 39 accepted retreat moves. Later the hero reached doorway 412 without a verified hold, fought under multiple threats, withdrew at low health and died. Source-pinned offline bookkeeping reconstruction matched all 1,383 original selections, including action, reason, intent and controller. It is reconstruction, not recorded policy memory. The proposed ordering correction runs the existing pursuit review before the emergency-retreat yield, without changing its thresholds or movement admission. Candidate reconstruction matched decisions 0–1303, then selected an already-admitted ordinary retreat at decision 1304 instead of another unverified doorway setup; investigation stopped there. The new three-test regression failed by assertion on original source and passed on the candidate. The full suite passed: 2,146 tests, four skipped. This establishes the bookkeeping repair, not escape, improved survival or prevention of the earlier fly split.

## Recommendations

- **000196-pursuit-review-starvation — Run accepted-pursuit outcome review before emergency retreat preempts preparation.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1289, accepted log line 3665: physical fly attack is followed by two observed swarms.; Decision 1303, log line 3732: accepted pursuit reaches 12 retreat moves.; Decision 1304, selection log line 3733: another unverified doorway setup remains eligible.; Decision 1331, selection log line 3868: a new doorway setup begins after 39 accepted retreats.; tools/mage_policy.py:1111–1131; tools/pursuit_budget.py:138–151; tools/multi_enemy_tactics.py:229–235.
  - Disposition: implemented

## Lessons for the next run

Review accepted pursuit outcomes before yielding preparation to emergency retreat. Retiring unverified doorway setups must leave existing hazard-filtered retreats and verified holds available. Do not infer that a changed retreat resolves pursuit or prevents death; stop offline continuation at the first changed selection.

Update: **accepted**.
