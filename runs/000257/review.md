# ShatteredAI run 000257

Played commit: `8acc179d31e0d08c5959656d9b3fd0aab3ed569a`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died under multi-enemy pressure after a recovered planner failure

## Improvements since the last run

- The bot now keeps returning to its chosen potion-preparation area even when opening a door reveals another possible testing spot. It still rechecks the route and requires fresh safety checks before drinking.

## Incoming learnings

Keep an admitted preparation-area return committed across doorway observations. Recheck each movement and require fresh bank and inventory-protection admission on arrival; remembered feasibility never authorizes drinking or collection credit.

## Analysis

The hero died under sustained multi-enemy pressure; an unambiguous killer is not established. An earlier planner failure is independently important. D1304 activates known purity, D1305–1308 begin protected collection, and D1309–1311 emergency gas escape interrupts that work. Reward 1007 receives collection credit, while chest 1036 and remains 915 remain unfinished. D1341–1347 and D1438–1447 show preparation returning to approach 980 while exploration leaves it. D1448 records navigation-stalled exhaustion with the hero alive at full health. Recovery actually descends at D1469 after 22 accepted actions, without collection credit; this is not a planner repair. Source inspection exposes a candidate initiating mismatch: toxic_escape.escape recognizes owned protection only on journey.route, whereas protected_rewards.RewardTrip dynamically tours its room. The reobservation helper also retries a preferred approach without an unsuccessful-arrival receipt. Original mutable journey and admission bookkeeping have not been reconstructed and validated, so neither expanded ownership nor suppressed revisits has been certified to select a safe continuation. No patch or new regression is supplied. Unknown potion effects remain unknown.

## Recommendations

- **000257-gas-tour-continuation — Establish a verified protected gas-tour continuation and prevent unsuccessful approach arrivals from repeatedly reversing exploration.** (high, deferred): Complete source resolves the selecting-chain gap, but original mutable tour state and a certified replacement remain missing. Escape checks a static route while adaptive tours operate within their room; later reobservation does not prove fresh testing, storage or reward-return admission. Next reconstruct and validate selected inputs through D1308, inspect D1309 route ownership and observed immunity, and derive a regression proving delegation to unchanged funded-return checks. Then derive the arrival-at-980 fixture and demonstrate an admitted progress action before suppressing retries. Do not expand hazard admission, extend bounds, infer protection or collection, or waive mandatory pickups.
  - Evidence: D1304–1311, log lines 4094–4115: known purity activation, partial collection and emergency escape.; D1341–1347, log lines 4190–4210: gas approach and exploration alternate.; D1438–1448, log lines 4494–4526: repeated reversals end in navigation-stalled planner failure.; D1469, log lines 4654–4655: actual recovery descent after 22 accepted actions, without collection credit.; tools/toxic_escape.py:23–44; tools/protected_rewards.py:191–280; tools/puzzle_supplies.py:457–508,1021–1068.
  - Disposition: deferred

## Lessons for the next run

Investigate the protected gas-trip interruption before its eventual fallback. Validate adaptive tour ownership, actual immunity and a funded return on paired public observations; arrival at a remembered testing approach does not establish executable preparation.

Update: **review-only**.
