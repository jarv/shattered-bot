# ShatteredAI run 000226

Played commit: `660014aa2eeffeba55752b632d4d2d48eb3bcdaf`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When badly hurt and invisible, the bot now lets its protected withdrawal take priority over attacking or luring a nearby magical enemy.

## Incoming learnings

Do not let an early caster-escape controller cancel low-health invisibility before protected withdrawal is considered. Preserve existing movement checks and finite retreat budgets. Selecting a different retreat does not establish survival or successful loot recovery.

## Analysis

The run ended in a planner failure with the hero alive at full health, not an observed death. Decision 666 (log lines 1922–1923) reports mandatory preparation unresolved. Despite the upgrade/strength wording, the upgrade scroll was collected at decision 394 and used at decisions 395–397. The actual terminal obligations were an iron key at 664 and a crystal key at 695, both excluded by the aquarium's water-and-shore safety boundary.

The initiating contradiction is in aquarium preparation: tools/priority_resources.py:203–208 requires the entire water enclosure and border to be currently visible before firing a stationary magic missile. The recorded enclosure contains 81 cells; only 65 were visible at the terminal observation, and no saved observation showed more than 70. Recognized aquariums intentionally do not trigger treasure-pool invisibility testing. Ordinary pickups therefore remained unsafe, preparation returned no action, and mandatory pickup correctly prevented descent. The fallback accepted no recovery actions.

A reduced offline terminal fixture confirmed these exclusions without dispatch or reconstructed runtime memory. The existing small-aquarium tests pass but do not cover this larger enclosure. The unchanged full suite passed 2,228 tests with four skipped. No patch is supplied: dropping fresh visibility would relax an explicit hazard check, and the recording supplies neither a fully visible replacement vantage nor known invisibility. Source inspection resolved the omitted preparation chain; the remaining blocker is establishing a safe replacement admission, not missing controller source.

## Recommendations

- **000226-large-aquarium-preparation — Provide a safely justified preparation path for mandatory keys beside large aquariums.** (high, deferred): The current ranged helper explicitly requires fresh visibility of all 81 enclosure cells; no recorded observation satisfies it. Removing that requirement would relax a hazard check, while guessed movement or unknown potion effects cannot certify an alternative. The next concrete step is a bounded one-shot enclosure certificate, with pinned-source validation of dry-boundary persistence and terrain-changing hazards, followed by a large-aquarium regression and stale-boundary negative cases. Retain live projectile checks, whole-shore exclusion and mandatory pickup receipts. No replacement safety proof or patch is claimed here.
  - Evidence: Decision 357, log line 1064: iron and crystal keys observed beside the aquarium.; Decision 394, log lines 1176–1177; decisions 395–397: upgrade scroll collected and used.; Decisions 664–665, log lines 1915–1919: keys remain observed before the terminal approach.; Decision 666, log lines 1922–1923: mandatory keys unreachable, charged staff available, living hero, no recovery action.; tools/priority_resources.py:203–208; tools/puzzle_supplies.py:79–83; tools/mage_policy.py:460–478.
  - Disposition: deferred

## Lessons for the next run

Keep mandatory keys distinct from already collected upgrade resources. Large aquariums need a separately justified preparation plan: a charged staff and a visible fish do not satisfy the current whole-enclosure visibility requirement. Preserve shore exclusion, honest pickup receipts, potion identification and the terminal stuck-planner label.

Update: **review-only**.
