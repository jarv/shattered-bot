# ShatteredAI run 000065

Played commit: `fa7bca776cfe237b66709ce7411eb800fbc3e8a7`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- Before leaving a floor, the bot can return a short distance to a previously checked potion-testing spot, including through a closed door. It checks the surroundings again before drinking and limits how many return steps it takes.

## Incoming learnings

Separate ordinary bank reobservation from unknown-potion drink admission. Remember only actually observed bank and stash feasibility, preserve fresh arrival checks and mandatory progression pickups, and account for accepted door-opening inputs even without displacement. A chosen preparation input is not completion evidence.

## Analysis

The living hero exhausted the planner because mandatory pre-descent potion discovery had no admitted testing bank or return plan. Decision 216's accepted transition (line 625) collected a second unidentified potion after the last reconstructed bank receipt at decision 215 (line 621). Exploration then left the water approaches. Decision 273's accepted transition (line 792) advanced the clock at full health; decision 274 (line 794) failed preparation, not survival. Source-pinned offline reconstruction matched all 274 selected actions, reasons and intents and reproduced the terminal blocker. Its terminal probe found no currently admitted visible bank; nearest remembered water required a 20-cell route through grass and closed doors. The remembered bank receipt required 33 route cells and described the earlier one-potion inventory, so the played short-return correction did not apply. The selecting chain is tools/mage_policy.py:414-468 through tools/descent_potions.py:110-253, with visibility and protection checks in tools/puzzle_supplies.py:97-121 and tools/potion_stash.py:51-76. Complete source resolves the bookkeeping gaps, but does not certify safe multi-stage transit and fresh two-color stash feasibility. No patch or new regression is submitted: simply extending the return bound, ignoring changed inventory, or weakening testing terrain checks would not establish that contract. The unchanged full suite passed 1,752 tests with four skipped; this does not resolve the recorded failure.

## Recommendations

- **000061-descent-bank-return — Establish bounded multi-stage return and fresh inventory-protection admission for mandatory pre-descent discovery.** (high, deferred): The exact blocker is an unvalidated multi-stage transit-and-arrival/protection contract, not missing selecting source or runtime bookkeeping. The only verified bank receipt predates the second potion; both its route and the nearest water route exceed the short-return contract and cross excluded grass and doors. No currently visible bank is admitted. Next, derive a deterministic fixture from the recorded 513-to-423 or 513-to-94 geometry and validate ordinary transit separately from testing, including hazards, door-opening receipts, total travel budget and fresh two-color stash admission on arrival. Increasing bounds or discarding inventory compatibility alone would not certify safe discovery. No speculative movement repair is submitted.
  - Evidence: Decision 215, line 621: last reconstructed bank receipt at 94 covers only turquoise potion.; Decision 216, accepted transition line 625: bistre potion is collected.; Decision 220, accepted transition line 634: the bistre strength hypothesis fails without revealing its full identity.; Decision 273, accepted transition line 792: the clock advances at full health.; Decision 274, line 794: mandatory discovery blocks departure.; Offline reconstruction matches all 274 selected inputs; nearest water route has 20 cells and the old receipt route has 33.; tools/descent_potions.py:51-88,110-253; tools/puzzle_supplies.py:97-121; tools/potion_stash.py:51-76.
  - Disposition: deferred

## Lessons for the next run

Separate long ordinary return-to-reobserve travel from drink admission. A bank receipt for one carried potion does not establish protection after another color is collected. Require fresh arrival visibility, inventory-protection feasibility, hazard barriers, hunger budgeting and accepted-input accounting; never treat route existence or a preparation choice as completion.

Update: **review-only**.
