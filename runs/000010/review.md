# ShatteredAI run 000010

Played commit: `eb98602cb93bf317cf85ea0697cafcee91ad2120`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died to a lightning bolt after an exhausted ranged retreat

## Improvements since the last run

- When its backpack is full, the bot ranks items before making room for a new pickup. It protects essential supplies and compares spare equipment using upgrades and strength requirements.
- The bot uses held keys and visible room layouts to choose which crystal-room rewards it can pursue, rather than treating every locked reward as available.
- The bot can spend six alchemical energy to turn a magical catalyst into a trinket, then choose among the offered trinkets using a Mage-specific ranking.
- The bot checks whether it is allowed to attack the Great Crab before attempting the hit.

## Incoming learnings

Special-enemy attack admission must survive recovery target reselection. An awake great crab is not an ordinary damage-scoring target, and regenerated wand charges do not prove a usable attack. Preserve separate evidenced surprise setups; declining blocked attacks does not establish a safe alternative or quest success.

## Analysis

The initiating missed opportunity was in ranged arbitration, not just the final recovery waits. At decision 2970 (log lines 8391–8393), the staff was empty, both throwing clubs were on the visible DM-100's cell, and an identified throwable stone of deep sleep remained carried. The early ranged controller raised NoSafeAction before shared runestone tactics could run; continuation spent the waterskin and then retreated. Offline memory reconstruction matched selected inputs 0–2970; an isolated candidate probe selected the sleep stone, without supplying subsequent observations. This is reconstructed policy state, not recorded memory. Decision 2979's accepted transition (8434) records a hidden explosive trap and HP falling from 33 to 7. Decision 2985's terminal transition (8457) explicitly reports lethal lightning and the Zapped badge; the final killer is not inferred merely from enemy proximity. The clock advanced during recovery. Post-death potion and ring revelations were not treated as prior knowledge. A focused selector correction and new regression are supplied for next-run validation; files is empty because the adapter derives changes. The original selector fails two expected assertions; the candidate passes all nine new tests and the full 1470-test suite, with four skips. This establishes control selection, not a successful throw, safe escape, puzzle completion or survival.

## Recommendations

- **000010-dm100-exhausted-sleep — Consider identified deep sleep before exhausted single-DM-100 continuation.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2964–2969, log lines 8377–8389: available ranged attacks exhausted; Decision 2970, log lines 8391–8393: known sleep bypassed before waterskin continuation; Decision 2979, accepted transition 8434: hidden explosive trap and severe HP loss; Decision 2985, accepted transition 8457: explicit lethal lightning
  - Disposition: implemented

## Lessons for the next run

Before exhausted ranged arbitration enters best-effort continuation, consider carried, identified point-target control. Preserve clear-shot, eligibility, cooldown, hazard and mandatory-pickup constraints. Selecting sleep is not evidence that it landed or that escape became safe.

Update: **accepted**.
