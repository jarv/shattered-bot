# ShatteredAI run 000223

Played commit: `f0d3354bdd423869fd56fba146fab2f0ce329ecd`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now recognizes a freshly confirmed DM-100 defeat even when the enemy is burning, so unreliable weapon-damage measurements do not leave that defeated enemy marked as a lightning threat.

## Incoming learnings

Keep confirmed defeat receipts independent of damage attribution. Fire can make a weapon-damage sample unreliable without making an exact fresh defeat confirmation unusable. Preserve hazard vetoes and terminal planner diagnostics rather than masking stale-threat failures with waits or blind attacks.

## Analysis

The hero remained alive at full health when mandatory potion preparation exhausted; this was not a death. Decision 44 opened the gas entrance, and decision 45 retreated from observed gas. Decisions 47–55 successfully staged and protected inventory for one unknown-potion test, but its observed effect was mind vision, not purity. After retrieving the stored potion and completing other floor work, the bot could not return to that preparation area. At decision 261, lines 727–728, missing purity blocked strength discovery, while the supply planner required a currently visible testing bank and had no gas reobservation handoff. All four preparation alternatives declined; recovery accepted no actions and credited no collection. Offline reconstruction against the played source matched decisions 0–260. On a copy of that validated terminal state, the candidate selects ordinary-ground travel toward the earlier bank instead of exhaustion. The focused correction extends the existing observation-only flight approach planner to gas, retaining hypothetical reward-route checks, hazard exclusions, bounded travel, and fresh arrival requirements. The new regression fails on the original helper and passes on the candidate; the full suite passes. This establishes an available preparation action, not successful arrival, safe potion consumption, room collection, or survival.

## Recommendations

- **000112-gas-preparation-return — Provide bounded observation-only return to gas preparation when other floor work has taken the hero away.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 44, accepted line 123; decision 45, accepted line 126: gas entrance observation and retreat.; Decisions 47–55, lines 131–155: admitted bank, remote potion storage, and an unknown drink with observed mind vision.; Decision 261, lines 727–728: missing purity blocks mandatory discovery; every preparation prerequisite declines.; tools/descent_potions.py:350–387; tools/puzzle_supplies.py:416–468,968–1008.; Original-source reconstruction matches decisions 0–260; isolated terminal candidate selects ordinary approach travel. Four new regression cases pass, and the full suite passes.
  - Disposition: implemented

## Lessons for the next run

A missing potion reservation needs an executable preparation return, not just a visible-bank requirement. Reuse a verified ordinary approach to refresh observations before testing; never treat hypothetical protection, a failed potion hypothesis, or fallback descent as a pickup receipt.

Update: **accepted**.
