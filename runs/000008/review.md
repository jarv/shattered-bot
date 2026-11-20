# ShatteredAI run 000008

Played commit: `42c90c4108917a30c1339cec00d711fb67818035`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died during the Tengu encounter after an earlier refused-loot retry stall

## Improvements since the last run

- New multi-enemy doorway staging honors an exhausted pursuit-loss budget; existing validated routes retain their checks. Added a regression.

## Incoming learnings

Honor exhausted pursuit budgets across every controller that starts an unverified doorway setup. Reaching a door without an observed holding square is not successful cover. Preserve honest unfinished-loot accounting and do not treat an offline alternative as proven safe.

## Analysis

The run died during the Tengu encounter; the accepted final targeting transition at decision 4466 (log 12818) changes HP 3→0. The empty death reason does not identify the killer. An earlier initiating selector defect is directly supported: decisions 3185–3187 (logs 8962–8972) receive fresh full-pack refusals for the corrupting whip, with unchanged inventory. Ordinary loot bookkeeping defers that pickup, but rule-preparation's mimic controller immediately retries it at decision 3188 (8974–8976). Repeated retries trigger navigation recovery, then waterskin consumption at decision 3203 and 90 advancing fallback waits at decisions 3204–3293. Source browsing resolves the missing controller chain: tools/mage_policy.py:1131 calls tools/mimic_hunt.py, whose reward branch ignored the inventory-context deferral honored by tools/room_loot.py. A focused candidate repair makes that branch honor the same deferral without completing the obligation or choosing replacement movement. The reduced public-evidence fixture is not reconstructed runtime memory or a gameplay replay. Original-source comparison fails the expected assertions; the candidate passes all four new tests and the full 1,427-test suite, with four skips. This establishes the selector correction, not successful cleanup, collection, or prevention of death.

## Recommendations

- **000008-refused-mimic-reward — Honor inventory-context pickup deferral in the mimic reward selector.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 3185–3187, logs 8962–8972: fresh full-pack refusals and unchanged inventory.; Decision 3188, logs 8974–8976: mimic reward selector retries the deferred pickup.; Decisions 3191–3203, logs 8987–9032: recovery oscillations and fallback dew consumption.; Decisions 3204–3294, logs 9034–9304: advancing fallback waits end with starvation and a meal.
  - Disposition: implemented

## Lessons for the next run

Every reward-specific selector must honor verified pickup refusal for the current inventory. Keep refused rewards unfinished, reopen collection when inventory changes, and distinguish zero-time rejected pickups from subsequent time-consuming recovery. Yielding selection is not proof of a safe alternative.

Update: **accepted**.
