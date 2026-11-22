# ShatteredAI run 000124

Played commit: `e69b9367211772d0aa413566a12d469da06a49e7`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Preparation memory must remain executable after legitimate potion pickups change inventory. Establish a bounded preparation-only return with fresh bank and stash validation before relying on historical feasibility. Preserve reserved room supplies, mandatory pickup, hazard checks and terminal exhaustion; selecting preparation alone would not establish identification or room success.

## Analysis

The run ended in planner exhaustion, not death; the Mage remained at full health. Decision 733 (log line 2030) first exposes the initiating contradiction: the pending Sad Ghost reward return selects a route through publicly triggered trap 675, then rejects its retained trap name despite inactive terrain and expired effects. Original-source offline bookkeeping matched all 821 selections and the terminal blocker at decision 821 (line 2277). The correction aligns reward-return checks with existing inactive-trap walkability while preserving active hazards, threat guards, mandatory pickup and terminal exhaustion. A new regression fails by assertion on original policy and passes after the correction; the full suite passes 1,913 tests with four skips. Candidate reconstruction stops at the first changed selection, decision 733. Selecting the return step does not establish ghost rediscovery or reward collection.

## Recommendations

- **000124-ghost-inactive-trap-return — Allow the existing admitted Sad Ghost return route across publicly inactive traps without treating retained trap names as active hazards.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 420, log line 1170: trap 675 is publicly triggered; later observations retain its name after gas expires.; Decision 733, log line 2030: reward completion dialogue is public, but ghost-return admission rejects inactive trap 675 on the ordinary return route.; Decision 761, log line 2109: reconstructed return travel remains zero with the same inactive-trap veto.; Decision 821, log line 2277: unfinished reward blocks descent and exhausts the planner with the hero alive.; tools/ghost_quest.py:return_for_reward; tools/survival_policy.py:436–447.
  - Disposition: implemented

## Lessons for the next run

Distinguish a triggered trap's retained name from an active hazard when returning for the Sad Ghost reward. Keep effect checks and require fresh ghost interaction and actual reward evidence; an admitted return step is not collection.

Update: **accepted**.
