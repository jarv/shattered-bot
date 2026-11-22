# ShatteredAI run 000151

Played commit: `66f762c63be08211e6025f9b230143b79a4fd163`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now recognizes visible adrenaline as a speed boost when judging enemy pursuit and retreat routes, even when the enemy's description has not changed.

## Incoming learnings

A visible adrenaline icon is speed evidence even when an enemy description is unchanged. Count its faster approach conservatively, but do not treat a nominal single-attacker endpoint as a persistent refuge or claim that improved risk estimates prove survival. Preserve health, hazard and mandatory-pickup gates.

## Analysis

The hero remained alive at full health when the planner exhausted after the fetid-rat fight. Decision 747's accepted transition (line 2199) shows the public quest-completion message, increased experience and no remaining visible rat. Decision 748 (line 2200) then blocks descent because the ghost reward is pending. Source-pinned offline reconstruction matches decisions 0–747 and reproduces the blocker: a retained retreat commitment makes the ghost-return controller decline every route, although the observed return through cell 779 does not reverse its protected edge. This is reconstructed bookkeeping, not recorded runtime memory. The proposed focused correction permits guarded reward return while preserving escape memory and refusing reversed edges anywhere along the return route. Threat, health, hazard, pickup and terminal-exhaustion gates remain. The new regression fails on original policy with the expected assertion and passes on the candidate; the full suite passes 1,979 tests with four skipped. Candidate reconstruction first differs at decision 748 and stops there. Selecting a return action does not establish reward collection or later survival.

## Recommendations

- **000151-ghost-escape-return — Allow guarded ghost-reward return along routes that do not reverse protected retreat edges.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 740, accepted line 2182: retreat from 781 to 780 establishes the protected edge.; Decision 747, accepted line 2199: public quest-completion evidence appears with the hero still at full health.; Decision 748, line 2200: pending ghost reward causes terminal planner exhaustion.; tools/ghost_quest.py:79-86 blanket commitment veto; tools/mage_policy.py:477-478 mandatory reward gate.; Offline reconstruction matches decisions 0–747; candidate first changes decision 748 to the nonreversing return through 779.
  - Disposition: implemented

## Lessons for the next run

A retained retreat commitment should protect its directed escape edges, not exclude unrelated guarded routes to a mandatory reward. Keep the reward pending until public collection evidence arrives, and revalidate every subsequent observation.

Update: **accepted**.
