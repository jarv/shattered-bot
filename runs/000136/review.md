# ShatteredAI run 000136

Played commit: `edb1d8b72c44373fdca7b9c439ff8c64f67a3f6c`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now saves its last known liquid-flame potion while ordinary unexplored branches remain, instead of spending it on optional bookshelves. It also reserves that dose for any barricade it has already seen.

## Incoming learnings

Keep the last identified liquid-flame potion for a possible barricade until ordinary branch discovery is finished. Optional bookshelves do not prove that the dose is surplus. Preserve existing collateral, protection, pickup and discovery requirements; never assume an unidentified potion replaces the spent supply.

## Analysis

The Mage stopped alive on floor 1 at full health after 276 elapsed turns. This was planner exhaustion, not a death. Decision 276 collected golden potion (selection line 774; accepted transition line 775), adding it to amber and identified liquid flame. Decision 277, line 777, then exhausted mandatory strength discovery. Source-pinned offline bookkeeping reconstruction matches all 277 preceding selections and the exact terminal blocker; it is reconstructed state, not recorded memory. Nine remembered preparation banks were certified for amber plus liquid flame only. The added potion invalidated every exact-inventory return receipt in tools/descent_potions.py:102-107. No locally visible water or known reconnaissance resource admitted an alternative. Mandatory pickup was not itself a mistake. Isolated copied-state probes find historical three-color storage feasibility around bank 104 and an otherwise admitted 54-step return corridor, but only after hypothetical inventory or receipt substitution. Those probes do not certify a current return-and-storage transaction. Source browsing resolves the packet's selecting-state gap, but no safe replacement is established. No policy patch or new regression is submitted; exact inventory matching, collateral checks, mandatory pickup and terminal exhaustion remain unchanged. The unchanged full suite passed 1,946 tests with four skipped; no baseline-red/candidate-green result is claimed.

## Recommendations

- **000123-inventory-aware-discovery-return — Establish inventory-aware preparation return after potion pickup invalidates discovery-bank receipts.** (high, deferred): Revalidated, but not patched. Historical projected three-color feasibility around bank 104 resolves part of the storage uncertainty; it does not provide a current inventory-aware preparation witness, fresh arrival admission or verified storage transaction. Simply substituting the new inventory into an old receipt bypasses a safety gate. Next derive paired decision-223/277 fixtures for bank 104, storage 228 and the recorded 54-step corridor, then validate bounded preparation-only return with accepted movement receipts and fresh bank/stash checks before drops or drinking. Preserve exact ordinary receipts, collateral protection, unknown identities, mandatory pickup and terminal exhaustion.
  - Evidence: Decision 222, selection line 620 and accepted line 621: amber pickup at 104.; Decision 223, line 623: amber and identified liquid flame share the inventory near witnessed preparation banks.; Decision 276, selection line 774 and accepted line 775: golden pickup changes the potion inventory.; Decision 277, line 777: both preparation prerequisites decline and mandatory discovery exhausts at full health.; Offline reconstruction matches decisions 0-276 and the terminal blocker; nine historical receipts cover only amber plus liquid flame.; tools/descent_potions.py:30-107,376-417; tools/potion_stash.py:103-133.
  - Disposition: deferred

## Lessons for the next run

Treat inventory-changing pickup as a preparation-planning dependency. Previously feasible banks need an independently validated, inventory-aware reobservation transaction, followed by fresh bank and remote-storage admission. Historical geometry must not become permission to drink, and unknown potion colors must remain unknown.

Update: **review-only**.
