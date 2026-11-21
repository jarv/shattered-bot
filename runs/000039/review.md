# ShatteredAI run 000039

Played commit: `f8c8fdd2068ea6ff499f371961a1d6080e35e792`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now tests unidentified potions for strength before an otherwise permitted departure, rather than during ordinary exploration. It preserves supplies needed for recognized puzzle rooms and checks the effects of each drink.
- When identifying a potion stored in a bag, the bot opens that bag instead of spending Identify on a lower-priority item already visible in the backpack.

## Incoming learnings

A projected single-attacker destination is not an achieved contact break. Investigate control before melee contact and the cost of waking sleeping ranged enemies. Preserve explosion avoidance, observed hazard checks, resource receipts and mandatory progression pickups; unknown potion identities are not escape resources.

## Analysis

The hero stopped alive at full health because the planner exhausted recovery, not because of an observed death. The initiating contradiction was potion-room staging: decision 710 moved toward bank 390, but decision 714 declined preparation there and resumed exploration; decision 715 immediately sent the hero back. Offline bookkeeping reconstructed from the played source and recorded public inputs matched every selected action and reason through decision 715. A local probe found that the hypothetical flight route from bank 390 crossed an unscouted closed door at 503, too far away for the entrance-opening helper to act. Bank selection accepted that route although arrival could neither open the entrance nor drink. Repetition displaced exploration and descent until navigation guards and hungry recovery were exhausted at decision 926. The proposed correction applies the existing entrance prerequisite before selecting a test bank or flight revisit. It does not cross a hazard, infer potion identity, grant collection credit, weaken progression pickups, or remove the terminal failure. The new regression has two expected assertion failures on original source and passes on the candidate; the full suite passes 1,648 tests with four skips. An isolated candidate probe first changes decision 709 to a public identification attempt; no subsequent gameplay was simulated. This establishes removal of the reproduced staging contradiction, not puzzle completion or eventual survival.

## Recommendations

- **000039-remote-flight-entrance — Reject potion-test banks and flight revisits whose unscouted entrance cannot be opened from that bank.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 710, log line 2111; Decision 714, log line 2120; Decision 715, log line 2123; Decision 740, log line 2208; Decision 925, log lines 2793–2794; Decision 926, log line 2796; tools/puzzle_supplies.py:265–300, 377–410, 580–591
  - Disposition: implemented

## Lessons for the next run

A hypothetical protected round trip is insufficient preparation evidence when its entrance cannot be scouted from the proposed bank. Check the same entrance prerequisite during selection and arrival, preserve honest unfinished obligations, and allow other admitted work when preparation cannot proceed.

Update: **accepted**.
