# ShatteredAI run 000038

Played commit: `6caa07b56b54c0fbc8a2b537c46608901d6bf804`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died while retreating from skeletons

## Improvements since the last run

- The bot no longer starts a new, unverified doorway escape when its health is already below the limit used to continue that escape. Retreats to an already verified single-attacker position remain available.

## Incoming learnings

Apply an unverified escape plan’s health floor before its first step, not only when continuing it. Reobserve successful crowd control before spending another escape resource. A frightened enemy is still relevant, but its presence alone does not establish an immediate attack threat or a safe teleport destination.

## Analysis

The hero died while retreating, not from planner exhaustion. Earlier, decisions 2093–2094 woke a sleeping DM-100; the attack and subsequent flight consumed health and dew. Later, decisions 2179–2186 spent charges as two skeletons approached. Decision 2187 began repeated retreat at 12 HP. Ten retreats preserved health without resolving pursuit; decision 2197 exhausted skeleton spacing and fell back to unverified movement. Decision 2201 lost five HP, and decision 2202's accepted transition reduced seven HP to zero. The journal does not identify the killer, so a bone-explosion death is not established. Complete source browsing explains the arbitration, but no safe replacement is validated. Offline reconstruction matched actions, reasons and controllers through decision 2093 before a scratch checkpoint serialization failure; late runtime memory was not recovered. No patch is supplied: extending spacing, trusting projected endpoints, forcing adjacent attacks or guessing potion identities would not establish safety. Existing targeted tests passed, but there is no candidate or new red/green regression.

## Recommendations

- **000038-skeleton-pursuit-intervention — Establish an admitted intervention before two-skeleton retreat degenerates into spacing exhaustion.** (high, deferred): The blocker is an unvalidated replacement, not omitted selecting source. Existing shock admission excludes two enemies while magic remains, and adjacent damage retains explosion risk. Reconstruction matched through decision 2093 but stopped at scratch serialization. Next, retain reconstruction in-process through decisions 2181–2187 and probe the existing control selector on copies, verifying a throw footprint outside the hero, allies and loot before proposing earlier arbitration. Stop at any selecting divergence. No safe control target or contact-breaking route is certified, so neither a policy patch nor a fabricated regression is supplied.
  - Evidence: Decisions 2093–2099, lines 5925–5946: waking a sleeping DM-100 leads to damaging flight and dew consumption.; Decisions 2181–2186, lines 6182–6194: two skeletons approach while waits and wand shots precede retreat.; Decision 2187, line 6195: retreat begins at 12 HP with one separate-wand charge remaining.; Decisions 2197–2199, lines 6239–6252: spacing exhaustion leads to unverified retreats.; Decisions 2201–2202, accepted transitions at lines 6260 and 6265: health falls from 12 to seven, then zero.
  - Disposition: deferred

## Lessons for the next run

A projected single-attacker destination is not an achieved contact break. Investigate control before melee contact and the cost of waking sleeping ranged enemies. Preserve explosion avoidance, observed hazard checks, resource receipts and mandatory progression pickups; unknown potion identities are not escape resources.

Update: **review-only**.
