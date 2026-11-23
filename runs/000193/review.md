# ShatteredAI run 000193

Played commit: `61c5bc7fb283444dd6e2143223cd166e963224b8`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

Code changed; no supported improvement summary available.

## Incoming learnings

Before committing to a doorway against flying pursuers, use already observed geometry to rule out doors with no viable holding square. Keep unknown-side reconnaissance distinct from verified refuge, preserve mandatory pickups and hazard gates, and do not equate a corrected plan with successful escape.

## Analysis

The living Mage stopped because mandatory strength discovery reserved an unidentified haste supply for an unfinished sentry room, while every preparation prerequisite declined. Decision 314 observes the sentry and spends a puzzle meal; decision 319 observes Chest 1004 but withdraws. Decision 341 exhausts preparation at full health, not an observed death. Offline bookkeeping reconstruction on the played source matches all 341 earlier selections and reproduces the terminal blocker. The enclosure still lacks boundary observations at 1051, 1084 and 1090. Ordinary scouting cannot reach a useful vantage: statue 965 and the unopened chest separate the lower safe pocket, while defended carpet remains excluded. No carried identification or reveal resource is available. No patch is supplied because neither an admitted observation route nor a safe protected alternative is established; adding grass transit alone also fails an isolated copied-state probe. The source chain is tools/room_tactics.py:179–215, tools/puzzle_supplies.py:967–1000, tools/preparation_prerequisites.py:65–146 and tools/descent_potions.py:begin/advance. Nine existing reconnaissance tests pass, but there is no candidate red/green or full candidate-suite claim. The truncated executable source comparison does not support attributing additional viewer-facing improvements.

## Recommendations

- **000184-sentry-geometry-preparation — Resolve sentry preparation when missing perimeter observations lie beyond a statue-separated safe pocket.** (high, deferred): Complete source and reconstruction resolve the selecting-memory gap, but not replacement safety. Missing boundary cells 1051, 1084 and 1090 have no qualifying reachable ordinary observation vantage. Statue 965 and unopened Chest 1004 separate pocket 1043–1044; defended carpet cannot be used as unprotected transit, and no known identification or reveal supply is carried. Next derive paired decision-319/341 fixtures and validate an observation-and-return transaction without carpet, statue or unopened-chest transit. If protection is necessary, first establish a conservative actual-buff-funded reconnaissance contract without inferring missing walls or potion identities. Merely returning, eating again, increasing limits or admitting high grass does not establish this repair.
  - Evidence: Decision 313, log lines 882–884: accepted entrance approach to 848.; Decision 314, log lines 885–886: sentry observed and puzzle meal consumed.; Decision 319, log lines 899–901: Chest 1004 observed from 926; exploration withdraws.; Decision 340, log lines 962–964: accepted movement advances the game clock.; Decision 341, log lines 965–967: missing haste exhausts all preparation prerequisites with the hero alive.; Source-pinned offline reconstruction matches selections 0–340 and reproduces the terminal blocker.
  - Disposition: deferred

## Lessons for the next run

Distinguish a route back to a sentry entrance from an observation route that can actually reveal its missing perimeter. A meal and a known chest do not establish preparation feasibility. Preserve unknown potion identities, defended-carpet exclusions, mandatory pickups and explicit planner exhaustion.

Update: **review-only**.
