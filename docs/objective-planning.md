# Preparation objectives and progress

The reactive safety/combat tree remains the action admission authority. The
objective layer schedules preparation and records why a required task cannot
currently run. It does not infer potion colors, waive collection, or certify
hazard protection from an intended action.

## Structured prerequisite selection

`tools/objective_planning.py` provides `Result` with `ready`, `blocked`, `paused`,
`complete`, and `exhausted` states. `resolve` tries ordered prerequisite providers
and records each decline. Unselected providers run transactionally: their local
resource claims and pending plans are rolled back. Dependency cycles produce a
blocker rather than recursive execution. Successful providers return ordinary
one-input decisions; safety arbitration may preempt them on the next observation.

Potion discovery now explicitly tries existing room preparation, the specialized
sentry reveal, and known general reconnaissance before declaring missing room
supplies exhausted. Its report names missing potion, room kind, observed location,
held count, and any active retrieval. Missing bank preparation separately tries
return travel and reconnaissance. Known mapping resources are bounded by the
existing per-floor attempt record; revealing geometry is not identification.

Unresolved reservations remain obligations. In particular, this layer does not
drink the only possible purity supply far from a gas-room reward without an
admitted protection/return plan. Run 79's exact inventory-protection dead end is
not claimed solved merely by adding structured scheduling.

The subsequent run-79 storage repair separates drinking-site admission from
storage-site admission. An observed grass pocket can hold other potion colors
when reachable within the existing stash budget and outside a conservative
test-fire footprint. Unknown terrain is treated as potentially flammable;
cardinal fire propagation follows the pinned `Fire.evolve` implementation.
Freezing does not diffuse beyond its seeded footprint. Arrival and pre-drink
checks revalidate collateral protection. Existing drop and retrieval receipts
remain mandatory. Gas-room tests may keep an isolated same-color stack while
whole stacks of other colors are protected.

In the original D276 observation, bank 241 can use storage 327 or 355. The old
admission rejects the inventory-protected experiment; the new admission selects
travel to bank 241. Sequence tests separately verify whole-stack drop, return,
and retrieval. This establishes preparation feasibility, not a replayed room
completion.

## Transit versus experiment

Returning to a remembered preparation area uses a terrain-constrained path search
and fresh visible next-step checks. Transit can span multiple observations,
including opening ordinary doors. The previous 12-input local return restriction
is replaced with:

- a maximum of 64 accepted transit inputs;
- eight consecutive inputs without observed progress;
- remaining route length within the remaining total allowance;
- an independently admitted round-trip hunger estimate plus preparation reserve.

The remembered receipt must match floor, branch and potion inventory. Arrival
always reruns current drink-bank and stash admission. Travel does not start a
probe, grant immunity, or credit collection. The conservative inventory matching
remains; a changed inventory may still need a newly established preparation area.

## Persistent shop search

Shop scouting retains its admitted frontier/door target across unrelated input
preemption. It drops the target on arrival, an existing arrival receipt, an unsafe
or inaccessible route, newly observed shop stock, or target-budget exhaustion.
Six consecutive non-progressing accepted inputs retire that target and allow
another branch. The global 80-input search allowance never resets on a target
switch. A proposal or rejected input no longer spends the allowance.

Progress is observed movement along the proposed route, a newly opened door,
or newly revealed geometry. A shop is still visited only from actual observed
proximity to stock or keeper; budget exhaustion never marks it visited.

## Receipts and diagnostics

The runner invokes `objective_planning.observe` only after acceptance and logs
`observed_objective_progress`. A receipt is attached to the selected decision,
not just mutable policy state, so a replacement action cannot claim progress.
Floor/branch changes and mismatched actions invalidate receipts. Repeated
observation IDs do not double-count. Objective state resets on floor changes.

Reports expose `objectives` and `objective_progress`. Terminal output additionally
retains `failed_objective_attempt` from before transactional rollback. This keeps
the actual selection-time blockers without committing an unexecuted plan.

## Validation

Sequence tests cover interruption/resumption, rejected/preempted proposals,
duplicate receipts, opening doors without movement, resource-budget changes,
long transit followed by failed fresh bank admission, failed-target replanning,
dependency cycles and transactional provider declines. These are deterministic
public-observation scenarios, not game replays or claims of improved win rate.
