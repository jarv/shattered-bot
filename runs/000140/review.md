# ShatteredAI run 000140

Played commit: `67eff0d05b460d4283bbcc30300d891255d6caf0`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When preparing to test a potion beside a fire barrier, the bot now approaches through the same ordinary corridor used for potion storage rather than taking a shortcut through a door. It still checks the testing spot again on arrival.

## Incoming learnings

A shortest route to an admissible preparation bank can invalidate its own visibility prerequisites. Prefer the already admitted ordinary stash corridor, then recheck the bank and inventory protection on arrival. An alternative preparation selection does not establish puzzle success or waive unfinished loot.

## Analysis

The living hero exhausted mandatory potion discovery, not combat: decision 352 (log line 947) stopped at 25/25 HP after decision 351 advanced the clock to turn 351 (accepted line 945). The initiating contradiction is that exploration can leave the admitted preparation-return graph before discovery is allowed to start. Decisions 349–351 move from water 802 through grass 759 and 716 to floor 673 (selection lines 938, 941, 944). At the terminal position, every historical bank return is disconnected by excluded grass 716/759. Source-pinned offline bookkeeping reconstruction matched all 352 recorded actions and reasons, decisions 0–351, and reproduced the terminal blocker. This is reconstructed state, not recorded memory. Seven reconstructed bank receipts cover the exact current indigo-plus-liquid-flame inventory; nearby banks 931, 845 and 888 therefore fail transit, not inventory matching or the distance bound. The selecting chain is tools/mage_policy.py:358–495, tools/descent_potions.py:266–294,403–452,103–149. Return transit excludes grass; fresh bank checks also require visible safe surroundings and inventory protection. Both return and reconnaissance prerequisites decline. The terminal inventory has no known mapping or clairvoyance resource; indigo remains unidentified. No policy or regression patch is supplied. Complete source and reconstruction resolve the packet's bookkeeping gap, but not the safety of an early preparation transaction. Broadening grass admission would weaken the existing safety filter; starting discovery earlier would bypass the deliberate pre-descent conservation/progression contract unless unfinished exploration and collection are retained and resumed. The concrete next repair is a bounded preparation reservation before the second grass step, tested with paired decisions 350/351, actual accepted transit/drop/effect/retrieval receipts, fresh arrival checks and restoration of the unfinished frontier objective. An isolated return proposal alone would not establish safe discovery or puzzle completion.

## Recommendations

- **000061-descent-bank-return — Reserve mandatory discovery preparation before exploration disconnects every admitted bank return.** (high, deferred): Revalidated in this recording. No safe focused patch is certified: terminal return requires crossing excluded grass 716/759, while an earlier drink must preserve the existing pre-descent supply/progression gate and resume the unfinished frontier and collection work. Complete source and reconstruction resolve missing selector state, not this transaction safety contract. Next derive paired decision-350/351 fixtures and validate a bounded preparation reservation before disconnection, with accepted movement/drop/consumption/retrieval receipts, interruption handling, fresh bank/stash admission and restoration of unfinished exploration. Do not allow grass, increase bounds, infer potion effects or waive pickup.
  - Evidence: Decision 349, selection line 938: exploration leaves water 802 for grass 759.; Decision 350, selection line 941 and accepted line 942: exploration moves from grass 759 to grass 716.; Decision 351, selection line 944 and accepted line 945: exploration reaches 673 alive at full health.; Decision 352, line 947: both preparation prerequisites decline and mandatory discovery exhausts.; Offline reconstruction matches decisions 0–351 and the terminal blocker; seven exact-inventory bank receipts remain, but all terminal returns are excluded.; tools/descent_potions.py:103–149,266–294,403–452; tools/mage_policy.py:445–495; tools/test_floor_potion_reservation.py:55–64.
  - Disposition: deferred

## Lessons for the next run

Exploration and mandatory discovery must share a preparation reservation: a remembered safe bank is insufficient once exploration disconnects every admitted return. Preserve unknown identities, potion protection, fresh arrival checks and all unfinished pickup obligations; do not solve this by allowing grass or restoring idle waits.

Update: **review-only**.
