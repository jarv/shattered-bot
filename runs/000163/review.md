# ShatteredAI run 000163

Played commit: `b6f70edd30a76bd3a9c4db68b3f173ff055584ae`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died during an exposed doorway retreat

## Improvements since the last run

- The bot can now cross ordinary observed grass when returning to a previously checked potion preparation area. Grass still does not qualify as a potion drinking or storage site, and hazard checks remain in place.

## Incoming learnings

Distinguish ordinary travel terrain from unknown-potion test terrain. Plain grass can connect a witnessed preparation area without becoming an admitted drinking site. Reobserve and validate storage on arrival; do not credit discovery or collection from a planned return.

## Analysis

The initiating mistake was choosing a distant doorway while already standing on a usable open threshold. Decision 3528 (selection 10231) starts a seven-step exposed route toward door 335 instead of stepping off door 643 into observed cover. Decisions 3528–3533, accepted lines 10232–10252, show six retreat moves and health falling from 31 to zero. Two DM-100s were observed; one was initially sleeping. The evidence does not establish the final killer. An isolated original-source fixture reproduces the recorded first step, 598; this is not recovered runtime memory or a full-run reconstruction. The proposed narrow correction admits a clean, freshly visible adjacent bank behind the current door, screening every observed caster, and retains fresh arrival verification before waiting. It rejects hazards, loot-blocked closure and unscreened sleeping casters. The new regression fails as expected on original policy and passes on the candidate; all 2024 Python tests pass, with four skipped. This establishes a corrected selection, not survival or subsequent closure. The adapter will derive the changed policy and new test; files is intentionally empty.

## Recommendations

- **000163-current-doorway-cover — Use verified adjacent cover at the current doorway before committing to a distant exposed doorway route.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3528, selection line 10231: hero on open door 643 selects step 598 toward remembered door 335.; Decision 3528 public map: adjacent banks 644 and 688 are visible and observed; provisional closure screens both observed casters.; Decisions 3528–3533, accepted lines 10232–10252: six retreat moves reduce health from 31 to zero.; tools/dm100_escape.py: original door search excludes the current threshold; the new deterministic regression reproduces the resulting selection.
  - Disposition: implemented

## Lessons for the next run

Before crossing a lightning-exposed room toward another door, check whether stepping off the current threshold provides observed cover. Account for sleeping casters too, exclude heaps that prevent closure, and verify actual closure and exposure on arrival. A planned retreat is not proof of safety.

Update: **accepted**.
