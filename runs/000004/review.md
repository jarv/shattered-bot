# ShatteredAI run 000004

Played commit: `945d92144e39d48327a18c4b5d191d160bd7576c`

Outcome: dead

Java build: `2d6e7b4f2433e84e361a92fd80e6540d95a663e43b9269b59cc5fa6a7724cce8`

Outcome summary: Died while starving under prison guard pressure

## Improvements since the last run

- Added caustic slime to the bounded weak-target finisher arbitration, with a regression for its existing health, crowding and attempt limits.

## Incoming learnings

Recognized ordinary enemy variants should receive the same bounded weak-target arbitration when their public observations satisfy its gates. Preserve hazard, healing, crowding, attack-admission and mandatory progression-pickup precedence. A selector regression is not evidence of a guaranteed kill or survival.

## Analysis

The hero died while starving under prison guard pressure. Decision 2964's accepted transition records HP 5 to 0; it does not establish the killer. Earlier, entrance-shop search exhaustion caused 201 advancing-time fallback waits on floor six. A separate, directly evidenced defect initiated repeated full-pack loot loops: decisions 2794–2798 repeatedly clicked the persistent pasty without advancing time, and decision 2799 reported a navigation loop. For the upgrade pickup, decision 2828 explicitly reports the occupied floor blocked by prior movement bookkeeping after full-pack refusal. The selecting chain confuses pickup refusal with failed movement. The proposed focused correction retains floor reachability and defers ordinary collection until inventory changes only when an existing public full-pack receipt matches; mandatory resources remain outstanding. A new reduced regression fails on the played policy and passes on the candidate. All 1410 Python tests pass, with four skipped. This does not prove pack relief or survival, and unidentified potions are not counted as known healing. Policy and regression changes are local proposals; files is empty because the trusted adapter derives them.

## Recommendations

- **000004-full-pack-floor — Separate verified full-pack pickup refusal from failed navigation bookkeeping.** (medium, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2794, log lines 7922–7925: persistent pasty and verified full-pack refusal; Decisions 2795–2799, log lines 7926–7944: repeated same-cell pickups and navigation-loop recovery; Decisions 2826–2828, log lines 8028–8036: upgrade refusal becomes blocked occupied floor; tools/survival_policy.py:301–336; tools/inventory_tactics.py:183–191; tools/room_loot.py:19–26
  - Disposition: implemented

## Lessons for the next run

A verified underfoot pickup refusal is not evidence that occupied ground is impassable. Preserve honest loot obligations and hazard checks; reopen ordinary collection after inventory changes without granting acquisition or descent credit.

Update: **accepted**.
