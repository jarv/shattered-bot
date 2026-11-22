# ShatteredAI run 000100

Played commit: `32359b2d00d774873888613775bb17b6a818fbaf`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now keeps recovering on Sungrass when another routine activates its planted seed first. It requires the observed healing effect and still stops for threats, starvation, exhausted recovery time or lack of healing progress.

## Incoming learnings

Preserve paid-for Sungrass recovery when another selector activates the plant: use the observed same-cell healing buff, then recheck threats, hunger, health progress and the existing recovery budget before each wait.

## Analysis

The hero remained alive at 31/60 HP when the planner exhausted. Two-skeleton pressure led to a committed doorway retreat (decisions 2722–2729), followed by stationary combat. The initiating bookkeeping defect is that escape protection ages for movement, waits, HP changes or charge changes, but ignores paid melee turns when those values stay unchanged. Decisions 2735–2737 advance the public clock at unchanged HP and charges (accepted transitions, log lines 7950, 7953 and 7956). Source-pinned offline reconstruction matches actions, reasons, intents and controllers through decision 2738; its reconstructed escape age stays eight through those three attacks and becomes nine after the final attack. This is reconstructed bookkeeping, not originally recorded memory. At decision 2739 the planner selects a frontier route toward 1105 but rejects its reverse escape edge (line 7960). Recovery also excludes reversal, waits twice, and then exhausts at decision 2741 (line 7966). This is a planner contradiction, not an observed death or proof that progression is impossible. The focused correction counts accepted public clock advancement toward the existing escape lifetime; it does not enlarge waiting limits or remove safety checks. A new four-case regression fails on original policy with the expected age assertion, passes on the candidate, and the complete suite passes 1,849 tests with four skips. Full original reconstruction stopped before selecting decision 2739 because an optional bookkeeping export failed; no subsequent observations were fed to a changed selection. No candidate trajectory or survival outcome is established.

## Recommendations

- **000100-escape-combat-clock — Count publicly timed accepted combat inputs toward escape-commitment expiry so stale protection cannot block onward planning.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 2722–2729: committed multi-enemy doorway retreat creates the protected return edges.; Decisions 2735–2737, accepted transitions at log lines 7950, 7953 and 7956: time advances without changing hero HP or charges.; Decision 2739, log line 7960: escape reversal excludes the frontier route toward 1105.; Decision 2741, log line 7966: hungry recovery exhausts with the hero alive.; tools/escape_commitment.py:14–26; tools/pursuit_budget.py:14–35; tools/mage_policy.py:417–422; tools/tactical_recovery.py:102–115,158–165.
  - Disposition: implemented

## Lessons for the next run

Spend the existing escape-protection lifetime on accepted time-consuming combat inputs too. Free targeting and inspections must not age it. Expiry only removes stale route bookkeeping: current hazards, remembered threats, movement admission and mandatory progression pickups still require their normal checks.

Update: **accepted**.
