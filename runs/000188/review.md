# ShatteredAI run 000188

Played commit: `0d82ea4e758c7b9de0fc0088f18add45699252f8`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot distinguishes exhausted optional exploration from safety and preparation blockages before attempting a fallback descent.
- For partly observed red-sentry rooms, the bot can scout from ordinary ground before reconsidering preparation. Fresh observations are still required before testing potions or entering hazardous flooring.

## Incoming learnings

Do not reward a just-left escape door as a new withdrawal destination. Keep route protection, remembered-threat checks and mandatory key collection intact; validate actual progress after any changed withdrawal rather than assuming a safe escape.

## Analysis

The hero remained alive at 48/50 HP. The terminal failure was mandatory entrance-shop search exhaustion, not an observed death (decision 2686, lines 7805–7806). A separate, directly evidenced bookkeeping defect appears earlier: decision 2540 reaches branch target 944, with an explicit accepted arrival receipt at line 7384. Corridor search then preempts shopping at decisions 2541–2544. Decisions 2545–2547 still attribute three more shop inputs to that already reached target (lines 7396–7404). The search commitment survives arrival because tools/objective_planning.py:observe increments progress but originally never releases it; tools/shop_tactics.py:visit_entrance_shop subsequently resumes the stale commitment before selecting fresh work. The proposed narrow correction releases only the matching travel target on accepted arrival. It does not certify a shop visit, door inspection, loot collection or safe alternative route, and retains the 80-input bound and terminal stuck outcome. The new deterministic public-evidence fixture fails its arrival assertion on original source and passes on the candidate; all 2093 Python tests pass, with four skips. This establishes a receipt repair, not successful shop discovery or prevention of the terminal failure. Returning along that dead-end corridor may still be necessary; these three movements are not proven avoidable. The initiating terminal problem is a mandatory shop search whose admitted traversal exhausts its global allowance before remaining entrance branches are checked. Separately, decision 1531 records unresolved piranha-chest preparation (line 4513); fallback crosses to the next floor at decision 1578 (line 4722), without chest collection credit. That earlier high-priority incident remains unresolved by this focused change.

## Recommendations

- **000188-shop-arrival-commitment — Release completed shop-search travel commitments before corridor-search or safety preemption can send the hero back.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2540, lines 7382–7384: branch target 944 is reached and explicitly credited as an accepted arrival.; Decisions 2541–2544, lines 7385–7395: required corridor search moves onward and completes.; Decisions 2545–2547, lines 7396–7404: three further inputs remain attributed to the previously reached target 944.; Decision 2686, lines 7805–7806: entrance-shop search exhaustion stops the living planner.; tools/shop_tactics.py:84–119,134–140; tools/objective_planning.py:78–114.
  - Disposition: implemented
- **000188-shop-search-envelope — Establish an entrance-search itinerary that makes progress within its existing allowance without skipping the store.** (high, deferred): The arrival receipt patch does not establish a repair for the search envelope. Public observations do not identify which remaining unopened branch contains the store, and no alternative branch order or complete admitted itinerary has been validated within the existing allowance. Changing the limit, skipping the store, or reclassifying this as abandonable navigation would mask the failure. Next reconstruct through the first entrance-component expansion, derive its observed door/frontier graph and interrupted key-detour costs, and test a rooted, remaining-budget-aware itinerary on copies with existing route and fresh-arrival checks. Do not feed later recorded observations after any changed selection.
  - Evidence: Decisions 2530–2684: entrance-search work expands across multiple branches and is interrupted by combat and mandatory key collection.; Decision 2684, lines 7799–7801: target 776 remains unreached at cell 738.; Decision 2686, lines 7805–7806: the search allowance is exhausted while observed doors remain unchecked.; tools/shop_tactics.py:143–240; tools/mage_policy.py:1386–1387.
  - Disposition: deferred
- **000102-pool-discovery-admission — Establish an executable preparation and retrieval transaction for the earlier unresolved piranha chest.** (high, deferred): Unaddressed by the single arrival-bookkeeping correction. The concrete safety gap is a protected identification-and-chest-return transaction: unidentified colors do not establish invisibility, and the incident supplies no admitted trial bank with carried-potion collateral protection and a duration-funded return. Next derive paired first-pool and incident fixtures from the public terrain and selecting bookkeeping, then validate fresh bank/stash admission, actual protection duration, interruption recovery and accepted chest pickup. Do not guess potion effects, waive the chest or treat fallback descent as collection.
  - Evidence: Decision 1531, line 4513: the original incident reports an uncollected piranha-room chest at 1086.; Decision 1531 public inventory: magenta, ivory and silver potions remain unidentified; no known invisibility or nonconsumptive identification item is carried.; Decision 1578, accepted line 4722: fallback changes floors without collection credit.; tools/puzzle_supplies.py:prepare_supplies; tools/room_tactics.py:plan_journey; tools/mage_policy.py:descent handling.
  - Disposition: deferred

## Lessons for the next run

Release a travel commitment when its matching accepted arrival is observed, even if another controller immediately takes over. Keep arrival separate from shop visitation, hazard admission and collection. Receipt repair does not prove the store or piranha chest will be reached.

Update: **accepted**.
