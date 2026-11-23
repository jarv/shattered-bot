# ShatteredAI run 000191

Played commit: `9573849df7d393913bf5d20abc0e20aa38561d76`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot remembers when a sleeping enemy guards optional food, even after the enemy leaves view. It can continue shopping instead of turning back, while keeping the food unfinished and preserving required pickups.

## Incoming learnings

Losing sight of a known sleeping enemy must not restart optional food collection that reverses existing shopping. Keep unfinished loot honest, preserve mandatory progression pickups, and clear remembered guards only through fresh public evidence.

## Analysis

The hero remained alive at 24/30 HP when the planner stopped. The initiating defect was conflicting escape rules: toxic-gas escape chose a dry piranha bank, and special-room escape returned to the gas threshold. Decision 1033, log lines 3164–3166, enters bank 396; decision 1034, lines 3167–3169, reverses to 451. Repetition eventually exhausted the navigation guard at decision 1046, lines 3205–3208. The clock advanced during this loop. The preceding unknown-potion test was only a hypothesis before consumption; its observed gas effect, not an assumed identity, informed escape. Nearby enemies do not establish the source of the final damage. The proposed narrow correction excludes recognized gas-free special-room hazards from gas-escape routes. A reduced public-geometry regression fails on the original selector and passes after correction; the full suite passes 2101 tests with four skips. Snapshot probes and fixtures are not recovered runtime memory, and no later observations were supplied after a changed selection. The adapter supplies changed files; the empty files field is intentional.

## Recommendations

- **000191-gas-pool-escape — Prevent toxic-gas escape from selecting recognized hazardous clear ground and reversing special-room retreat.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1033, log lines 3164–3166: gas escape enters piranha bank 396 despite an observed alternate route through 504 toward clear floor 557.; Decision 1034, log lines 3167–3169: room escape reverses to threshold 451.; Decisions 1045–1046, log lines 3200–3208: navigation and recovery guards exhaust with the hero alive.; tools/toxic_escape.py:49–78; tools/special_rooms.py:64–80; tools/survival_policy.py:935–985.
  - Disposition: implemented

## Lessons for the next run

Gas-free ground is not necessarily a safe exit: preserve recognized piranha-bank and other special-room exclusions when choosing a gas escape. Reobserve after each step, retain unfinished loot honestly, and keep terminal exhaustion rather than restoring repeated waits. A corrected selection does not establish successful escape or puzzle completion.

Update: **accepted**.
