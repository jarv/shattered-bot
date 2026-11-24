# ShatteredAI run 000259

Played commit: `3791b68f188206664a3d2efc46a27662dc445509`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died after repeated recovery waits under great-crab pressure

## Improvements since the last run

- The bot preserves its last known purity potion when its existing confusion-gas escape passes every landing check. It still uses the potion for emergency rescue when that escape is unsafe, threatened or exhausted.

## Incoming learnings

Preserve the last known purity dose when the existing bounded confusion escape passes every landing check. A requested direction is not a guaranteed dizzy landing. Keep mandatory pickup and hazard gates intact. Next, validate original terminal reobservation budgets and safe observation vantages before adding a bounded mandatory-key handoff ahead of spent-room descent; cached gas is neither proof of current danger nor permission to enter.

## Analysis

The initiating episode was a suspicious-chest test followed by mimic kiting and mixed-enemy retreats, not merely the final wait. Decisions 2187–2188 revealed a mimic; decisions 2195–2208 retreated under mixed pressure and ended at cell 408. Recovery fought the mimic and flies before quest combat declined at decision 2220. Its accepted wait advanced the clock and reduced HP from 24 to 19. Healing and dew were subsequently used, but repeated recovery waits continued until the final accepted transition showed 3 HP becoming zero. A great crab and starvation were observed; the recording does not unambiguously identify the final killer. Source inspection explains the contradiction: geometric onward-room checks do not guarantee a later crab-separated escape, while the dedicated crab controller correctly refuses ordinary attacks and adjacent retreat squares. An isolated original-source probe of the decision-2220 public snapshot reproduced the decline and recovery wait. Its only clean adjacent move, 407, remained adjacent to the crab despite having a geometric exit. Two carried foods and later recharged wands do not establish a safe replacement. No patch is supplied: complete source resolves the selecting-chain gap, but original earlier retreat bookkeeping and an executable, unchanged-safety-gated alternative remain uncertified. Existing crab regressions passed all 33 tests; this does not establish coverage of the initiating retreat defect.

## Recommendations

- **000243-crab-room-edge-retreat — Establish an executable crab escape before retreating toward a room edge.** (high, deferred): The terminal public snapshot has no certified non-adjacent escape: only cell 407 is clean, and it remains adjacent to the awake crab. Its geometric exit does not satisfy existing threat-separation checks. No known invisibility is carried; unknown potion effects cannot be inferred. Fresh-memory earlier snapshots select different routes, so original attempt and pursuit bookkeeping cannot be assumed; offline reconstruction validated decisions 0–2174 but stopped before this episode because scratch checkpoint serialization failed. Next remove that checkpointing limitation and extend validation through decisions 2203–2206, then derive paired pre-edge/trapped fixtures and prove an admitted continuation toward an observed exit under unchanged pressure and hazard checks. Only then change endpoint selection and add a positive regression. If no such continuation exists, investigate earlier suspicious-container admission instead of weakening terminal safety or extending waits.
  - Evidence: Decisions 2187–2188, log lines 6278–6281: suspicious-container test reveals a mimic.; Decisions 2195–2208, log lines 6306–6365: mixed-enemy retreats end at cell 408.; Decision 2220, log lines 6399–6401: crab combat declines; recovery waits and HP falls from 24 to 19.; Decisions 2221 and 2239, log lines 6402 and 6455: healing and dew are used.; Decision 2260, log lines 6518–6519: final recovery wait precedes observed death.; tools/great_crab_tactics.py:197–208; tools/retreat_geometry.py:8–41; tools/tactical_recovery.py:190–199.
  - Disposition: deferred

## Lessons for the next run

Do not equate a geometrically connected retreat endpoint with an executable crab escape. Validate earlier accepted retreat bookkeeping and prove a threat-separated continuation before changing endpoint selection. Preserve mandatory pickups, fresh-surprise requirements and hazard gates; food, charges and unknown potions are not evidence of a safe escape.

Update: **review-only**.
