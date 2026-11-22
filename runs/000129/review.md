# ShatteredAI run 000129

Played commit: `7614640589cb4b130701cc0deb8c21fbefd0e97e`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died from a bone explosion after fighting a necromancer’s summon

## Improvements since the last run

- When badly wounded and invisible, the bot no longer abandons that protection for a last-resort attack just because withdrawal fails. It still tries healing, emergency transport and ordinary retreat.

## Incoming learnings

An empty escape route must not silently turn defensive invisibility into an attack. Preserve observed protection and report genuine planner exhaustion when no rescue is admitted. The next progress repair needs an earlier verified retreat or a bounded blocker-clearance plan funded by public protection, charge and damage evidence; target distance does not contain every cursed-wand effect.

## Analysis

The recorded death was caused by a bone explosion: decision 3628 attacked the adjacent wounded summon at 7 HP, and accepted transition 10547 reduced HP to zero. An earlier, actionable defect appears at decision 3614 (selection 10498): after defeating the doorway summon, the bot saw its surviving necromancer and held one usable staff charge, but doorway preparation preempted an admitted stationary shot with a wait. Decisions 3614–3618 advanced time while the caster approached and replaced its minion; subsequent retreat lost more health. The selecting chain is tools/policy_tree.py:26, tools/mage_policy.py:1180 and tools/doorway_tactics.py:129–164 in the played source. A reduced public-input fixture with explicitly supplied hold bookkeeping reproduces the preceding doorway attack and the erroneous wait; this is not a complete runtime reconstruction. The proposed correction intercepts a lone visible summoner from an otherwise valid hold using existing magic/thrown admission, without moving or breaking invisibility. Original-source regression: seven tests, two expected assertion failures. Candidate: seven passing tests; full suite: 1,926 tests passed with four skipped. This establishes selection behavior, not a guaranteed kill or survival. Unknown potions and post-death equipment revelations were not used.

## Recommendations

- **000129-doorway-summoner-interception — Intercept a lone visible necromancer from an established doorway hold instead of waiting for another summon.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 3613, selection 10495 and accepted transition 10496: doorway summon disappears and HP falls from 41 to 32.; Decision 3614, selection 10498: visible necromancer at 529, open door 534 and one usable staff charge; doorway preparation selects wait.; Decisions 3614–3618, selections 10498–10506: five waits advance time; decision 3619 at 10508 sees a replacement summon.; Decisions 3622–3623, accepted transitions 10525/10530: retreat reduces HP from 27 to 11; decision 3628, accepted transition 10547, ends in death.; tools/doorway_tactics.py:132–145; tools/test_shattered_doorway_summoner_interception.py: original assertions fail, candidate passes.
  - Disposition: implemented

## Lessons for the next run

A doorway controls approaching melee enemies, not a summoner’s ability to replace them. When the minion is gone, use an already admitted stationary ranged attack on the visible caster rather than granting free lure turns. Keep the established bank, protection, resource and targeting checks; do not assume the shot kills or the room is cleared.

Update: **accepted**.
