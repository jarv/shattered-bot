# ShatteredAI run 000155

Played commit: `d0e6cd54f80580d5a31314117e72e70d76ecd1fe`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died to an albino rat

## Improvements since the last run

- After exhausting travel to crab ambush setups, the bot can still break sight at its current doorway when the escape geometry and fresh-entry checks allow it. It does not travel to another setup or assume the ambush succeeded.

## Incoming learnings

Distinguish exhausted lure travel from an immediately verified sight break at the current doorway. Preserve accepted-departure and fresh-entry evidence before attacking; an eligible departure alone does not prove surprise or quest success.

## Analysis

The hero died to an albino rat, explicitly identified by the complete public death message at accepted decision 111, log line 404. An earlier policy defect appears at decision 29, line 96: the hero abandons an established single-file hold with 19 HP and four staff charges. The approach predictor invents a sidestep by the rat already occupying the gate, then counts the queued rat in that vacated gate as a second attack slot. This makes preparation yield before its existing hold handler. The selected retreat loses three HP at accepted line 97. The pinned game source shows ordinary contact rats attack rather than sidestep. Offline bookkeeping reconstruction matches all selections 0–29, including actions, reasons, intents and controllers. An isolated candidate probe then chooses the existing stationary hold attack and stops without consuming later observations. A focused correction and new five-test regression are supplied in the working tree; the original policy fails the expected slot-count assertion, the candidate passes, and the full suite passes 1,995 tests with four skips. This establishes an early arbitration repair, not that the alternative would kill the rat or prevent death. Later withdrawal exhaustion and the broader non-choke pursuit problem remain distinct.

## Recommendations

- **000155-contact-rat-choke — Preserve an established choke when false contact-rat sidestep pressure would trigger another doorway retreat.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 27, selection line 89 and accepted line 90: the hero reaches holding square 285 behind door 310.; Decision 28, lines 94–95: an observed entry strike leaves the hero at the hold with 19 HP.; Decision 29, lines 96–97: two queued rats trigger retreat to door 286, losing three HP despite verified single-file geometry.; tools/mage_policy.py:1089–1101,1180; tools/multi_enemy_tactics.py:26–54,84–99; game Mob.Hunting.act:1358–1395.; Source-pinned offline reconstruction matches decisions 0–29; the copied candidate state selects the existing hold attack without dispatch.
  - Disposition: implemented

## Lessons for the next run

Do not count a normal-speed rat already attacking from an established choke as simultaneously sidestepping to make room for another attacker. Keep prospective movement and fast-enemy pressure conservative, and require fresh geometry and existing combat admission before retaining a hold.

Update: **accepted**.
