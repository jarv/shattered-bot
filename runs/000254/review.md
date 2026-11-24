# ShatteredAI run 000254

Played commit: `2c242925a35ad8a4d0e631b9790bc51485420a2d`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

Code changed; no supported improvement summary available.

## Incoming learnings

Thrown weapons can split flies too. An early species-specific throw must not bypass an already admitted ordinary-contact alternative when magic is empty. Preserve escape and control precedence, and distinguish a corrected selection from proven survival.

## Analysis

The hero was alive at full health when the planner stopped. The mandatory target was a golden key, despite the generic upgrade/strength error. The key appeared during combat at D1518 (log line 4407). At D1521 (4416), a revealed summoning trap caused the room containing the key to be quarantined. Terminal diagnostics at D1842–1843 (5355–5361) show that barrier still excluded pickup. A separate spent flame supply prompted descent, which correctly failed the mandatory-key check. Source inspection identifies incomplete summoning-prerequisite delegation in tools/priority_resources.py:265–310 and tools/mage_policy.py:1280–1330. However, delegation alone would not repair this episode: the existing summoning controller rejects the recorded equipment, buffs and three-door geometry. Offline calculations from public maps confirm those exclusions; original runtime memory was not reconstructed. No patch is proposed because useful activation would require an unsupported new containment/protection safety case, not merely a scheduling change. Existing hazard gates and mandatory pickup remain intact. Targeted existing tests passed (27); no candidate or red/green regression was produced. The truncated source comparison exposes only a regression excerpt, so no played-code improvement is attributed.

## Recommendations

- **000254-summoning-key-prerequisite — Plan safe summoning-room prerequisites for mandatory keys instead of reaching an unrelated descent veto.** (high, deferred): No safe useful replacement is supported yet. The priority leaf omits summoning delegation, but the existing controller would still reject cloth armor, the staff's readiness score, current buffs and three observed doors. Repairing delegation alone would not fix this recording. Build a reduced mandatory-key fixture preserving those exclusions, then implement a bounded activation/containment/return plan using publicly known supplies before adding a positive preparation-selection regression. Do not weaken hazard admission, guess potion effects or waive the key.
  - Evidence: D1518, log line 4407: golden key observed during combat; D1521, log line 4416: summoning trap revealed in the key's room; D1842, log lines 5355–5358: key route blocked; healing does not resolve it; D1843, log lines 5359–5361: mandatory-preparation failure; recovery declined
  - Disposition: deferred

## Lessons for the next run

Trace blocked mandatory pickups to their actual room prerequisite before treating unrelated exhausted supplies as grounds to leave. A key behind summoning quarantine needs explicit preparation planning; delegating a controller is not enough when its equipment and containment checks still reject the observed state.

Update: **review-only**.
