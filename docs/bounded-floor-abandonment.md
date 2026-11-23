# Bounded floor abandonment after planner incidents

This is an operator-authored runner recovery path, not permission for automated
reviews to edit protected execution or validation files.

## Scope

After ordinary tactical and until-death recovery have declined, the production
survival runner may replace a `PlannerStuck` stop for optional-room or navigation
exhaustion with an observed route to known downstairs. Other failures, including
ranged exposure and mandatory potion discovery, retain their explicit stop.

The runner logs the original observation, reason, decision index and failed
policy report **before** selecting recovery. Run-owned diagnostics survive policy
transaction rollback. A recovered incident is not reclassified as a successful
planner decision.

The recovery remains committed to one stair target, but yields to the normal
survival policy for enemies, warning cells, harmful buffs, menus or loading.
Every subsequent navigation input rechecks current safety and hard gates.
Recent threats or unexplained damage do not authorize a stair rush.

Hard gates include:

- Known mandatory strength/upgrade pickups, held strength and unresolved unknown
  potion discovery.
- Owned potion stashes, trap payload returns, room journeys, drop plans, potion
  probes, burn plans and pending item menus.
- Already-owned Ghost reward retrieval and user-requested strict loot completion.
- Unknown terrain, traps, plants, effects, blocked rooms, occupied cells, locks,
  forbidden escape reversals and unaffordable hunger cost.

Optional rewards are recorded as deferred, never collected or certified clear.
The existing pathfinder does not route through another stair transition.

## Limits and receipts

One admitted episode per depth/branch; at most 64 accepted actions and eight
accepted inputs without route progress. Proposals do not consume these counters.
Survival interruptions count toward the same finite episode, rather than
creating an unbounded wait controller. An explicitly rejected API action aborts
the episode without recording accepted progress.

Success requires an accepted recovery input targeting the chosen downstairs
followed by an observed depth+1 transition in the same branch. Merely reaching
the stairs, selecting a route or proposing descent is not success.

## Evidence

`decisions.jsonl` records `planner_incident`, links recovery decisions through
`planner_recovery_incident`, and logs accepted `planner_recovery_update` receipts.
The final outcome retains `planner_incidents`, `planner_incident_count` and
`planner_recoveries_succeeded`, alongside the actual eventual outcome.

Supervisor review must retain these incidents and their causal context, and
require a high-priority repair recommendation even if recovery descended and
the hero later died normally. Quota-skipped reviews leave original evidence
available. No survival or win-rate improvement is inferred from a synthetic
sequence or an admitted first action.

## Saved-recording checks

Offline bookkeeping with an action-checking observation adapter consumed saved
observations only while proposed inputs matched the recording. No game/API was
started, and no historical follow-up was supplied after an alternative input.

- Run 178: all 1,122 recorded action inputs matched; the terminal piranha-room
  failure then selected cell 174 as the first bounded descent-route action.
- Run 180: all 1,137 recorded action inputs matched. Recovery still declined
  because an observed mandatory progression/key pickup remained.
- Run 173: all 674 recorded action inputs matched; mandatory potion discovery
  still ended explicitly rather than being waived.
- Runs 179 and 170 diverged before their terminal failures under the newer
  policy source. Their selecting memory was not validated, so no terminal
  recovery claim is made for them.

Synthetic runner tests independently verify accepted movement and descent
receipts, eventual outcome separation, no floor-clear credit, bounded stalls,
API rejection, hard-gate negatives and survival preemption.
