# ShatteredAI run 000236

Played commit: `3df60e55919a3ad6dfa2da700f5842530f0312db`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died under rat, fly and crab pressure

## Improvements since the last run

- The bot now recognizes the magefruit crafting option when cooking blandfruit with mageroyal. It checks the resulting inventory for the actual named fruit rather than treating the recipe preview as a completed craft.

## Incoming learnings

Verify known recipes against their publicly rendered output names. A recipe preview is not acquisition: retain pre-craft counts and require actual inventory changes. Repairing the missed fruit craft does not establish later frost identification, key collection or survival.

## Analysis

The hero died under combined rat, fly and crab pressure; the recording does not establish an individual killer. An earlier unknown emerald-ring equip at decision 404 (selection line 1165, accepted receipt 1166) revealed a curse and reduced strength from 10 to 8. During the final pursuit, strength was 9 while identified cloth armor required 10. Decisions 749–755 repeatedly retreated with observed movement costs of approximately 1.2 turns. At decision 755 (selection 2178, receipt 2179), the planner admitted endpoint 235 with one possible approach attacker, despite the longer movement allowing additional approach opportunities. The selecting chain reaches multi_enemy_tactics.approach_pressure, which used a fixed one-step normal or two-step fast-enemy horizon without accounting for known armor encumbrance. Decisions 758–760 then show HP falling 20 to 13 to 4 to zero during melee and dew drinking. No planner incident was recorded. The proposed next-run correction conservatively expands that approach horizon using observed strength and identified armor requirements; it does not invent a safe alternative. A new reduced public-observation regression fails on the original helper and passes on the correction. The full suite passes 2,260 tests with four skipped. This is not a reconstruction of original runtime memory or evidence that the changed policy would survive.

## Recommendations

- **000236-encumbered-retreat-envelope — Account for publicly known armor slowdown when evaluating multi-enemy retreat approaches.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 404, selection line 1165 and accepted receipt 1166: unknown-ring equip reveals a curse and reduces observed strength.; Decisions 749–755, accepted receipts 2149–2179: retreat moves cost approximately 1.2 turns with strength 9 and identified armor requiring 10.; Decision 755, selection line 2178: endpoint 235 is admitted with one approach slot while a fly, rat and fast crab are closing.; Decisions 758–760, accepted receipts 2191, 2193 and 2196: health falls to zero after retreat options are exhausted.; tools/multi_enemy_tactics.py:31–80 and 174–177: approach estimates govern endpoint admission.
  - Disposition: implemented

## Lessons for the next run

Known armor encumbrance must affect retreat approach estimates: a move that costs more than one turn can admit extra enemy movement. Keep current contact separate from prospective approach pressure. Unknown-ring effects and post-death revelations must not be used to justify earlier choices; a corrected risk estimate does not establish a safe escape or survival.

Update: **accepted**.
