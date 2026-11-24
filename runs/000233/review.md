# ShatteredAI run 000233

Played commit: `75ac3070769b08603efd32a805590f284d98263a`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died under mixed fly, rat and gnoll pressure

## Improvements since the last run

- When an unfinished piranha pool needs invisibility, the bot now uses an admitted stone of intuition attempt to test that missing supply rather than defaulting to strength. The guess does not authorize drinking an unknown potion.

## Incoming learnings

Use admitted non-drinking information opportunities for the missing supply of an observed unfinished pool, not an unavailable default hypothesis. A failed or canceled guess identifies nothing. Preserve fresh bank, inventory-protection, actual-effect and return checks; fallback descent is neither collection nor planner repair.

## Analysis

The hero died under mixed enemy pressure, not planner exhaustion; no planner incidents were recorded. Decision 946, accepted log line 2767, shows HP falling from 3 to 0, but does not identify an unambiguous killer. The initiating defect addressed here appears earlier: at decision 764 (selected line 2183), an empty staff and adjacent gnoll did not dislodge the urgent fly target. Decisions 766 and 944 (accepted lines 2190 and 2759) show subsequent fly melee adding another visible swarm while ordinary contact foes remained. In tools/unit_strategies.py:97–119, species urgency retains the fly target after its dedicated tactics decline; tools/policy_nodes.py:467–469 then carries that target into ordinary melee. The fly guard counts adjacent flies, so one fly plus other contact attackers remains admitted. A deterministic public-observation reduction reproduces this arbitration gap without claiming recovery of original runtime memory. The proposed correction selects an already-admitted ordinary contact melee strike only after existing escape, magic, control and withdrawal options decline. Original policy fails the new assertion; the candidate passes seven regressions and the full 2,246-test suite, with four skips. This establishes selection behavior, not prevention of the recorded death. Post-death item identities were not used to justify earlier actions. The earlier doorway hold failure and recovery depletion are not certified repaired.

## Recommendations

- **000233-mixed-contact-fly-splitting — Prefer an admitted ordinary contact strike over empty-staff fly melee in mixed contact after higher-priority options decline.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 764, selected log line 2183 and accepted line 2184: fly melee despite adjacent gnoll and staff 0/5.; Decision 766, selected line 2189 and accepted line 2190: another visible fly appears while gnoll and crab remain in contact.; Decision 944, selected line 2758 and accepted line 2759: fly melee adds another swarm; HP falls from 10 to 6 with rat and gnoll adjacent.; tools/unit_strategies.py:97–119; tools/policy_nodes.py:467–469; tools/fly_tactics.py:40–68.; New public-reduction regression: original assertion fails; candidate passes seven tests; full suite passes 2,246 tests with four skips.
  - Disposition: implemented

## Lessons for the next run

When magic is exhausted and retreat or control has not produced an action, avoid splitting an adjacent fly if an awake ordinary contact foe already offers an admitted melee strike. Preserve protected enemy tactics, hazard checks, mandatory pickup and honest collection receipts. A visible health bar is not a guaranteed finishing hit, and a different target is not proof of survival.

Update: **accepted**.
