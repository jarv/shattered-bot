# ShatteredAI run 000131

Played commit: `98dd013d1f9a1b8ceb7b6abe6db73b123ae715fd`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died to lightning under DM-100 pressure

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Reserve an executable preparation opportunity before exploration disconnects every compatible bank. Remembered feasibility alone cannot guarantee an admitted return. Preserve fresh bank and storage validation, actual consumption and pickup receipts, reserved supplies and terminal exhaustion.

## Analysis

The hero died to lightning: decision 3621's accepted transition (log line 10437) records health falling from two to zero and explicitly reports a fatal lightning bolt. The initiating defect investigated is earlier: decision 3609 (line 10391) abandons a wall-separated position to seek a remembered door merely because a DM-100 is visible. An isolated original-helper probe on the recorded public input reproduces step 964 and the reported door plan, although both conservative bolt-line checks find the hero occluded. This is not a full reconstruction of original runtime memory. The proposed guard declines new door flight without current or remembered exposure, leaving existing controllers to choose any subsequent action. A new deterministic public-geometry regression fails as expected on the original selector and passes after correction; the candidate full suite passes 1,929 tests with four skips. This does not establish a safe replacement action or survival, and no changed trajectory was replayed.

## Recommendations

- **000131-occluded-dm100-flight — Do not initiate another door escape solely because a wall-separated DM-100 is visible.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3609, selection line 10391: a new northward door flight preempts descent from cell 1012 despite blocked bolt lines from the observed caster at 1062.; Decision 3618, selection line 10424: the escape episode reaches two observed DM-100s with eight health.; Decision 3621, selection line 10436 and accepted transition line 10437: another door search reverses through 679 and ends in confirmed fatal lightning.; tools/policy_nodes.py:93-116; tools/dm100_escape.py:choose: visible targets previously reached new-door selection without an exposure prerequisite.
  - Disposition: implemented

## Lessons for the next run

A visible caster is not necessarily able to shoot through observed walls. Check conservative current and remembered lightning exposure before starting another door escape; preserve actual-exposure responses, mandatory pickups and bounded recovery.

Update: **accepted**.
