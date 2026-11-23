# ShatteredAI run 000182

Played commit: `c53585d61860ccd4aad497e7f5e6b0899e2fecd8`

Outcome: blocked

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Blocked after retreating back into toxic gas

## Improvements since the last run

- After some navigation or optional-room stalls, the bot can attempt a bounded retreat to known downstairs. It still refuses routes that bypass required pickups or unfinished preparation, and it does not count abandoned rewards as collected.

## Incoming learnings

Before abandoning a required pool chest, check whether carried, identified, uncursed armor can satisfy timed-movement preparation. Seeing a bandolier alone does not establish potion protection. Recheck actual equipment and every potion, entrance, protection and pickup requirement after preparation; never infer unknown colors or waive the chest.

## Analysis

The run ended blocked, not dead: the last observation shows the hero alive at 27/35 HP. Gas was first observed at doorway 903 during decision 880. Later, the multi-enemy retreat selected that doorway despite remembered gas beyond its closed, apparently clear threshold. Decision 1023 escaped the gas; decision 1024 immediately re-entered the same doorway. The final observation places scouts on both exterior escape squares, and the gas escape controller stopped without an admitted exit or usable transport. No killer is established.

The proposed correction rejects ordinary combat retreat routes through closed doors adjacent to remembered toxic gas, for both new and continuing plans. A reduced public-evidence fixture reproduces the original door selection; the original policy fails three assertions, the candidate passes, and the full suite passes 2,072 tests with four skips. Fresh observed gas clearance readmits the door. This is not a full runtime reconstruction or proof that the alternative combat choice survives. Required pickups, protected retrieval, hazard checks and explicit terminal stops remain intact.

## Recommendations

- **000182-gas-door-retreat — Exclude known gas-room entrances from ordinary multi-enemy doorway retreats until fresh observations clear the gas.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 880, lines 2563–2564: gas observed at doorway 903 and escape accepted.; Decision 1022, lines 2974–2975: retreat enters the previously observed gas entrance.; Decisions 1023–1024, lines 2979–2984: gas escape is followed by re-entry through the reclosed door.; Terminal line 2988: living hero blocked in gas with exterior squares occupied.; tools/multi_enemy_tactics.py:190–217; tools/survival_policy.py:339–358; tools/toxic_escape.py:44–84.
  - Disposition: implemented

## Lessons for the next run

A clear closed doorway does not establish that the gas behind it has cleared. Check remembered neighboring gas before choosing a combat refuge, and require fresh clearance evidence before readmitting that entrance.

Update: **accepted**.
