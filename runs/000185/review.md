# ShatteredAI run 000185

Played commit: `8b66faf3adcaf918c67df19dac1c25a12d730044`

Outcome: blocked

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Blocked returning from a gas room; hero still alive

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Incomplete sentry geometry needs an explicit preparation-only reconnaissance prerequisite, not indefinite supply reservation. Validate ordinary-floor reobservation and door closure before selecting a return; require fresh geometry, potion protection, actual effects and collection receipts before testing or retrieving rewards. Never assign effects to unknown colors or replace planner exhaustion with idle waits.

## Analysis

The run ended blocked, not dead: the last accepted action left the Mage at 74/75 HP with purification active. The initiating failure was a newly visible necromancer occupying the fixed gas-room return waypoint 481 (decision 4220, lines 12434–12437). The public map at that decision offered a dry, visible alternative through 482, 523 and 522 to the original bank 563. Its four moves fit seven observed immunity turns with the existing two-turn margin. Instead, recovery attacked without moving; the next observation added a skeleton at 482, excluding that later escape. A focused correction now permits a duration-checked, freshly observed dry detour to the same bank, only for an occupied gas-return waypoint and with at most one extra move. It preserves hazard exclusions, protection checks, reward identity and collection requirements. The reduced regression reconstructs the journey from public route selections, not recorded runtime memory; whole-policy reconstruction was not performed. Original source fails the expected assertion; the candidate passes all three new tests and the full suite of 2,078 tests, with four skips. This establishes an admitted alternative selection, not successful escape, puzzle completion or improved survival. No patch content is embedded here; changed policy and the new regression are left for the trusted adapter.

## Recommendations

- **000185-gas-return-detour — Replan an occupied gas-room return waypoint onto a bounded, observed dry route to the same bank.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 4207, line 12408: known purity activation for the protected journey.; Decisions 4216–4219, lines 12426–12433: accepted return toward doorway 439.; Decision 4220, lines 12434–12437: occupied return waypoint triggers an obligation failure, followed by an attack without escape.; Decision 4220 public map: dry alternative 439→482→523→522→563 and seven turns of immunity.; Terminal result, line 12438: blocked by toxic-gas escape exhaustion, with the hero alive.; tools/room_tactics.py:144–173; tools/test_shattered_gas_return_detour.py.
  - Disposition: implemented

## Lessons for the next run

A protected return should not insist on an occupied waypoint when a freshly observed dry detour reaches the same bank within the actual immunity budget. Recheck each subsequent observation; never reuse the earlier empty destination after a new enemy appears, invent collection, or replace planner exhaustion with waiting.

Update: **accepted**.
