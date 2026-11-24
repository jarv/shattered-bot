# ShatteredAI run 000267

Played commit: `0e7ad4a7c0cf14c0607c0cd6f04c0eca057ba2e3`

Outcome: stuck-planner

Java build: `51bdb688a8fed22859aa80c5a30a841418fb3c1d6da0f7e728dd727d4914879c`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now stops setting up new doorway lures as soon as accepted retreat injuries exhaust its safety budget, rather than waiting for the next movement review.

## Incoming learnings

Accepted injury must retire exhausted lure setups immediately, rather than waiting for the periodic movement review. Canceling and restarting a doorway plan must not erase the encounter’s accumulated health loss. Verified escapes remain eligible; retirement is not proof of safety or survival.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. After discovering gas and escaping, the bot repeatedly returned to an approach beside a chasm that its own potion-testing rules could never accept. These reversals exhausted exploration targets; unfinished gas-room preparation then correctly prevented descent. D192–195, log lines 542–553, establish the initiating sequence; D223–226, lines 641–654, show recovery and terminal failure. Source inspection traced the mismatch to the shared flight/gas approach envelope in tools/puzzle_supplies.py. Offline reconstruction matched every original action and reason through D195. The proposed correction tightens only gas staging geometry, preserving flight handling and all testing, storage, protection, return and mandatory-pickup checks. On a copy of that validated state, preparation instead selects an existing observed route toward a compatible western bank. The new regression fails on the original helper and passes on the candidate; the full suite passes 2463 tests with four skipped. This establishes an admitted reobservation choice, not successful potion testing, reward collection or survival.

## Recommendations

- **000267-gas-approach-envelope — Reject structurally incompatible gas-testing approaches before they repeatedly reverse useful exploration.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D192–195, log lines 542–553: gas discovery, escape and return to the chasm-adjacent approach.; D223–226, log lines 641–654: navigation recovery followed by mandatory-preparation planner exhaustion.; tools/puzzle_supplies.py:183–211,457–514: gas test-bank terrain differs from the shared reobservation envelope.; Offline reconstruction matched D0–195; an isolated candidate preparation probe selects the observed route toward bank 938.
  - Disposition: implemented

## Lessons for the next run

A protected reward route is not enough to choose a potion-testing approach. Gas staging must also match the actual test-bank terrain requirements before preferring a remembered location. Reobservation remains preparation only: fresh visibility, inventory protection, actual potion effects and pickup receipts must still be verified.

Update: **accepted**.
