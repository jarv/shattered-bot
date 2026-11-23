# ShatteredAI run 000217

Played commit: `b51c2f2e5e740b47811a9ef42cc7bbcc795f800f`

Outcome: timeout

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Timed out repeating a refused food pickup with the hero alive

## Improvements since the last run

- The bot now avoids a Shocker and every adjacent tile even between visible electrical pulses. It also keeps those tiles out of smoke-bomb escape routes rather than treating the bomb countdown as protection from electricity.

## Incoming learnings

Treat a publicly described Shocker and all adjacent cells as electrical exposure even between visible pulses. Use existing checked escapes rather than waiting for damage to reveal the next orientation. Keep electrical exposure separate from smoke-bomb countdowns, and retain explicit refusal when no admitted immediate escape exists.

## Analysis

The recording timed out with a living hero, not an observed death. Decision 3180 (log lines 9145–9147) reached a pasty but received an explicit full-pack refusal. Decisions 3181–3183 repeated the pickup without changing inventory. At decision 3183 (9157–9159), starvation preparation selected the refused food before the existing inventory-cleanup controller could act. The ordinary room collector deferred the item correctly, but the higher-priority food helper ignored the refusal. Bounded recovery then moved away and returned; decision 3217 (9271) reported exhausted hungry recovery, whose continuation reused the same food helper. The last accepted transition, decision 11530 (42525), kept position, health and game clock unchanged. Source tracing identifies tools/policy_tree.py:25–45, tools/mage_policy.py:1162 and tools/exploration_budget.py:22–37 as the initiating scheduling chain. A limited reconstruction of the public full-pack receipt reproduced the original decision-3183 helper action and reason; it was not a reconstruction of all runtime memory. An isolated candidate probe selected existing checked inventory relief and stopped before any later observation. The focused patch routes current same-bag refusal evidence through existing guarded cleanup, preserving required pickups and honest receipts. The new regression failed three assertions on the original policy and passed all five tests after the fix; the full suite passed 2,203 tests with four skipped. This does not establish successful disposal, food collection, eating or improved survival.

## Recommendations

- **000217-starving-full-pack-handoff — Let starvation food selection use verified full-pack relief instead of repeatedly clicking refused food.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3180, log lines 9145–9147: pasty pickup explicitly refused by full pack.; Decision 3183, log lines 9157–9159: starvation preparation preempts inventory relief and repeats the refused pickup.; Decision 3217, log lines 9271–9273: exhausted recovery continues through the same food helper.; Decision 11530, log line 42525: accepted pickup leaves health, position and game clock unchanged.; tools/exploration_budget.py:22–52; tools/inventory_tactics.py:100–150,186–225.
  - Disposition: implemented

## Lessons for the next run

A publicly refused food pickup needs inventory relief before another attempt, even while starving. Keep refusal evidence tied to the current inventory and correct bag; preserve guarded disposal and require actual receipts before crediting either a drop or collection. A stopped game clock is not continuing starvation damage.

Update: **accepted**.
