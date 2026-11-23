# ShatteredAI run 000171

Played commit: `8219a47f75cb83e79df91ded422476853b55bd7f`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died after prolonged caster and skeleton pressure

## Improvements since the last run

- Before fleeing to a known doorway, the bot now checks that the far side offers a usable step out of the DM-100's firing line. It still permits scouting when that side has not been observed.

## Incoming learnings

Before committing caster flight to a known doorway, verify that its observed far side can support the required cover step. A reachable door is not itself a refuge. Unknown banks still require scouting and fresh arrival checks; available charges alone do not prove a clear shot.

## Analysis

The hero died after prolonged caster and skeleton pressure. Decision 3555's accepted transition (log line 10376) reduces HP from five to zero during a wand attack; the exact damage source is not established. An earlier selecting defect is supported: decisions 3486, 3490 and 3492 approach a visible necromancer while below half health, keeping contact with its skeleton. At 3490, the approach loses health and is immediately reversed by retreat at 3491, before being repeated at 3492. The necromancer helper vetoed wounded contact approaches only for remembered casters, not visible ones. Independent public-observation helper probes reproduce these original choices; they are not recovered whole-run memory. A focused correction extends the existing veto to visible-caster approaches while retaining immediate admitted caster attacks and existing withdrawal checks. The new regression fails on the original policy and passes on the candidate; the full suite passes 2,041 tests with four skipped. This establishes a local selection repair, not survival, a confirmed killer, or a successful counterfactual escape. Changed files are supplied through the trusted adapter.

## Recommendations

- **000171-visible-necro-contact — Apply the wounded contact-approach veto to visible necromancers as well as remembered sightings.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3486, selection line 10167 and accepted line 10168: wounded bypass remains beside the supported skeleton.; Decision 3490, lines 10179-10180: approach from 556 to 557 lowers HP from 21 to 20.; Decision 3491, lines 10182-10183: retreat reverses that step and HP falls to 17.; Decision 3492, lines 10188-10189: the same wounded approach is selected again.; tools/necromancer_tactics.py:98-158; tools/unit_strategies.py:68-70,87-119.
  - Disposition: implemented

## Lessons for the next run

Seeing a support caster does not justify wounded movement beside its minion. Keep immediate admitted caster attacks available, but prefer existing contact-free withdrawal over exposed approach steps. A spacing choice alone does not prove lasting safety.

Update: **accepted**.
