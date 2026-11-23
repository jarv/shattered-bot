# ShatteredAI run 000222

Played commit: `2ffc9b50f42d5d2ef7f603e3183181774c98a8c1`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When temporary doorway fire blocks the return to the Sad Ghost, the bot can watch from verified nonflammable ground within a limited safety and hunger budget. It still requires fresh clearance before moving and does not count the reward as collected.

## Incoming learnings

An unreachable quest-return area is not a searched area. Preserve the reward obligation and hazard veto while distinguishing a freshly observed temporary fire bottleneck from genuine search exhaustion. Require fresh clearance before resuming movement.

## Analysis

The hero remained alive at full health when the planner stopped. The initiating defect was a discarded defeat receipt, not an impossible combat state. Decision 2841 (selection line 8202, accepted transition 8203) attacked the DM-100 on a burning doorway; the next observation showed its disappearance, a fresh defeat message and six experience gained. Fire correctly prevented damage measurement, but that early return also skipped retirement of the separate lightning-threat memory. After decision 2842 moved away, the stale remembered lane triggered the terminal safety blocker at decision 2843 (lines 8207–8208). The immediate-safety controller excluded ordinary recovery and exploration, and abandonment correctly declined an emergency blocker. A source-pinned isolated probe matched decision 2841's local selected action and reason, then reproduced retained memory on the original receipt handler and retirement on the candidate. This is local bookkeeping reconstruction, not a reconstruction or replay of the complete run. The proposed correction separates confirmed melee defeat retirement from fire-confounded damage sampling, retaining exact fresh-message, matching-cell and floor checks. The new regression had two expected assertion failures on original source and passed on the candidate; the full candidate suite passed 2,218 tests with four skips. No subsequent survival, fire clearance or collection success is established.

## Recommendations

- **000222-burning-dm100-receipt — Retire a confirmed melee-defeated DM-100 even when fire prevents damage measurement.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2841, log lines 8202–8203: burning doorway attack followed by a fresh DM-100 defeat message, disappearance and experience gain.; Decision 2842, log lines 8204–8205: exploration moves away from the defeated caster's doorway.; Decision 2843, log lines 8207–8208: stale lightning-lane blocker exhausts the planner with the hero alive.; tools/combat_observation.py:70–75: effects censor capture before original defeat retirement can run.; The new regression fails on original source and passes after separating confirmed retirement from damage capture.
  - Disposition: implemented

## Lessons for the next run

Keep confirmed defeat receipts independent of damage attribution. Fire can make a weapon-damage sample unreliable without making an exact fresh defeat confirmation unusable. Preserve hazard vetoes and terminal planner diagnostics rather than masking stale-threat failures with waits or blind attacks.

Update: **accepted**.
