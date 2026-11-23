# ShatteredAI run 000176

Played commit: `5765bc6462a77c17a3434673bc842e125a7789c0`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died to lightning after an unidentified potion caused paralysis

## Improvements since the last run

- The bot now reassesses prolonged retreats from multiple enemies and can use a limited, safety-checked intervention before continuing to retreat, including in regular games.

## Incoming learnings

A bounded pursuit intervention must remain reachable when the multi-enemy retreat controller preempts preparation, including regular mode. Preserve verified sight breaks, emergency rescue priority, known-charge checks and intervention limits. A geometric retreat endpoint is not evidence that pursuit has ended.

## Analysis

The initiating failure was an unidentified-potion experiment for a levitation room. Decision 2779 (line 8158) staged at dry floor 762. Decisions 2780–2781 tested potions that revealed haste and healing. Decision 2782 (selection 8167, accepted transition 8168) drank unidentified bistre at full health; the clock advanced 27 turns and HP fell from 55 to zero without another selection. Public effects show paralytic gas, repeated paralysis, and an explicit lightning-bolt death message. The attacker is not established. Azure became known as levitation only after death. The selecting chain is rule-preparation through tools/mage_policy.py:1377 to tools/puzzle_supplies.py:899–967. Its bank check verifies nearby terrain and exits, not the ability to act after paralysis. Isolated original-source helper probes admit the recorded bank; they are not reconstructed runtime memory or a replay. No patch is proposed: the missing safety witness is executable identification or verified gas-immunity preparation before testing. The recorded inventory and geometry do not establish either, and a bank veto or speculative relocation alone could replace death with mandatory-discovery exhaustion. Original tests pass (2,053 run, four skipped); no red/green repair claim is made.

## Recommendations

- **000176-paralysis-test-admission — Require executable identification or verified paralysis-safe preparation before admitting unknown room-potion tests.** (high, deferred): Source and full-log inspection establish the admission gap, but not a safe replacement. The fatal public snapshot has no active gas immunity or available nonconsumptive identification item; no verified preparation transaction covers continuous paralysis. Water, alternate exits or mind vision alone do not prove recovery. Next derive paired approach/activation fixtures and validate an identification or duration-checked gas-immunity prerequisite with fresh arrival, enemy-interruption and recovery checks before implementing it. Preserve mandatory pickup, potion protection and explicit planner exhaustion; a blanket veto or speculative movement is not certified here.
  - Evidence: Decision 2779, selection line 8158: preparation moves toward dry bank 762.; Decisions 2780–2781, accepted lines 8162 and 8165: haste and healing tests leave levitation unresolved.; Decision 2782, selection 8167 and accepted transition 8168: unknown bistre drink advances 27 turns, with paralysis, paralytic gas and lightning death.; tools/puzzle_supplies.py:138–162,899–967,988–1060: geometric bank admission precedes recovery that needs a later observation.
  - Disposition: deferred

## Lessons for the next run

An empty visible room, full health and walkable exits do not establish safe unidentified-potion testing: paralysis can consume many turns before the next decision. Separate protection of carried potions from protection of the hero, and never treat post-death potion identities as prior knowledge.

Update: **review-only**.
