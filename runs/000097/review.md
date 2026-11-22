# ShatteredAI run 000097

Played commit: `27378a92c072297784e37dfb82df5424a9f87230`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When planning a levitation trip, the bot can first switch from uncertain movement gear to carried, identified, curse-known safe armor, but only if the alternative permits a verified round trip. It checks the observed equipment again before entering danger.

## Incoming learnings

When a mandatory protected pickup is blocked by uncertain movement equipment, consider carried, identified, curse-known safe armor as preparation only after verifying the full trip under that alternative. Reobserve equipment and protection before entering danger. Choosing preparation does not establish collection or puzzle success.

## Analysis

The run ended in planner exhaustion, not death; the hero was alive at full health. Decision 1457 identifies three unreachable golden keys as the actual mandatory pickups behind the generic upgrade/strength message. Earlier, decision 1328 spent the only identified levitation potion on a nearby chest while one held key covered only one of four observed locks. The chest yielded gold, and the bot returned with insufficient remaining protection for the nearest conservatively budgeted key trip. The original reward search accepted the short chest trip before considering matching keys. An isolated probe using the recorded public snapshot reproduces that route; it is not recovered runtime memory or a gameplay replay. The proposed correction prefers an already-admitted golden-key flight trip when observed locks exceed held keys, retaining the original reward as fallback. A new regression fails on the original policy and passes on the candidate; the full suite passes 1,841 tests with four skipped. This establishes planning preference, not successful retrieval or completion of the remaining room.

## Recommendations

- **000097-flight-key-deficit — Prefer verified matching-key flight trips over chest trips while observed locks outnumber held keys.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1262: known-flight staging begins.; Decision 1328: one held golden key, four locked chests, three isolated golden keys, and the sole identified levitation dose.; Decisions 1329–1334: chest retrieval and return leave 14 turns of levitation.; Decision 1457: mandatory matching-key pickups block descent.
  - Disposition: implemented

## Lessons for the next run

A held key does not mean every observed lock is supplied. Prefer a fully budgeted matching-key flight trip before spending scarce levitation on a chest when keys are still deficient. Recheck actual protection before movement; never infer an unknown potion identity or treat a planned pickup as collected.

Update: **accepted**.
