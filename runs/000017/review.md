# ShatteredAI run 000017

Played commit: `f863ff5982edbec54a570e1cb2efe87970181061`

Outcome: blocked

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Blocked by an unreachable ration being treated as mandatory progression

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Known-protection staging does not solve unknown-supply preparation. Establish a publicly justified identification or jointly feasible test-bank, inventory-protection and reward-trip plan before changing admission. Preserve mandatory progression pickup and actual receipt verification; do not infer potion identities from floor generation or post-death revelations.

## Analysis

The run stopped alive after 128 accepted fallback waits, not death or a frozen clock. The initiating defect is a descent-gate category mismatch: tools/priority_resources.py:15–29 includes food in pickup priorities, while the played tools/mage_policy.py:418–430 treats every priority target as mandatory upgrade/strength progression. Decision 3442, log line 9825, records exactly one target: an unreachable remembered ration at cell 157, with eternal-fire buffers on component boundaries. The upgrade at cell 1543 was picked up at decision 3112; decision 3113 shows its quantity rising from one to two and a public pickup confirmation (lines 8863–8866). The erroneous veto then led to near-full-health healing at decision 3442 and waiting from decision 3443 through 3570 (lines 9827–10212). The final accepted wait advances the clock to turn 3483. Complete log and source browsing resolve the misleading progression diagnosis without reconstructing runtime memory. The proposed focused correction excludes food from this unconditional gate while retaining priority pickup, strict loot refusal, honest unfinished-loot deferral, mandatory upgrades/strength and matching keys. A reduced selector fixture, not a replay or a certified replacement route, produced two expected assertion failures on original policy; all five new tests pass on the candidate. The full Python suite passes 1,540 tests with four skipped. No claim is made that this solves the fire room or proves safe subsequent descent. The separate older unknown-supply preparation issue remains unresolved.

## Recommendations

- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): Complete source browsing resolves the selector and fallback chain, but does not establish a safe replacement. The actual initiating inventory has unknown supplies, and no validated alternative simultaneously demonstrates visible dry-bank safety, a budgeted protected trip, and remote protection of the other carried potions. A reduced snapshot probe admitted a hypothetical reward route but did not admit the corresponding test bank or stash. Needed follow-up is an offline, recorded-input-validated preparation state and a fixture demonstrating all three admissions, or observed access to a non-drinking identification resource. Changing only the distance filter, candidate ordering or wait bound would leave independent safety gates unresolved.
  - Evidence: Decision 3014, log lines 8669–8671: return to the dry pool approach; Decision 3015, log lines 8672–8674: mandatory chest veto and near-full-HP waterskin use; Decision 3016, log lines 8675–8677: fallback waiting begins; Decision 4063, log lines 11755–11758: final wait, HP loss and explicit starvation message
  - Disposition: deferred
- **000017-optional-food-progression-gate — Keep food pickup priority separate from mandatory permanent-progression descent checks.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2866, log line 8140: public ration sighting at cell 157.; Decision 3112–3113, log lines 8863–8866: upgrade pickup confirmed by inventory gain and public message.; Decision 3442, log lines 9825–9828: sole veto target is unreachable food, followed by healing at 64/65 HP.; Decisions 3443–3570, log lines 9830–10213: accepted waits advance time, then the run stops alive.
  - Disposition: implemented

## Lessons for the next run

Separate valuable pickup priorities from mandatory progression. Inspect the actual veto targets rather than trusting its upgrade/strength wording. Keep optional hazard-room food unfinished and logged when descent is otherwise admitted; never infer collection, relax fire safety, or guess potion effects. This isolated gate repair does not establish puzzle success or future survival.

Update: **accepted**.
