# ShatteredAI run 000077

Played commit: `32a178410156514f86cc72c6da887a7789057a05`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now remembers scouting a gas-room entrance even if toxic gas forces it back and the door closes again. It can then prepare known protection from clear ground instead of repeating the unprotected scout.

## Incoming learnings

An observed entrance remains scouted when its ordinary door recloses. Use that observation to prepare known protection from clear ground, never to assume a buff or reward. Separately validate terminal supply obligations and protected gas-controller arbitration before claiming retrieval or descent success.

## Analysis

The run ended with a living hero at full health, not an observed death. The initiating terminal-episode bug was contradictory stair-pickup handling. Decision 1228 (accepted transition, log line 3755) reached an ordinary square adjacent to visible mystery meat on the exit. Decision 1229 (soft failure, line 3757) explicitly selected that fresh heap for collection, but the final guard rejected it as an unplanned descent. Recovery moved away instead. Repeated reobservation and recovery eventually exhausted the hungry planner; decision 1312 healed to full health before terminal decision 1313 (lines 4043–4044). The clock advanced. Pinned game source selects ordinary heap pickup before transition handling when enemies do not suppress pickup. The proposed correction narrowly recognizes an already admitted, fresh adjacent LOOT interaction rather than treating it as descent. It preserves threat checks, unplanned-transition rejection, mandatory progression pickup, collection receipts and terminal exhaustion. A new reduced public-evidence fixture fails by assertion on original policy and passes on the candidate; all 1779 Python tests pass, with four skipped. This is selector/wrapper validation, not reconstructed runtime memory or proof of subsequent collection or descent. Historical backlog episodes were not revalidated. Policy and regression changes are supplied separately for trusted extraction; files is intentionally empty.

## Recommendations

- **000077-stair-pickup-admission — Allow an admitted fresh adjacent stair-heap pickup through the final transition guard without admitting ordinary stair transit.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1228, accepted transition at log line 3755: arrival beside the exit heap advances time and restores one HP.; Decision 1229, soft failure at log line 3757: the selected fresh stair-heap pickup is rejected as unplanned-stairs.; Decisions 1311–1313, log lines 4038–4044: reobservation and healing precede living planner exhaustion with the heap still visible.; tools/region_navigation.py:121–137; tools/mage_policy.py:411–431; pinned Hero.java:1965–1998.
  - Disposition: implemented

## Lessons for the next run

Distinguish fresh adjacent heap pickup from actually using the stairs. Preserve the existing threat and observation requirements, and require an accepted collection receipt before considering the heap finished. Choosing this interaction does not establish collection or subsequent descent success.

Update: **accepted**.
