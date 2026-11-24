# ShatteredAI run 000250

Played commit: `3037b51a862e19c2bf7c4ecdb839583ee2295487`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot can now recognize a defeated DM-100 after a close-range disintegration staff blast, using the spent charge and other public evidence. It keeps uncertain threats on record rather than assuming that disappearance means defeat.

## Incoming learnings

A consumed disintegration staff zap can confirm the matching caster is defeated without a new defeat text when Arcane Vision rules out a hidden survivor and conservative public XP, timing and actor checks agree. Retire only that threat; do not credit loot or floor clearance. Healing cannot resolve a stale safety obligation. This receipt repair does not establish a safe cover itinerary or eventual survival.

## Analysis

The hero remained alive at full health when planning stopped. The initiating defect was an icecap seed thrown onto the only return connector, not the final crab fight. Decision 1095 (log 3200) chose the seed; decision 1096 (logs 3202–3204) planted it at 1027. The plant remained visible at decision 1099, excluding the mapped exit at 426 from ordinary paths. Full mapping correctly suppressed further wall searches. Source tracing reaches seed-preparation through tools/policy_nodes.py and tools/seed_tactics.py to tools/seed_strategies.py; its original target ranking lacked an exit-connectivity check. Isolated public-observation probes reproduce target 1027 and show that excluding it cuts both known stairs. These are fixture probes, not recovered original runtime memory. The proposed correction rejects offensive seed targets that sever currently reachable stairs, retaining all existing hazard and collateral checks. A reduced regression fails three assertions on original source and passes on the candidate; the full suite passes 2,289 tests with four skipped. This establishes prevention of the self-sealing proposal, not successful descent or survival. Earlier deferred frontiers and snake routing trouble remain separate observations.

## Recommendations

- **000250-seed-exit-cut — Prevent offensive seed placement from severing the hero's known stair routes.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1095, log 3200: icecap THROW selected from doorway 1099.; Decision 1096, logs 3202–3204: target 1027 receives a publicly observed icecap plant.; Decisions 1098–1099, logs 3208–3211: final zap followed by planner exhaustion with 35/35 HP and the plant still present.; tools/seed_strategies.py: original target ranking; tools/survival_policy.py:436–470,1174–1183.; New reduced regression reproduces the original choke target and validates a bypassable alternative without dispatch.
  - Disposition: implemented

## Lessons for the next run

A seed that has not triggered is still a real obstacle. Before placing a harmful pursuit plant, preserve observed access to currently reachable stairs without assuming the enemy will activate it. Keep mandatory loot unfinished until public collection receipts establish otherwise.

Update: **accepted**.
