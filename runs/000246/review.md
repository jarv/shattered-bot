# ShatteredAI run 000246

Played commit: `a7db7917879d0c030fce6d5ee28c714ba813b235`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died under vampire-bat pressure while starving

## Improvements since the last run

- When a known frost potion reaches visible magical fire, the bot now attempts to extinguish it before returning to exploration. It still checks visibility, throwing distance, a clear shot and nearby threats.

## Incoming learnings

Complete the known-frost handoff when arriving at visible magical fire rather than resuming exploration. Keep visibility, throwing distance, clear-shot, threat and workflow checks, and require fresh receipts before crediting extinguishing or mandatory pickup. Reduced fixture bookkeeping is reconstructed, not recorded runtime memory.

## Analysis

The hero died while starving and under observed vampire-bat pressure; the recording does not identify a definitive killer. Earlier fighting reduced HP from 26 to 5 (decisions 5386–5393). A separate initiating defect prolonged the terminal chase: decisions 5405, 5408 and 5411 selected doorway scouting despite a fast bat following. At decision 5408 (log 16180), the hero had 4/85 HP, a charged known missile staff, and a bat one cell behind; the proposed step left a two-cell gap. The recorded species report already included fast movement, but the exposure scorer checked only speed buffs or particular description wording. This incorrectly bypassed existing low-health and water-scout exposure checks. The accepted move at log 16181 consumed a turn and reduced HP to 3; starvation prevents attributing that loss to an attack. The final targeting receipt at log 16199 confirms HP 3 to 0. The proposed correction consistently includes existing fast-species capabilities in pursuit exposure. A reduced public-observation fixture reproduces the original scout and, after correction, selects an existing charged stationary attack. This fixture includes explicitly reconstructed inspection bookkeeping, not recovered original runtime memory. The new six-test regression has four expected assertion failures against original source and passes on the candidate; the full suite passes 2,279 tests with four skips. Neither a guaranteed kill nor improved survival is established.

## Recommendations

- **000246-fast-species-doorway-pressure — Include known fast-species movement in pursuit exposure before admitting doorway scouting.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 5408, log 16180: fast-movement bat report, critical HP and admitted two-cell-gap scouting.; Decision 5408, log 16181: accepted movement consumes one turn; HP 4 to 3 while starving.; Decision 5411, logs 16188–16189: another scouting step preserves the same short pursuit gap.; tools/challenge_combat.py:65–86; tools/doorway_tactics.py:351–367; tools/unit_profiles.py:35–37.; New regression: original source fails four assertions; candidate passes all six tests and the full unittest suite.
  - Disposition: implemented

## Lessons for the next run

Use the existing fast-movement species capability consistently when evaluating short pursuit gaps; an empty buff list does not make a vampire bat slow. Keep pursuit risk separate from current melee contact, and verify actual damage, defeat and pickup receipts. The isolated fixture demonstrates a different admitted selection, not encounter success.

Update: **accepted**.
