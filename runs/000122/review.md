# ShatteredAI run 000122

Played commit: `9d8064c858b38bd62eca16813714eeeacc01c552`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now clears a remembered DM-100 threat when a carefully verified disintegration attack proves it was defeated. Uncertain attacks still leave the threat remembered.

## Incoming learnings

Keep remembered lightning threats separate from ordinary sightings, but retire matching memory when a rigorously confirmed tracked attack proves that caster cannot remain alive. Experience and disappearance alone are insufficient for a penetrating beam; preserve threat memory when tracking, range or successful execution is uncertain.

## Analysis

The hero was alive at full health when mandatory potion discovery exhausted the planner. Decisions 227–229 moved from water through grass and a door into the final explored pocket; the last accepted move advanced the clock normally. Source-pinned offline reconstruction matches all 230 recorded selections and reproduces decision 230's blocker. Reconstructed bookkeeping retains 66 inventory-compatible preparation banks, but the existing return-terrain restriction disconnects every bank: only the current grass cell and adjacent door remain reachable. The nearest remembered bank needs just six ordinary route cells, so increasing travel or waiting bounds would not solve this. All water is currently unseen, and no known identification or reconnaissance resource remains. Complete source and reconstruction resolve the packet's selecting-state uncertainty. No patch is supplied because crossing the grass requires an unvalidated change to the transit safety contract; stale bank observations cannot authorize drinking. The unchanged source passes 1910 tests, with four skipped. No new regression or candidate success is claimed.

## Recommendations

- **000061-descent-bank-return — Establish an executable preparation reservation before exploration disconnects every remembered discovery bank.** (high, deferred): Revalidated here, but no safe focused replacement is established. Grass 851–853 disconnects the return graph independently of hunger or travel limits; allowing that transit would relax an existing safety restriction. Terminal inventory has no known nonconsumptive identification resource. Next derive paired decision-227/230 fixtures and validate a bounded preparation-reservation transaction before leaving the admitted component, including legitimate preparation timing, fresh bank and inventory admission, accepted-input receipts, interruption handling and unchanged mandatory exploration/pickup obligations. Do not drink from remembered visibility, guess crimson's effect or increase bounds.
  - Evidence: Decision 227, selection line 626 and accepted line 627: movement leaves water 820 for grass 851; reconstruction retains bank 755.; Decisions 228–229, lines 629–633: exploration crosses door 884 and reaches grass 916.; Decision 230, line 635: mandatory discovery exhausts with the hero at full health.; Offline reconstruction matches all 230 selections; the existing constrained return graph contains only cells 916 and 884, excluding all 66 compatible bank receipts.; tools/descent_potions.py:85–143,376–417; tools/preparation_prerequisites.py:16–58.
  - Disposition: deferred

## Lessons for the next run

Preserve a freshly verifiable preparation opportunity before exploration leaves the admitted return graph. Bank receipts alone do not guarantee an executable return. Keep mandatory discovery, progression pickup, fresh inventory protection and terminal exhaustion intact.

Update: **review-only**.
