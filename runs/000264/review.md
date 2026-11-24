# ShatteredAI run 000264

Played commit: `08c9cf256c68f348fad3c17b686a8aa38bda6979`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a necromancer's skeleton

## Improvements since the last run

- Before descending, the bot can revisit safe ground to look again at a required item last seen in confusion gas. It keeps the item unfinished until there is actual pickup evidence and does not assume the gas has disappeared.

## Incoming learnings

Plan mandatory room preparation across possible failed hypotheses, including protection or identification of the remaining potion stacks. A successful unknown test transaction is not puzzle completion. Keep mandatory pickup receipts, fire restrictions and terminal planner exhaustion; do not replace missing prerequisites with extra waiting or guessed potion identities.

## Analysis

The complete recording confirms death: decision 3474, log 10249, changes HP from 2 to 0 and the terminal public text names a necromancer's skeleton. This is not inferred from nearby enemies; the compact packet omitted that text. Earlier attrition began with the guard pull during loot travel (D3324, logs 9734–9735); committed DM-100 flight then lost 19 HP over D3332–3333. A later, specific planning defect is that necromancer navigation treats a two-square gap from an adrenaline-buffed summon as contact-free. At D3442 (logs 10141–10142), the wounded hero investigates a remembered caster, moving from 108 to 149 while the empowered summon is at 107; HP falls from 23 to 20. The helper uses adjacency checks despite the shared risk evaluator already recognizing fast pursuit. A reduced public-input fixture reproduced this selection, without reconstructing original runtime memory or dispatching actions. No patch is retained: the proposed pursuit veto passed its four new probe cases but failed six existing regression assertions, replacing required spacing with adjacent summon attacks, including at 3 HP. That is not a supported safe replacement. All changes were reverted; the restored full suite passed 2,443 tests with four skips. No planner incidents were recorded. The exact enemy scheduling and a survival-preserving alternative remain unestablished.

## Recommendations

- **000264-empowered-summon-navigation — Make necromancer navigation account for empowered-summon pursuit without sacrificing low-health spacing.** (high, deferred): Full source resolved the selecting-chain gap, but a blanket fast-pursuit veto is unsafe as a replacement: its local fixture passes while six existing assertions fail, including required spacing at 3 HP being replaced by an adjacent summon attack. No original mutable counters or enemy action phase were recovered, and no alternative survival transaction was proved. Next derive a movement-aware ranking, rather than a zero-exposure veto, against the paired D3442 corridor and existing low-health memory/visible-caster spacing fixtures. Require a positive admitted continuation in both before retaining a patch; preserve explosion checks and bounded exhaustion.
  - Evidence: D3441–3442, logs 10136–10142: retreat is followed by a remembered-caster approach beside an adrenaline-buffed summon; HP falls from 23 to 20.; D3449–3460, logs 10168–10209: remembered-caster investigation continues amid attrition.; tools/necromancer_tactics.py:128–144,148–166: adjacency-only approach and withdrawal checks precede bounded blocker attacks.; tools/challenge_combat.py:34–40,65–86: public acceleration already contributes fast-pursuit exposure.
  - Disposition: deferred

## Lessons for the next run

Account for publicly visible adrenaline when comparing necromancer approaches and withdrawals, but do not turn every threatened gap into a stationary summon attack. Preserve low-health death-blast spacing, bounded combat, hazard admission and mandatory pickup receipts. A locally admitted shot is not evidence of survival.

Update: **review-only**.
