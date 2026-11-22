# ShatteredAI run 000101

Played commit: `ba9c0079ccee3e3446cd52a71478e1fe3ac8bb6c`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now counts time spent attacking toward the lifetime of its retreat commitment, even when health and wand charges stay unchanged. Free targeting and inspections do not shorten that commitment.

## Incoming learnings

Spend the existing escape-protection lifetime on accepted time-consuming combat inputs too. Free targeting and inspections must not age it. Expiry only removes stale route bookkeeping: current hazards, remembered threats, movement admission and mandatory progression pickups still require their normal checks.

## Analysis

The living hero exhausted the planner, not the game clock. Bookshelf 635 first appears at decision 347 (line 1074); shelves 636–638 follow at decision 348 (line 1077). The policy reserves liquid flame for every bookshelf, but its unknown-fire preparation admits barricades, not shelves. Hungry room preparation also declines. The last scroll publicly becomes Remove Curse, not Identify. Decision 354's accepted cancellation advances time; decision 355 (line 1093) terminates because the sole missing supply is flame at 635. Source-pinned offline bookkeeping reconstruction matches all 355 selected actions, reasons, intents and controllers and the exact terminal blocker; this is reconstructed state, not recorded memory. It excludes active retrievals and competing room demands. Ordinary test banks exist, but they do not override supply preservation or establish safe testing and retrieval. No patch is submitted: shelf-back cells 599–602 remain unobserved, and no known identification or reconnaissance resource remains. The game source permits both ordinary library shelves and flame-separated rewards, so dropping reservation or extending unknown-fire use would lack safety evidence. The unchanged source passes 1,849 unit tests, with four skipped; no candidate red/green validation is claimed.

## Recommendations

- **000076-terminal-supply-arbitration — Resolve shelf-driven missing-flame arbitration without bypassing safe discovery or retrieval.** (high, deferred): Revalidated here. Full source and matching reconstruction resolve the selecting-state gap, but do not establish whether the unseen shelf backs conceal a required retrieval. No known identify, intuition, mapping or clairvoyance resource remains. Removing reservation could consume needed flame; broadening unknown-fire preparation would bypass the tested shelf exclusion without an admitted fire-recovery contract. No patch or new regression is supplied. Next derive the decision-347 shelf-strip fixture with explicitly unknown backs, plus paired observed-wall-back and shelf-separated-reward fixtures. Establish a positive public-evidence distinction while retaining reservation for unknown backs and real retrievals; otherwise establish an executable nonconsumptive reconnaissance plan before changing arbitration. Preserve hazard checks, inventory protection, mandatory pickup and terminal exhaustion.
  - Evidence: Decision 347, line 1074: bookshelf 635 first appears; decision 348, line 1077: shelves 636–638 appear.; Decisions 350–354, lines 1083–1092: the unknown scroll becomes Remove Curse; accepted cancellation advances turns 346 to 347.; Decision 355, line 1093: missing liquid flame at 635 is the only reserved-supply blocker and all preparation prerequisites decline.; Offline reconstruction matches all 355 selections and terminal exhaustion; copied probes exclude active retrievals and find unobserved shelf backs 599–602.; tools/puzzle_supplies.py:87–88,585–639; tools/wooden_barrier.py:24–25; tools/descent_potions.py:283–317.
  - Disposition: deferred

## Lessons for the next run

Treat bookshelf-driven supply exhaustion as an obligation/admission mismatch, not a death or a reason to wait longer. Preserve unknown potion identities and mandatory pickups. A safe repair needs positive public evidence distinguishing optional shelf fuel from a real retrieval barrier, or executable nonconsumptive reconnaissance; an ordinary safe test bank alone is insufficient.

Update: **review-only**.
