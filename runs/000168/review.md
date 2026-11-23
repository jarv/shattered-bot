# ShatteredAI run 000168

Played commit: `608aa10eb010031ddabd3a7fd0915040a0b05327`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now abandons a DM-100 lure-waiting spot if another observed attacker can hit it, including before its first wait. Breaking the caster's line of sight alone is no longer enough.

## Incoming learnings

Breaking one caster's sight does not make a waiting square safe from another attacker. Check current contact and ranged exposure before the first lure wait, not only after damage arrives. A conservative veto is not evidence that the downstream action will save the hero.

## Analysis

This was a living-hero planner failure, not a death. Decision 3172's accepted transition (log 9272) reaches doorway 1150. Decision 3173 (log 9274) publicly observes exit 1074, summoning trap 1114, upgrade scroll 1155 and a sleeping thief at 1156; known levitation is already carried. The bot retreats and continues other exploration. The initiating blocker is therefore not simply failure to discover stairs: the observed stair approach is quarantined with a mixed chasm/trap chamber. tools/summoning_tactics.py:71-87 floods the observed chamber; tools/special_rooms.py:103-107 excludes it, and tools/survival_policy.py:436-465 removes its approach from ordinary paths. Deliberate summoning preparation refuses floors beyond four. Flight preparation also has independent health, actor, route and room-exclusion requirements; its existing journey controller plans loot round trips, not protected stair transitions. Reduced public-snapshot helper probes reproduce the excluded approach and declining preparation, but are not recorded runtime memory. A complete historical policy-state reconstruction was attempted but is not certified here. At decision 3305, accepted log 9653 confirms healing from 44 to 62 HP while remaining at 1104; decision 3306, log 9654, exhausts planning with the hero alive. Four starving wall searches and last-resort healing are downstream symptoms. No patch or regression is submitted: a safe protected itinerary preserving mandatory upgrade pickup, actual levitation verification, fresh enemy checks and interruption/return handling has not been established. Simply allowing chamber entry, treating stairs as loot, increasing search limits or bypassing quarantine would not supply that contract. Source browsing resolves the omitted-exit and selecting-chain ambiguity, but does not certify a safe replacement.

## Recommendations

- **000137-summoning-exit-quarantine — Establish a verified protected progression plan when summoning-room quarantine encloses the stair and mandatory upgrade approaches.** (high, deferred): Revalidated here, but not safely repaired. The concrete blocker is a missing executable mixed-hazard flight/pickup/stair transaction, not missing source or an unidentified levitation supply. Existing flight planning retains ordinary-ground room exclusions, requires a loot endpoint and a protected return, while the final movement guard independently refuses summoning-room entry. The first doorway observation also includes a sleeping thief beside the upgrade. Neither removing these exclusions nor substituting the stair for a reward proves fresh enemy safety, buff duration, mandatory pickup or interruption recovery. Next derive paired doorway-1150 and terminal fixtures, validate a bounded preparation-only return with fresh arrival observations, then establish an actual-buff-verified itinerary that collects scroll 1155 before explicit descent at 1074 and retains an admitted abort route. Require baseline-red/candidate-green regressions for missing protection, enemy interruption, door reclosure, expired duration and failed pickup receipts. Do not weaken quarantine or waive mandatory progression pickup.
  - Evidence: Decision 3172, accepted log 9272: arrival at doorway 1150.; Decision 3173, log 9274: exit 1074, summoning trap 1114, upgrade scroll 1155 and sleeping thief 1156 are public; known levitation is carried.; Decision 3173, accepted log 9275: retreat to 1149 rather than protected progression.; Decision 3305, accepted log 9653: healing advances time and raises HP without resolving the route.; Decision 3306, log 9654: planner exhaustion with the hero alive.; tools/summoning_tactics.py:71-107; tools/special_rooms.py:103-107; tools/room_tactics.py:200-313; tools/mage_policy.py:403-415.
  - Disposition: deferred

## Lessons for the next run

Distinguish an unobserved exit from an observed exit whose approach is excluded. Investigate the chamber's protection and pickup transaction before spending missing-exit searches. Known levitation is a preparation resource, not evidence that a hazardous crossing or mandatory pickup has succeeded.

Update: **review-only**.
