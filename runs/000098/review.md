# ShatteredAI run 000098

Played commit: `8b6c344b485a87a4e32b8cfe64e4a26d1beeaca4`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When known locked chests outnumber held golden keys, the bot now prefers a fully budgeted flight trip to another golden key before spending levitation on a chest. It still checks protection and the return journey.

## Incoming learnings

A held key does not mean every observed lock is supplied. Prefer a fully budgeted matching-key flight trip before spending scarce levitation on a chest when keys are still deficient. Recheck actual protection before movement; never infer an unknown potion identity or treat a planned pickup as collected.

## Analysis

The hero remained alive at 25/30 HP when mandatory potion discovery exhausted the planner. Decision 612's accepted transition (line 1848) advanced the clock normally; decision 613 (line 1850) stopped before another action. Ordinary healing targeted 75% health, while discovery required 85%, leaving a preparation gap. The terminal report showed zero healing waits spent, available food and an admitted recovery budget, but discovery tried no healing prerequisite. The local candidate supplies bounded stationary healing only in that gap, retaining threat, hunger, terrain, drink-safety and mandatory-pickup gates. A new reduced public-evidence regression fails on the original selectors and passes on the candidate; all 1,848 suite tests pass, with four skipped. This is not reconstructed runtime memory or proof that subsequent potion identification or room retrieval succeeds. Changed policy and regression files are supplied locally; files is empty because the trusted adapter derives them.

## Recommendations

- **000098-discovery-health-prerequisite — Resolve the ordinary-healing versus mandatory-discovery health gap with an admitted bounded recovery prerequisite.** (high, rejected): Candidate validation failed; code was not promoted.
  - Evidence: Decision 612, accepted transition line 1848: movement advances turn 599 to 600 at 25/30 HP.; Decision 613, line 1850: discovery exhausts on health despite zero healing waits spent and carried food.; tools/mage_policy.py:742–750 and tools/policy_nodes.py:566–574: ordinary recovery stops below discovery's required health.; tools/descent_potions.py:206–266 in the played source: paused health immediately becomes terminal planner exhaustion.
  - Disposition: rejected

## Lessons for the next run

Treat missing health as a preparation prerequisite when existing safe recovery is funded, rather than immediately exhausting mandatory discovery. Charge accepted recovery inputs to the existing budget. Recheck actual health, threats, inventory protection and drink admission afterward; preparation is not identification or collection success.

Update: **rejected**.
