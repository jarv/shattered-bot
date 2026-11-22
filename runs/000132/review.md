# ShatteredAI run 000132

Played commit: `e4628c4abf9e3924f248e370d7d95c8166b79ac0`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Killed by a sewer crab after rage drew converging enemies

## Improvements since the last run

- The bot no longer starts another doorway escape merely because it can see a DM-100 behind walls. It still responds when lightning can reach it or a remembered threat remains exposed.

## Incoming learnings

A visible caster is not necessarily able to shoot through observed walls. Check conservative current and remembered lightning exposure before starting another door escape; preserve actual-exposure responses, mandatory pickups and bounded recovery.

## Analysis

The initiating avoidable risk was decision 761 (selection line 2217, accepted line 2218): the bot read unidentified GYFU despite carrying a readable, known scroll of identify. An intuition attempt had just been cancelled without revealing the rune. The recorded effect was rage's enraging roar; the pinned game source confirms this beckons enemies throughout the floor. The existing identification selector preferred known Identify only for unknown potions, then directly tested unknown scrolls. Converging gnoll, fly and crab pressure followed, with retreat, exhausted charges and splitting-risk melee. Decision 820's accepted transition (line 2446) confirms death and explicitly names a sewer crab as the killer. This attribution does not depend on nearby enemies or post-death item revelations. The candidate prefers known Identify within the existing safe scroll-testing gate and preserves the intended consumable through menu and bag selection. A reduced public-observation fixture is not recovered runtime memory: it matches the original helper's recorded READ choice, then demonstrates the correction without dispatching gameplay. The final regression has four expected assertion failures on original policy and passes all six tests on the candidate. The full suite passes 1935 tests with four skips. This establishes selection behavior, not successful identification or survival in a replacement run.

## Recommendations

- **000132-identify-before-scroll-risk — Prefer known Identify over directly activating an unknown scroll during safe discovery.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 758–760, lines 2211–2216: intuition ends in cancellation without revealing GYFU.; Decision 761, lines 2217–2218: GYFU is read while known Identify is carried; the accepted observation reports rage's roar.; Decisions 767–772, lines 2239–2260: gnoll, flies and crabs converge during doorway retreat.; Decision 820, accepted line 2446: HP falls from three to zero and the public death message names a sewer crab.; tools/consumable_tactics.py:89–119; tools/policy_nodes.py:322–323; new tools/test_shattered_scroll_identify_before_read.py.
  - Disposition: implemented

## Lessons for the next run

Before deliberately activating an unidentified scroll, use a carried known Identify when the same safety gates admit it. Keep potion identification priority, preserve the chosen consumable across bag navigation, and require actual public identification evidence. A cancelled intuition attempt reveals nothing; no visible enemies does not make rage harmless.

Update: **accepted**.
