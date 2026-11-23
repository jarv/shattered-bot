# ShatteredAI run 000172

Played commit: `54cdfcaff98203618762e4a5bc50545e6a45efa0`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died to a crazy thief after a guard pull and prolonged retreat

## Improvements since the last run

- When badly wounded, the bot now avoids approaching a visible necromancer through its minion's reach, just as it already did for remembered necromancers. Immediate attacks remain available.

## Incoming learnings

Seeing a support caster does not justify wounded movement beside its minion. Keep immediate admitted caster attacks available, but prefer existing contact-free withdrawal over exposed approach steps. A spacing choice alone does not prove lasting safety.

## Analysis

The initiating attrition followed waking a prison guard with the last staff charge: decision 2549 (accepted line 7465) pulled the hero into contact and inflicted cripple. Melee, a small dew drink and a two-turn retreat left 14 HP. During the subsequent escape, decision 2554 (line 7479) continued toward a formerly separated cover destination even though the following guard could now see it. The committed-cover branch omitted endpoint checks already required for fresh guard-cover selection. A partial offline helper reconstruction matches decisions 2553-2554; it is not recovered original runtime memory. The proposed correction reapplies those existing endpoint checks before continuing. Three new regression tests pass after two expected baseline assertion failures; the full suite passes 2,044 tests with four skips. This does not establish lasting escape or death prevention; the first movement remains unchanged. The final accepted transition at line 7639 records death, and the full terminal public message explicitly identifies a crazy thief as the killer. Unknown potion identities were not treated as pre-death resources. The adapter will derive the changed policy and new test from the working tree; files is intentionally empty.

## Recommendations

- **000172-guard-cover-goal-refresh — Revalidate committed guard-cover destinations against current threat positions before continuing.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2549, accepted line 7465: the last-charge attack is followed by a guard pull and cripple.; Decision 2553, line 7475: isolated original helper reconstruction selects cover goal 430.; Decision 2554, selection line 7479 and accepted line 7480: the helper retains goal 430 after the guard follows to 485 and exposes that destination.; tools/ranged_tactics.py:190-207: committed guard cover now applies the endpoint conditions already required by fresh cover selection.; The new regression has two expected baseline assertion failures and passes all three tests with the candidate; the complete suite passes.
  - Disposition: implemented

## Lessons for the next run

A following guard can invalidate a cover destination before arrival. Recheck the destination as well as the route on every committed escape step. Currently admitted cover is not proof of lasting safety or successful escape.

Update: **accepted**.
