# ShatteredAI run 000099

Played commit: `d5789dfb1287a762386be78856c817700f4f5a8c`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Killed by a gnoll scout while retreating

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Treat missing health as a preparation prerequisite when existing safe recovery is funded, rather than immediately exhausting mandatory discovery. Charge accepted recovery inputs to the existing budget. Recheck actual health, threats, inventory protection and drink admission afterward; preparation is not identification or collection success.

## Analysis

The hero died during retreat. Decision 1046 (transition 3155) reduced health from six to two; decision 1047 (transition 3160) ended at zero. The full terminal observation explicitly names a gnoll scout. An earlier supported defect wasted recovery: decisions 937–938 planted and activated Sungrass at 16/30 health, but decision 939 moved away despite publicly observed herbal healing; transition 2804 confirms the effect vanished. Garden activation preempted the seed selector without advancing its pending activation stage. When the consumed plant disappeared, the seed selector discarded recovery. The proposed correction recognizes the actual same-cell healing buff and retains existing bounded recovery safety checks. A minimal public-input-derived regression matches the preceding plant/activation selections; it is not full-run memory reconstruction. Original policy fails two assertions; the candidate passes all four new tests and the full 1845-test suite, with four skips. This establishes the recovery handoff correction, not survival or a safe replacement for later multi-enemy retreats. No post-death wand revelations informed the correction.

## Recommendations

- **000099-sungrass-activation-handoff — Retain bounded Sungrass recovery after the garden selector activates a pending seed.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 937, selection 2797: Sungrass planted at 16/30 health.; Decision 938, selection 2800 and transition 2801: garden activation produces observed herbal healing.; Decision 939, selection 2803 and transition 2804: movement immediately removes the healing effect.; tools/mage_policy.py:1226; tools/garden_tactics.py:26–46; tools/seed_strategies.py:88–114.
  - Disposition: implemented

## Lessons for the next run

Preserve paid-for Sungrass recovery when another selector activates the plant: use the observed same-cell healing buff, then recheck threats, hunger, health progress and the existing recovery budget before each wait.

Update: **accepted**.
