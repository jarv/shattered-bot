# ShatteredAI run 000244

Played commit: `514e7ce2a4cf542c7218e18464f151f361225fda`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now discards an old great-crab doorway surprise opportunity when intervening actions have consumed multiple turns. It replans instead of treating the crab's earlier position as a fresh doorway entry.

## Incoming learnings

A doorway entry claim must expire when intervening combat consumes multiple turns; a cached last-seen position is not fresh surprise evidence. Preserve observed second exits and direct-attack restrictions. Separately, inspect crab retreat continuation before choosing room-edge separation over executable exit progress.

## Analysis

Decision 489 approached an unopened door across publicly ordinary floor (log 1431). The accepted move revealed a hidden confusion-gas trap and vertigo, with HP unchanged at 25/25 (log 1432). Decision 490 then exhausted recovery without accepting another action; the final observation still shows a living hero and an unchanged clock (logs 1434–1436). The vertigo controller excludes waiting in renewing gas and rejects its random escape because closed door 1772 is a possible landing. Clear floor 1672 alone cannot certify escape. Source inspection confirms that the door is passable and opens on entry, not a harmless wall bump. A reduced fresh-state probe isolates this rejection but is not recovered runtime memory. No patch is supplied: admitting the door would bypass an existing safety veto without proving containment of the complete pathfinding click, which can continue after an unintended random landing. The public inventory establishes no known purity or transport rescue; the jade potion remains unknown. Existing focused tests passed (23), as did the full suite (2,269 tests, four skipped). These results establish neither a safe replacement nor successful escape.

## Recommendations

- **000244-confusion-door-recovery — Establish a safe, whole-input recovery from confusion exposure beside a closed door.** (high, deferred): Source browsing resolves the selecting chain and door semantics, but not replacement safety. A copied terminal snapshot admits route 1722–1672 only when the closed door is diagnostically normalized; that is not an executable safety proof. The door can open on a random landing, and a normal cell request may continue before another observation. Original mutable threat state is also unrecovered. Next derive paired decision-489/490 fixtures and prove the complete settled-click envelope, including door opening, repeated random attempts, evolving gas and interruption, before adding a positive original-red/candidate-green regression. The existing 000237-vertigo-click-containment backlog remains relevant. Do not remove the door veto alone, change protected API behavior, extend waits, guess the unknown potion or waive mandatory pickup.
  - Evidence: Decision 489, log 1431: destination 1722 is ordinary visible floor before entry.; Decision 489, log 1432: accepted entry reveals confusion gas and vertigo without HP loss.; Decision 490, logs 1434–1436: immediate-safety planner exhaustion, zero accepted recovery actions, living hero.; tools/vertigo_tactics.py:41–112,149–232; tools/test_shattered_vertigo_response.py: all-direction closed-door veto.; Pinned game Terrain.java:90, Char.java:1302–1336 and Hero.java:1014–1031,1808–1914 establish passable door landings and continuing movement requests.
  - Disposition: deferred

## Lessons for the next run

Treat a closed door as a possible vertigo landing that can open sightlines, not as a wall bump. Before changing admission, validate the whole settled cell request, including repeated random movement and renewing gas. Preserve terminal planner exhaustion, unknown-item boundaries and mandatory pickup obligations.

Update: **review-only**.
