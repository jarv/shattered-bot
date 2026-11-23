# ShatteredAI run 000177

Played commit: `52d49c8306afa50b450619deb6d88090dbaf322b`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died after guard pulls and a damaging multi-enemy retreat

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

An empty visible room, full health and walkable exits do not establish safe unidentified-potion testing: paralysis can consume many turns before the next decision. Separate protection of carried potions from protection of the hero, and never treat post-death potion identities as prior knowledge.

## Analysis

The hero died after a guard-pull encounter became a damaging multi-enemy retreat. Decision 2849 requested cover at 775 from 808, but the accepted transition ended at 810 with crippled newly observed (lines 8189–8190). Decision 2850 requested 777 but ended at 778, losing four HP over two turns (8193–8194). These displacement and status observations, together with the chain messages and pinned Guard behavior, support guard pulls; they do not identify the final killer. The next two retreat inputs each consumed two turns while crippled. A new doorway setup then led through 776, 809 and 778, reducing HP from 53 to 36 (decisions 2852–2854, lines 8202–8213). Decision 2855 reported no admitted single-attacker retreat. Combat, dew and a known haste potion followed; the final accepted zap transition reduced HP from 6 to 0 (decision 2864, line 8241).

The initiating policy weakness is that retreat admission models enemy approach slots but not the extra exposure of crippled movement after a pull. In tools/multi_enemy_tactics.py:136–137,195–208, impairment rejection omits cripple, unlike tools/ranged_tactics.py:109–126. The doorway route checks immediate attack counts, not two-turn transit exposure, and remains committed until its separate health budget fails. This establishes a tactical modeling gap, not proof that refusing every impaired retreat would be safer. No patch is supplied: neither an alternative move nor a stationary attack has been validated against the original selecting state. Replacing retreat with an unconditional veto could simply expose the hero to the same attackers. Full-log and source inspection resolved the timing and displacement gaps, but original route memory and a safety-qualified replacement remain unvalidated. No policy-memory reconstruction or changed-decision continuation was performed. No post-death item identity is used.

## Recommendations

- **000177-crippled-retreat-exposure — Validate a cripple-aware retreat reassessment after guard displacement before committing to a doorway setup.** (high, deferred): The blocker is replacement-action safety, not omitted selector source. Cripple-aware rejection alone can force combat under multiple attackers, and no alternative has been validated on the original selecting state. Next reconstruct public-input bookkeeping through decision 2852, stopping at the first selection divergence, then compare the current route with existing attack and escape options on copies. Derive a regression for two-turn transit exposure and preserve hazard gates, accepted-input accounting and honest pickup receipts. Do not assume either waiting or speculative movement is safe.
  - Evidence: Decision 2849, lines 8189–8190: requested cover differs from actual landing; cripple appears.; Decisions 2850–2852, accepted lines 8194, 8198 and 8203: crippled retreat inputs consume two turns.; Decisions 2852–2855, lines 8202–8218: damaging doorway setup ends without an admitted single-attacker retreat.; tools/multi_enemy_tactics.py:136–163,190–264; tools/ranged_tactics.py:109–133.
  - Disposition: deferred

## Lessons for the next run

Guard pulls can displace a requested escape and leave crippled movement consuming two turns. Revalidate the actual landing and transit exposure before committing to another doorway setup; a geometric endpoint alone is not a safe escape.

Update: **review-only**.
