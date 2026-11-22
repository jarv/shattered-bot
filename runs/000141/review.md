# ShatteredAI run 000141

Played commit: `d3334a5880e79fe63e1556f3496939e6ce7fec1e`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Exploration and mandatory discovery must share a preparation reservation: a remembered safe bank is insufficient once exploration disconnects every admitted return. Preserve unknown identities, potion protection, fresh arrival checks and all unfinished pickup obligations; do not solve this by allowing grass or restoring idle waits.

## Analysis

The hero remained alive at 56/75 HP when the planner exhausted its options. Decisions 3681-3682 selected and fired an identified, noncursed magic-missile staff at the only observed actor, a DM-100. The accepted transition at log line 10575 consumed one charge and advanced one turn: level 11 with 56/60 XP became level 12 with 2/65 XP, exactly six earned XP. Arcane Vision was already learned, yet no DM-100 remained in the subsequent public observation. The old receipt required adjacency, unchanged level and complete neighborhood visibility, so it missed this ranged level-up kill. Remembered lightning exposure then blocked preparation, pickup, recovery and exploration at decision 3683 (line 10576). Source inspection supports a focused new receipt using consumed charge, a clear observed projectile ray, Arcane Vision tracking and exact XP rollover; disappearance alone remains insufficient. A reduced public-evidence regression failed two assertions on original source and passed on the candidate. All 1,961 Python tests passed, with four skipped. Only targeting/receipt bookkeeping was reconstructed; original full runtime memory and individual rejected door routes were not recovered. The correction does not certify a replacement movement or future success. Policy and new regression changes are supplied through the trusted change adapter; files is intentionally empty.

## Recommendations

- **000141-arcane-missile-levelup-receipt — Recognize the evidenced Arcane Vision magic-missile level-up kill before stale lightning memory blocks progress.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3681, log lines 10572-10573: known staff selected with Arcane Vision already learned.; Decision 3682, log lines 10574-10575: targeted zap consumes a charge and earns exactly six XP across a level-up.; Decision 3683, log line 10576: no DM-100 observed, but remembered lightning exposure causes planner exhaustion.; tools/combat_observation.py:39-81; tools/policy_nodes.py:93-115
  - Disposition: implemented

## Lessons for the next run

A ranged magic-missile kill can cross a hero level boundary without fresh defeat text. Retire only the matching lightning memory when charge consumption, an observed clear ray, Arcane Vision and exact six-XP rollover jointly confirm the kill. Preserve ambiguity checks, unfinished pickups and terminal exhaustion rather than manufacturing waits.

Update: **accepted**.
