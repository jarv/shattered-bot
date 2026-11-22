# ShatteredAI run 000116

Played commit: `d06db4ef0e82b64d76c4fd0d41e7211d4291d4c8`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Killed by a skeleton's bone explosion

## Improvements since the last run

- The bot no longer returns to a fully visible approach to a piranha room when that spot already fails its preparation checks. It still keeps the chest unresolved rather than pretending it was collected.

## Incoming learnings

A fully observed approach that fails its arrival checks must not keep attracting travel after exploration leaves it. Preserve the unresolved chest and terminal failure label; validate a separately budgeted known-invisibility door and return plan before permitting a replacement.

## Analysis

The hero died from a skeleton's bone explosion: decision 2254 targets the adjacent skeleton with 2 HP, and accepted transition line 6723 records zero HP; the recorded death message confirms the cause. Earlier resource ordering contributed to the vulnerability. The hero entered the shop starving at 6 HP. Known rations were visible by decision 2183, but bags and scrolls outranked food. At decision 2192, a reachable 100-gold ration was available with 798 gold and no safe carried food, yet the bot pursued scrolls and did not buy food until decision 2203. The proposed focused correction prioritizes known rations while already starving without safe food, preserving curse-removal priority, route restrictions and purchase confirmation. An isolated original-source selector probe matches decision 2192; the candidate selects the admitted food approach instead. This is not a full runtime-memory reconstruction or evidence that the changed choice prevents death. The new regression fails on original policy with two expected assertions and passes on the candidate; the full suite passes 1881 tests with four skips. The terminal spacing problem and earlier resource depletion remain outside this repair.

## Recommendations

- **000116-starving-shop-food — Prioritize known shop rations over optional supplies when starving without safe carried food.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2183, line 6544: known 100-gold rations are observed while starving at 6 HP.; Decision 2192, line 6562: at 5 HP with 798 gold and no safe carried food, the bot pursues a scroll instead of the nearby ration.; Decisions 2195 and 2197, lines 6568 and 6572: scroll purchases precede food.; Decisions 2203–2204, lines 6584–6587: food is finally purchased and eaten, ending starvation.; tools/policy_nodes.py:238–259; tools/shop_tactics.py:34–79.
  - Disposition: implemented

## Lessons for the next run

When already starving without safe carried food, buy an observed, affordable ration before optional shop supplies. Raw mystery meat is not safe carried food. Keep existing movement and purchase checks; choosing food does not prove acquisition or survival.

Update: **accepted**.
