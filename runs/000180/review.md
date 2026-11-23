# ShatteredAI run 000180

Played commit: `bda17d76d254a7eba8034d328e7d6cd9bcf317a2`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When testing unknown potions requires protected storage, the bot now starts preparing at its current safe spot instead of first walking to preferred water. It still checks potion protection and rechecks safety on arrival.

## Incoming learnings

When unknown-potion discovery needs protected storage, begin an already admitted standing-bank preparation rather than repeatedly moving to preferred water that loses storage visibility. Recheck arrival and require real drop, consumption and retrieval receipts; preparation selection alone is not completion.

## Analysis

The hero stopped alive, not dead. Offline reconstruction of the played source matched decisions 0–1136 and reproduced terminal decision 1137. The initiating stale-route contradiction already appears after decision 1106: a confirmed final scout defeat leaves its immediate escape edge protected, so decision 1107 rejects useful key routing and detours. Later, a revealed summoning trap excludes the key, and another retreat protects the food route. After the final crab defeat, reversal rejection and exhausted recovery end the run. The correction retires only an immediate edge occupied by a newly confirmed sole defeated foe, with strict threat, visibility and status checks. The candidate first diverges at decision 1107; reconstruction stops there. A separate late-state probe correctly retains protection because another stale sighting remains. The new regression fails on original policy and passes on the candidate; all 2058 suite tests pass, with four skipped. This establishes a focused initiating bookkeeping repair, not successful collection, puzzle completion or survival.

## Recommendations

- **000180-defeated-escape-edge — Retire a matching immediate escape edge after an unambiguous last-pursuer defeat, without weakening other movement gates.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1106, accepted log line 3249: final adjacent scout defeated.; Decision 1107, selection line 3252: stale reversal protection substitutes a retreat for key routing.; Decisions 1119–1122, log lines 3291–3300: newly observed summoning trap interrupts the key approach.; Decisions 1135–1137, log lines 3337–3342: crab defeat, rejected food routing and terminal planner exhaustion.; Source-pinned reconstruction matches original selections through 1136; candidate stops at first divergence 1107.; tools/combat_observation.py; tools/escape_commitment.py; tools/mage_policy.py:416–422; tools/tactical_recovery.py:105–165.
  - Disposition: implemented

## Lessons for the next run

A confirmed last pursuer defeat can retire its matching immediate escape edge without declaring the floor clear. Retain unrelated edges and threat memories, and continue requiring actual pickup receipts and independent hazard admission.

Update: **accepted**.
