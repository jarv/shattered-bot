# ShatteredAI run 000212

Played commit: `01b9b61d23aa77a77e8f0fbc39b395de57cc16cd`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- After a failed potion-stash return, the bot can retry room preparation when it picks up a new, untested potion supply. It still treats the abandoned stash as unfinished.

## Incoming learnings

A failed stash return should not permanently veto independently acquired potion supplies. Retry preparation only after a verified, matching new pickup; keep prior drops unfinished and retain every health, identification, hazard, protection and collection check. Selecting preparation is not proof of puzzle completion.

## Analysis

The hero remained alive at 30/30 HP when planning exhausted. The initiating blocker was an iron key on a revealed toxic gas trap, first exposed around decision 344, not the upgrade scroll mentioned by the generic refusal message. The scroll was collected at decision 372. At decisions 543–544, the resource diagnostic lists only the trapped key; the last waterskin drink advances the clock and restores HP but cannot resolve that obligation. Source inspection and offline bookkeeping reconstruction matched all 544 recorded actions and reasons, then reproduced the terminal veto. Independent non-dispatch probes confirm that existing trap clearance handles shocking or chilling mechanisms, while the remaining levitation preparation has no carried supply. No policy change is proposed: a remote throw is possible, but neither distance nor a clear shot certifies safety from spreading toxic gas. The missing safety certificate is a bounded gas-excluded refuge and verified return after dissipation, not missing selector source. A new expected-action regression would otherwise encode an unsupported safety assumption. Mandatory pickup checks and the terminal planner-failure label remain intact.

## Recommendations

- **000212-toxic-trap-key-preparation — Plan safe preparation for mandatory keys stranded on toxic gas traps.** (high, deferred): No patch is supplied because the pinned gas diffusion rules do not support reusing the existing cold or electrical safety footprint, and no current helper certifies a gas-excluded refuge, dissipation bound, and safe retrieval route. The terminal inventory has no known levitation or purity supply. Source browsing and validated offline reconstruction resolved the selecting-state gaps, but not this safety proof. Next, derive a public-map fixture from decisions 345 and 544 and prove conservative gas reach with unknown boundaries treated adversarially. Only then add remote activation and receipt-checked retrieval with a new original-red/candidate-green regression; never bypass the mandatory key or restore death-waits.
  - Evidence: Decision 344, log lines 976–977: approach exposes the trap beneath the key.; Decision 345, log line 979: iron key remains on a revealed toxic gas trap.; Decision 406, log lines 1138–1139: potion test raises strength without levitation.; Decision 543, log lines 1537–1540: trapped-key veto followed by healing only.; Decision 544, log lines 1541–1543: mandatory-preparation planner exhaustion with a living hero.; tools/priority_resources.py:122–165,229–294; tools/environment_tactics.py:115–142; tools/mage_policy.py:459–478.
  - Disposition: deferred

## Lessons for the next run

A required key on a toxic gas plate needs its own safely bounded preparation plan. Do not reuse a chilling trap's radius check, assume levitation from an unidentified potion, or treat a throwable container as proof of safe gas clearance. Preserve the unfinished pickup until an actual collection receipt.

Update: **review-only**.
