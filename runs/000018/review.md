# ShatteredAI run 000018

Played commit: `4062f923afbfb21dabf43c63760229a83d1ef2cb`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved after mandatory strength-potion retrieval stalled

## Improvements since the last run

- The bot no longer treats optional food as a permanent reason to block descent. Uncollected food still remains unfinished, while strength potions, upgrade scrolls, and needed keys retain their pickup requirements.

## Incoming learnings

Separate valuable pickup priorities from mandatory progression. Inspect the actual veto targets rather than trusting its upgrade/strength wording. Keep optional hazard-room food unfinished and logged when descent is otherwise admitted; never infer collection, relax fire safety, or guess potion effects. This isolated gate repair does not establish puzzle success or future survival.

## Analysis

The run ended in confirmed starvation: decision 3903's accepted wait reduced HP from 1 to 0, and the public terminal message explicitly reports starvation (log lines 11150–11151). The initiating dead end appeared after the awareness well revealed a potion of strength at cell 999 (decision 2826, line 8000). At decision 2827, recorded diagnostics show this mandatory target outside current paths, with trapped or locked component boundaries and no general threat or inventory veto (line 8002). Descent was refused, then fallback drank the waterskin and subsequently spent advancing turns waiting, interrupted by other actions. Complete source inspection resolves an important ambiguity: tools/priority_resources.py already offers guarded puzzle preparation when ordinary pickup is unavailable; this is not simply a missing call. Independent hunger, staging, protected-trip, and potion-protection requirements remain. No patch is supplied because no validated alternative establishes all required admissions at the initiating state. Reduced snapshot probes are not recovered runtime memory and cannot certify a replacement. The original full suite passed 1540 tests, with four skipped; no new regression or baseline-red/candidate-green comparison is claimed.

## Recommendations

- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): This recording does not resolve the earlier pool-specific admission gap. The needed evidence remains a recorded-input-validated preparation state demonstrating a safe dry test bank, budgeted protected trip, and protection of other carried potions, or observed access to non-drinking identification. A strength-room diagnosis does not certify that pool repair.
  - Evidence: Run 000013: decisions 3014–3016 and 4063, retained backlog evidence.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish an admitted preparation route for the mandatory strength potion instead of exhausting resources in fallback.** (high, deferred): Complete source browsing resolves the selector and helper chain, but not a safe replacement. Recorded diagnostics establish the target and route veto, not an admitted unknown-potion preparation. Needed follow-up is an offline policy state validated against earlier recorded selections and a fixture demonstrating a safe approach/test bank, bounded protected strength retrieval, and protection of the other potions, or observed non-drinking identification. Snapshot-only probes do not establish these conditions; changing movement, potion assumptions, hunger admission, or the mandatory pickup gate would be speculative.
  - Evidence: Decision 2826, log line 8000: publicly revealed strength potion at cell 999.; Decision 2827, log lines 8002–8005: unreachable mandatory target, descent veto, and waterskin fallback.; Decisions 2829–2854, log lines 8009–8084: repeated advancing fallback waits.; Decision 3903, log lines 11150–11151: accepted wait and explicit starvation death.
  - Disposition: deferred

## Lessons for the next run

Distinguish a genuine mandatory strength target from optional food. Inspect recorded route boundaries and preparation admissions before changing selection. A supply fallback already exists; the next investigation needs an offline, recorded-input-validated state and a safe staging, protected-trip, and potion-protection fixture. Do not waive progression pickup, guess potion effects, or shorten waiting and call the problem solved.

Update: **review-only**.
