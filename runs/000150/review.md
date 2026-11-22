# ShatteredAI run 000150

Played commit: `5c05997de93319b2436b01cb786f4e27846613e4`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a prison guard after prolonged skeleton pursuit

## Improvements since the last run

- At an established doorway, the bot now prefers available magic against wraiths after the first surprise strike, rather than favoring ordinary melee damage. Its existing ranged-first preference against other undead remains in place.

## Incoming learnings

An established doorway limits approach lanes but does not remove wraith evasion after the first surprise strike. Preserve admitted magic priority there instead of comparing nominal melee damage alone. Do not treat post-death potion identities as resources the living bot knew how to use.

## Analysis

The final encounter began with skeleton combat at decision 3353 (line 9785), followed by eleven accepted retreat moves without an intervention. Low health excluded starting an unverified doorway setup; short routes to nominal single-attacker endpoints remained eligible and repeatedly preempted later combat choices. Health fell to four before the guard appeared. Decision 3369 exhausted those retreats and selected ranged cover; its accepted transition (line 9853) explicitly reports that a prison guard killed the hero after a pull. This attribution comes from the complete public death message, not nearby enemies. A specific contributing modeling defect is reproducible: the summoned skeleton visibly had adrenaline, but both approach-pressure and exposure estimates ignored that speed buff. The proposed correction recognizes the public icon without inferring hidden timers or future empowerment. A reduced decision-3368 fixture was checked against recorded terrain, enemy fields and hero position/health; this is an isolated helper probe, not reconstructed runtime memory. Original-source probes fail two expected assertions; the candidate passes all five new tests and the full 1,975-test suite, with four skips. This establishes corrected risk accounting, not a changed recorded action or avoided death. The broader non-choke pursuit failure remains unresolved. Unknown potion identities and post-death equipment revelations were not treated as living resources. Policy changes and the new regression are supplied through the adapter; files is intentionally empty.

## Recommendations

- **000150-visible-adrenaline-pressure — Include publicly visible adrenaline in approach-pressure and fast-pursuit estimates.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3366, accepted line 9837: the summoned skeleton gains a visible adrenaline icon.; Decision 3368, line 9846: the empowered minion remains at 2492 while retreat to 2439 is selected.; Reduced public-input probes: original exposure to 2439 and approach pressure at 2440 are zero; corrected values are one.; tools/challenge_combat.py:34-40,65-81; tools/multi_enemy_tactics.py:26-45; pinned game Char.java:770-776.
  - Disposition: implemented
- **000089-multi-rat-retreat-feasibility — Establish a bounded intervention or verified refuge before repeated non-choke retreats sustain enemy pursuit.** (high, deferred): The adrenaline correction does not resolve this broader backlog. Source inspection resolves the selector chain, but no bounded safe intervention and subsequent escape is validated: low health excludes unverified doorway setup, a zap spends time under two pursuers, the ordinary skeleton has a death blast, and the minion has no observed health bar. Next derive paired decision-3355/3359 fixtures with accepted pursuit, charge and damage bookkeeping, then validate ranged or shielding intervention plus freshly admitted spacing and a verified refuge, including interruption receipts. Do not lower health gates, disable retreat wholesale or guess potion effects.
  - Evidence: Decisions 3355 and 3359-3368, lines 9789 and 9801-9847: repeated retreats preempt later combat choices.; Accepted pursuit bookkeeping through line 9850 records eleven retreat moves and zero interventions.; Decision 3369, line 9851: no admitted single-attacker retreat remains.; tools/multi_enemy_tactics.py:125-157,190-196,244-265; tools/mage_policy.py:1166-1176; tools/pursuit_budget.py:77-135.
  - Disposition: deferred

## Lessons for the next run

A visible adrenaline icon is speed evidence even when an enemy description is unchanged. Count its faster approach conservatively, but do not treat a nominal single-attacker endpoint as a persistent refuge or claim that improved risk estimates prove survival. Preserve health, hazard and mandatory-pickup gates.

Update: **accepted**.
