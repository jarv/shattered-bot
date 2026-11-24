# ShatteredAI run 000237

Played commit: `cae2ab7fcfa8a91ae0d0a5bbbf32a6dacb783834`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now allows for extra enemy movement when judging retreats in identified armor that requires more strength than the hero has. Unknown armor requirements do not count as confirmed encumbrance.

## Incoming learnings

Known armor encumbrance must affect retreat approach estimates: a move that costs more than one turn can admit extra enemy movement. Keep current contact separate from prospective approach pressure. Unknown-ring effects and post-death revelations must not be used to justify earlier choices; a corrected risk estimate does not establish a safe escape or survival.

## Analysis

The hero remained alive at 47/70 HP when the planner stopped. The initiating defect is an action-granularity mismatch, not a confirmed killer: decision 3730 checked only immediate randomized landings and called its adjacent cell click a single-step escape. Accepted transition 10632 and the next public movement receipt show two relocations, from 368 through 401 to 434, and seven elapsed turns. The pinned game continues normal cell pathfinding until readiness; adjacent clicks are not guaranteed single movement attempts under vertigo. Renewing confusion gas then fills the visible corridor. At decision 3731, unseen flanking terrain prevents a fully checked exit, waiting would renew exposure, and no known purity or transport supply is carried. Earlier, decision 2100 exhausted pool preparation; decisions 2100–2108 performed fallback descent, with the actual transition at log line 6111 and no collection credit. Source browsing resolves the terminal execution mismatch but not a safe replacement. Independent recorded-snapshot probes reproduce the escape proposal and terminal exhaustion; they are not recovered runtime memory. No patch or new regression is supplied: changing movement granularity requires protected API/runner changes, while an eligible whole-click containment or known-resource rescue has not been safely established. Simply refusing the original click would only stop earlier. The earlier pool incident also needs original bank/journey bookkeeping reconstructed before a particular admission rule can safely change.

## Recommendations

- **000237-vertigo-click-containment — Establish whole-input safety for vertigo movement instead of assuming an adjacent click is one attempt.** (high, deferred): The API exposes normal cell pathfinding, not an interruptible single-attempt move; changing that contract requires protected source. No eligible known-resource rescue or complete settled-click containment certificate is established for this inventory and evolving cloud. An earlier veto alone is not a progress repair. Next derive paired decision-3729/3730/3731 fixtures and a source-pinned whole-click envelope, including repeated random attempts and renewing gas, then require a positive safe rescue or containment regression before changing selection. Preserve unknown-neighbor, hazard and terminal checks.
  - Evidence: Decision 3729, log lines 10628–10629: exploration enters apparently ordinary floor and reveals confusion exposure.; Decision 3730, log lines 10631–10632: immediate landing envelope excludes the eventual endpoint; one input advances seven turns.; Decision 3731, log lines 10635–10636: renewed gas and unchecked flanking terrain leave no admitted escape.; tools/vertigo_tactics.py:73–113,149–221; tools/survival_policy.py:187–188; pinned game Hero.actMove/getCloser and Char.move.
  - Disposition: deferred
- **000237-pool-round-trip-preparation — Identify and repair the pool preparation admission failure that preceded fallback descent.** (high, deferred): The report establishes failed bank/journey admission but does not isolate its rejecting conjunct. Original room-attempt exclusions, deferred controllers, pool-approach receipts and revisit bookkeeping have not been reconstructed; substituting fresh snapshot defaults would not justify relaxing them. Next reconstruct original selections and accepted feedback through decisions 1436 and 2100, stop at the first divergence, and enumerate bank, entrance and return-budget rejections on validated copies. Require an executable preparation transaction and new regression, not guessed invisibility or collection credit.
  - Evidence: Decision 1436, log line 4157: pool chest 1602 is publicly observed.; Decision 2100, log line 6059: unfinished chest and no verified protected reward round trip trigger a planner incident.; Decisions 2100–2108, log lines 6062–6111: nine accepted recovery inputs culminate in descent without collection credit.; tools/puzzle_supplies.py:285–322,971–1018; tools/room_tactics.py:234–357; tools/mage_policy.py:439–458.
  - Disposition: deferred

## Lessons for the next run

An adjacent cell click can execute repeated randomized movement before the next observation. Immediate landing checks and synthetic one-step receipts do not prove whole-input safety. Preserve terminal exhaustion, unknown-terrain checks, mandatory pickups and honest collection receipts; fallback descent does not repair unfinished preparation.

Update: **review-only**.
