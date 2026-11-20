# ShatteredAI run 000009

Played commit: `6484516ea91b36f5da4c264d0444a805fad0f05e`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Killed by the great crab after repeated blocked attacks

## Improvements since the last run

- If a mimic reward cannot be picked up, the bot stops repeating the attempt until its inventory changes. It still remembers that the reward has not been collected.

## Incoming learnings

Every reward-specific selector must honor verified pickup refusal for the current inventory. Keep refused rewards unfinished, reopen collection when inventory changes, and distinguish zero-time rejected pickups from subsequent time-consuming recovery. Yielding selection is not proof of a safe alternative.

## Analysis

The completed run died to the great crab, explicitly identified by terminal public text (log line 4218); the final accepted transition records HP 3 to 0 (4217). The initiating policy defect was shared recovery bypassing dedicated great-crab attack admission. Decision 1325 first declines quest combat but attacks a fly, not the crab. At decision 1329 (3824–3826), the quest controller refuses direct crab combat, yet recovery selects melee on the sole observed awake crab; the accepted action advances time and reports blocking. Repeated blocked attacks consume turns and healing before death. Source tracing reaches tactical_recovery.py target reselection and MagePolicy.attack_kind_allowed, which previously protected only fly splitting. The candidate makes crab admission apply to shared attack scoring while preserving public sleeping/invisible openings and the separate doorway workflow. Six deterministic regression checks pass; the original policy fails three assertions. Full unittest discovery passes 1,433 tests, four skipped, using garbage collection between tests after plain discovery encountered memory termination. No full runtime ledger was reconstructed, and no safe replacement, quest completion or survival improvement is established.

## Recommendations

- **000009-crab-shared-attack-admission — Preserve great-crab direct-attack restrictions in shared attack eligibility.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1325, log lines 3811–3813: quest refusal followed by an attack on a fly; Decision 1329, log lines 3824–3826: recovery attacks the awake crab and receives blocking feedback; Decision 1447, log lines 4216–4218: terminal accepted transition and explicit killer message; tools/tactical_recovery.py:130–144; tools/mage_policy.py:790; tools/survival_policy.py:599
  - Disposition: implemented

## Lessons for the next run

Special-enemy attack admission must survive recovery target reselection. An awake great crab is not an ordinary damage-scoring target, and regenerated wand charges do not prove a usable attack. Preserve separate evidenced surprise setups; declining blocked attacks does not establish a safe alternative or quest success.

Update: **accepted**.
