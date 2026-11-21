# ShatteredAI run 000050

Played commit: `1d45ad3d1d19731ce0959e844e11496d4d9d2442`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When escaping a prison guard, the bot now checks every step toward cover against the guard’s melee reach, including when continuing a previously chosen route.

## Incoming learnings

A covered destination does not make the journey safe. When escaping a guard, check every transit cell against its current melee reach as well as ranged sight, and recheck committed routes after each observation. Static separation is not a guarantee against pursuit or chain pulls.

## Analysis

The hero remained alive at 15/30 HP when planning stopped. Decision 822 (log lines 2393–2394) explored onto an unrevealed burning trap; the next observation showed Burning and fire blocking the admitted route out. Decision 823 (2396), followed by terminal observation 2397, exhausted the planner rather than recording a death. The burning-recovery selector checked water routes and known frost but omitted the identified, throwable potion of purity already carried. The exact played game source confirms that throwing purity onto the hero’s triggered-trap cell clears fire and removes Burning; drinking it is not equivalent. Unknown colored potions were not usable evidence of an extinguishing effect. The proposed focused correction adds known purity self-splash to emergency recovery while preserving hazard checks, existing frost priority, adjacent-water preference, honest pickup accounting and the stuck-planner terminal outcome. A new reduced public-observation regression produced three expected assertion failures on original policy and passed all six tests after the fix. The full suite passed 1675 tests with four skips. These are isolated selector tests, not recovered original memory or gameplay replay; they establish action selection, not successful execution or survival.

## Recommendations

- **000050-purity-burning-rescue — Admit known purity self-splash before declaring burning recovery exhausted.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 822, log lines 2393–2394: exploration triggers an unrevealed burning trap.; Decision 823, log line 2396: identified throwable purity remains carried while burning recovery exhausts.; Log line 2397: living hero and unchanged clock at planner termination.; tools/combat_positioning.py:98–183; PotionOfPurity.java:55–94; Potion.java:419–429.
  - Disposition: implemented

## Lessons for the next run

An identified potion of purity can extinguish Burning when shattered on the hero, even when fire blocks every safe water route. Do not substitute drinking, guess an unknown potion’s identity, or claim rescue or room completion before observing the result.

Update: **accepted**.
