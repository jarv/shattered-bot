# ShatteredAI run 000075

Played commit: `732100b919cc1e731a07d873c4a0387652bbcd77`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- If a piranha blocks the next step toward a protected chest, the bot now looks for a visible, safe detour that does not lengthen the trip. It keeps the same reward and return bank.

## Incoming learnings

Distinguish temporary occupied waypoints from failed protection preparation. Revalidate a bounded protected route before abandoning its mandatory chest, preserving the same bank, observed protection budget and actual pickup receipts. A selected bypass is not evidence that the puzzle was completed.

## Analysis

The living hero exhausted the planner, rather than dying. Decision 315's accepted entrance move (log line 901) revealed a sentry. Decision 316 spent a puzzle-backed meal, but neither potion identification nor usable room geometry followed. Decisions 321–323 explored the admitted grass strip and collected a seed; the final accepted action (line 924) advanced turns 317 to 318 at 25/25 HP. Decision 324 (line 926) stopped because mandatory potion discovery would risk supplies reserved for the unfinished sentry room. The initiating problem is missing observation/identification preparation: room testing requires a verified protected reward trip, but the enclosure and reward remain incompletely observed. Source-pinned offline bookkeeping reconstruction matched all 324 selected actions, reasons and intents, then reproduced the terminal blocker. Isolated copied-state probes found no admitted sentry test bank or protected journey origin. The public inventory held two unidentified singleton potions, no known haste and no identification resource. Their effects cannot be inferred from color. Relevant gates are tools/room_tactics.py:148–184, tools/puzzle_supplies.py:343–375,642–684, tools/descent_potions.py:186–194, and tools/mage_policy.py:416–470. No patch or new regression is supplied: complete source resolves the selecting-state gap but does not establish a safe replacement action. Guessing unseen geometry, crossing exposed flooring, or testing elsewhere and potentially wasting the required haste would bypass safety. The unchanged Python suite passed 1773 tests with four skipped; this is not red/green validation of a repair.

## Recommendations

- **000075-sentry-observation-preparation — Establish safe observation or identification preparation before incomplete sentry geometry exhausts mandatory discovery.** (high, deferred): No safe focused repair is established. The exact blockers are unobserved enclosure interior/perimeter and reward, no admitted sentry test bank, and no known haste or carried identification resource. Complete selecting source and reconstruction resolve the memory gap, not those safety prerequisites. Next, derive a deterministic fixture from decision 321 and inspect the pinned sensing and grass/obstacle rules for a bounded observation-only action from the admitted entrance strip. Require evidence that it reveals the missing geometry without exposed-floor entry before adding preparation arbitration and a red/green regression. If that contract cannot be established, pursue a public identification-resource plan instead. Do not guess potion effects, waive mandatory pickup, or restore death-waits.
  - Evidence: Decision 315, accepted transition at log line 901: entrance observation precedes recognition of the sentry.; Decision 316, log lines 903–904: a puzzle meal advances time without establishing protection or identification.; Decisions 321–323, accepted transitions at lines 918, 921 and 924: exploration finishes the admitted grass strip while health remains full.; Decision 324, log line 926: missing recognized-room supplies block mandatory discovery.; Offline reconstruction matches all 324 selected actions, reasons and intents; copied-state probes find no admitted test bank or sentry journey origin.
  - Disposition: deferred

## Lessons for the next run

Recognizing a sentry room is not enough to authorize a potion test or retrieve its reward. Separate safe observation preparation from protected retrieval, and require public evidence for both. Full health and a puzzle meal do not resolve missing geometry or unknown potion identities.

Update: **review-only**.
