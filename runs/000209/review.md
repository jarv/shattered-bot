# ShatteredAI run 000209

Played commit: `6cd4598c9443fda8f2b5df0868d4399ac1409cfa`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Plan unknown-potion testing and protected reward retrieval as distinct prerequisites when their safe locations differ. Preserve fresh bank checks, inventory protection, actual protective-effect verification, mandatory discovery, pickup receipts and explicit planner exhaustion. A feasible route calculation alone does not establish successful retrieval.

## Analysis

The run ended with a living hero at 12/65 HP, not an observed death. Decision 3304 suffered displacement and damage during doorway flight. The terminal planner defect arose later: decision 3308 consumed a known magic-missile charge, advanced one turn, gained six XP without leveling, and removed the only observed enemy. Arcane Vision supports tracking any surviving struck caster. The policy recognized adjacent missile receipts and ranged level-up receipts, but excluded this ranged same-level receipt, leaving a phantom DM-100 lightning lane. At decision 3310 that memory blocked ordinary recovery and progress before those selectors could run. The focused correction extends the existing tracked-missile receipt to unchanged level while preserving its identification, charge, timing, geometry and ambiguity checks. A new reduced public-evidence regression failed on the original policy and passed on the candidate; the full suite passed 2174 tests with four skips. An exact recorded-input receipt probe corroborated the difference. Only receipt bookkeeping was reconstructed, not the full run. This does not establish a safe next move, repair the earlier guard displacement, or prove future survival.

## Recommendations

- **000209-arcane-missile-same-level-receipt — Retire matching DM-100 memory after a verified same-level ranged missile kill receipt.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3307, selected log line 9664: known staff, Arcane Vision and DM-100 bar 6/21.; Decision 3308, selected line 9666 and accepted line 9667: charge 3/7 to 2/7, one turn, XP 8 to 14, unchanged level and no surviving actor.; Decision 3310, lines 9671–9673: phantom lightning-lane exhaustion with hero alive.; tools/combat_observation.py:123–180,237–287; tools/policy_nodes.py:93–115.
  - Disposition: implemented

## Lessons for the next run

Recognize a consumed clear-ray magic missile with Arcane Vision and six public XP as a narrow matching-caster retirement receipt even without a level-up. Preserve refusal of ambiguous disappearance, mandatory pickups, hazard checks and explicit planner exhaustion. Releasing a stale threat veto is not proof of successful progression.

Update: **accepted**.
