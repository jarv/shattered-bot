# ShatteredAI run 000256

Played commit: `432b1fdfbc15de027877262fcb1f3dacd7c26239`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Treat a protected reward route and an observation approach as separate from executable potion preparation. Before returning repeatedly, establish a jointly feasible test bank, isolated storage route and fresh-arrival handoff. Preserve mandatory pickup, unknown identities, hazard checks and explicit planner exhaustion.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. At decision 365 (logs 1016–1017), potion preparation selected a return toward remembered bank 272 through doorway 218. Decision 366 (logs 1020–1021) abandoned that journey for nearby water 217; decision 367 returned through the doorway again. Changing visibility made the reactive choices alternate, eventually triggering navigation-loop recovery and the terminal stop at decision 421 (logs 1225–1227). Offline reconstruction matched the original selections through decision 366; the candidate first differs there and was not advanced using later observations. The proposed correction retains the admitted observation journey while rechecking its existing safety and resource gates. A new regression fails on original source and passes on the candidate; the full suite passes 2,417 tests with four skipped. This establishes continued preparation selection, not successful identification, collection, descent or improved survival.

## Recommendations

- **000256-discovery-return-commitment — Preserve an admitted potion-preparation return instead of reversing toward briefly visible water.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 365, logs 1016–1017: return toward bank 272 enters doorway 218.; Decision 366, logs 1020–1021: fresh water preference reverses to 217.; Decision 367, logs 1023–1024: preparation returns through the doorway again.; Decision 375, log 1051: navigation-loop detection.; Decision 421, logs 1225–1227: planner exhaustion with a living hero.; tools/descent_potions.py:92–157,306–496; tools/mage_policy.py:1298–1304.
  - Disposition: implemented

## Lessons for the next run

Keep an admitted preparation-area return committed across doorway observations. Recheck each movement and require fresh bank and inventory-protection admission on arrival; remembered feasibility never authorizes drinking or collection credit.

Update: **accepted**.
