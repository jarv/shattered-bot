# ShatteredAI run 000114

Played commit: `f4582ac7c81cdfd008f9f2f55c2592fa9aa347cf`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Mandatory preparation can require more health than ordinary exploration recovery. Admit a bounded, freshly checked health prerequisite rather than treating that threshold gap as exhausted discovery. Keep potion identification, protected inventory and actual reward pickup as separate obligations.

## Analysis

The living hero exhausted mandatory entrance-shop search, rather than dying. Doors 762 and 953 were already observed at decision 2094 (line 6183), but repeated nearby frontier choices pulled the search through a large connected component. Decision 2174 (line 6402) finally routed toward another door. Decision 2246 consumed the 80th accepted search input; the final blink advanced time without finding the shop. Decision 2249 (line 6646) stopped with 50/50 HP. Source-pinned offline bookkeeping reconstruction matched all 2,249 recorded selections; this was reconstructed memory, not recorded runtime state. The correction adds entrance-relative ordering among already admitted same-layer doors and frontiers, preserving movement safety, target commitment, actual visit and pickup evidence, the search cap and terminal failure. A copied validated decision-2111 probe selects an admitted route toward door 953 instead of further outward scouting, then stops without using later observations. The new regression fails as expected on original policy and passes on the correction; the full suite passes 1,874 tests with four skips. This establishes a selection repair, not successful shop discovery, purchases or subsequent survival. Changed files are supplied through the trusted adapter.

## Recommendations

- **000114-shop-entrance-radius — Prevent outward entrance-frontier chains from starving already admitted entrance-side doors.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2094, line 6183: entrance 855 and doors 762 and 953 are publicly observed.; Decision 2100, lines 6201-6203: another outward frontier input is selected and accepted.; Decision 2111, line 6228: a copied validated selector state admits an alternative route toward door 953.; Decision 2174, line 6402: door search begins only after extensive frontier scouting.; Decision 2246, lines 6638-6640: the 80th accepted shop-search input opens door 750.; Decision 2249, line 6646: mandatory shop search exhausts with the hero alive.; tools/shop_tactics.py:186-230; tools/objective_planning.py:79-108; tools/policy_nodes.py:238-257.
  - Disposition: implemented

## Lessons for the next run

An entrance search can drift indefinitely through adjacent frontiers even while entrance-side doors remain unchecked. Order admitted work relative to the entrance as well as the current hero, without claiming a shop visit or waiving unfinished pickup.

Update: **accepted**.
