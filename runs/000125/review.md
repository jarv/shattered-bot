# ShatteredAI run 000125

Played commit: `b5da034223ce2504590ceca0f568942649696049`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now recognizes that a triggered trap is no longer active when returning for the Sad Ghost’s reward. It still avoids harmful effects and requires a fresh encounter before claiming the reward.

## Incoming learnings

Distinguish a triggered trap's retained name from an active hazard when returning for the Sad Ghost reward. Keep effect checks and require fresh ghost interaction and actual reward evidence; an admitted return step is not collection.

## Analysis

The run ended with a living Mage at full health, unable to proceed. The upgrade scroll seen at decision 320 (log line 971) remained behind an eternal-fire safety buffer. Intuition identified a carried potion as frost at decisions 549–552 (lines 1656–1663), but decision 553 resumed exploration instead of its unfinished fire-observation return. The known-potion branch skipped that return, and the extinguisher only supported nearby throwing positions. At decision 596 (lines 1790–1791), mandatory pickup correctly prevented descent. Offline reconstruction on the played source matched all 596 selected action/reason pairs and reproduced the terminal failure. Copied-state probes established an existing guarded observation route, not fire clearance. The proposed correction preserves that bounded return after identification, prioritizes the existing local extinguisher, and retains hazard checks and mandatory collection. The new regression failed with the expected missing-action assertion on original source and passed on the candidate; the full suite passed 1,916 tests with four skips. Candidate reconstruction stopped at its first changed decision, 553; no changed gameplay was executed. This establishes preparation selection, not puzzle success or scroll collection.

## Recommendations

- **000123-inventory-aware-discovery-return — Establish an inventory-aware preparation return before mandatory discovery loses every compatible bank receipt.** (high, deferred): No safe focused replacement is established. The missing prerequisite is an executable collateral-separated stash and retrieval plan for the new three-potion inventory; singleton receipts cannot certify it. Before identification, an outstanding levitation reservation also prevents simply drinking earlier. Next derive paired decision-295/315 fixtures around bank 849 and its alternatives, including decisions 299/306 inventory changes. Validate bounded preparation-only transit, fresh bank/stash admission, accepted-input accounting and return to unfinished pickup. Require a demonstrated safe stash or an actually observed identification/protection resource before changing arbitration. Do not weaken inventory matching, hazard gates, reservations or mandatory pickup.
  - Evidence: Decisions 294–295, log lines 816–820: exploration and collection transit leave the water area carrying crimson alone.; Decision 299, selection 831 and accepted transition 832: charcoal is collected; existing singleton bank receipts become incompatible.; Decision 306, selection 852 and accepted transition 853: golden is collected.; Decisions 313–314, log lines 873–876: the identify scroll reveals crimson as levitation; strength remains unresolved.; Decision 315, log line 877: discovery exhausts with the Mage alive.; Offline reconstruction matches all 315 selections; 73 historical banks remain transit-reachable but inventory-incompatible.; tools/descent_potions.py:85–143,376–417; tools/potion_stash.py:103–134; tools/mage_policy.py:443–497.
  - Disposition: deferred
- **000112-flame-impact-clearance — Account for the actual flame-potion impact before authorizing bookshelf ignition, then verify clearance after escape.** (high, deferred): The selector checks distance from the requested shelf, but a nonpassable bookshelf makes the projectile collide one cell earlier. For the recorded 612-to-689 shot, impact is reconstructed at 650, adjacent to the hero; flame covers neighboring cells. The observed burning confirms the unsafe result, not a successful clearance. A larger requested-target distance alone leaves impact-area collateral and post-escape clearance unverified; the existing close-shelf regression also expects this class of throw. Next derive an actual-impact fixture and validate a floor-targeted ignition or separately admitted impact-safe bank, protecting the complete impact/fuel footprint and confirming fresh shelf clearance before local retrieval. Do not certify the unseen shelves burned away or replace the throw with speculative movement. No safe complete replacement is certified here.
  - Evidence: Decision 835, line 2378: known liquid flame is selected from 612 for shelf 689.; Decision 836, selection line 2380 and accepted line 2381: the target input consumes the potion, starts burning and lowers HP from 30 to 27.; Decisions 837-840, accepted lines 2384-2393: extinguishing travel reaches water at 733 with 23 HP.; Decision 940, line 2697: remembered shelves still reserve missing flame alongside the gas obligation.; tools/wooden_barrier.py:146-206; tools/survival_policy.py:541-554; game Item.throwPos, Ballistica.build and PotionOfLiquidFlame.shatter.
  - Disposition: deferred
- **000112-gas-preparation-return — Establish a funded return to freshly verified gas-room preparation before mandatory discovery exhausts.** (high, deferred): Complete source and matching reconstruction resolve the selecting-state gap. Several trip origins have observed nonflammable surroundings, but those surroundings are now unseen; the remaining origins also fail terrain or effect checks. Gas lacks the unknown-supply revisit used for flight and pool, and hunger independently excludes testing. No executable fresh bank/stash admission and gas-funded preparation transaction is established. Next derive the recorded return corridor to 436/475/514 and validate bounded reobservation with accepted movement receipts, fresh hazard checks, inventory-compatible remote stash admission and a puzzle-specific meal only after feasibility is demonstrated. Keep chest pickup mandatory and retain terminal exhaustion. A meal alone, stale visibility or generic remote drinking is not a repair.
  - Evidence: Decision 925, selection line 2652 and accepted line 2653: exploration reaches the gas entrance at 592.; Decision 926, line 2655: chest 669 and gas are observed; the hero retreats to 553.; Decision 939, accepted line 2695: opening door 249 advances time at full health; decision 940, line 2697 exhausts mandatory discovery.; Source-pinned offline reconstruction matches all 940 selections and reproduces the terminal blocker. Copied terminal probes find nine hypothetical gas-trip origins but no currently visible admitted drink bank; removing hunger still yields no preparation.; tools/descent_potions.py:309-347; tools/puzzle_supplies.py:585-640,764-810; tools/preparation_prerequisites.py:17-65.
  - Disposition: deferred
- **000125-known-frost-observation-return — Keep the guarded fire-observation return actionable when the carried potion becomes known frost.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 320, log line 971: upgrade scroll 646 is observed but excluded by the eternal-fire buffer.; Decisions 549–552, log lines 1656–1663: intuition identifies the carried frost supply.; Decision 553, log line 1664: exploration replaces the unfinished observation return.; Decision 596, log lines 1790–1791: uncollected progression resource blocks descent with the Mage alive.; tools/puzzle_supplies.py: known-supply branch; tools/room_tactics.py: extinguish and throw_vantage; tools/mage_policy.py: mandatory progression descent gate.
  - Disposition: implemented

## Lessons for the next run

Identifying a puzzle supply must not orphan its unfinished observation return. Known frost can fund bounded travel back over observed safe ground, but fresh fire visibility, safe throwing checks and actual pickup evidence are still required. Keep the terminal failure and mandatory progression gate; never substitute clearance or collection assumptions.

Update: **accepted**.
