# ShatteredAI run 000135

Played commit: `77638d068c294cace849fdde39b80dbe54bf80b4`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When choosing among doorway retreats, the bot now prefers a first step exposed to at most one observed attacker over one exposed to several. It still prefers shorter routes within each group.

## Incoming learnings

Among already admitted doorway approaches, avoid a first step beside multiple observed attackers when another route limits current contact to one. Keep shortest-route preference within each contact class, and recheck hazards and the actual holding square. A less-exposed first step does not prove safe arrival or survival.

## Analysis

The hero remained alive at planner exhaustion. The initiating resource error occurred at decision 138: the bot spent its only identified liquid-flame potion on optional bookshelves before finishing ordinary exploration. Decision 139's accepted transition confirms consumption; decision 157 first reveals a real barricade. At decision 194, mandatory potion discovery blocked descent because that barricade's flame supply was missing, and all listed preparation alternatives declined. The remaining unidentified potion was not a known replacement. A focused candidate now reserves the last known flame from optional shelves while exploration is unfinished or a barricade is remembered. An isolated original-source probe matched the recorded throw and target; it was not a full runtime-memory reconstruction. The new regression failed with two expected assertions on original policy and passed on the candidate. The full suite passed 1,946 tests with four skips. This establishes reservation behavior, not successful barricade clearance or continuation.

## Recommendations

- **000135-last-flame-reservation — Reserve the last known flame from optional bookshelf ignition before exploration finishes or while a barricade remains.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 138, log line 380: sole identified flame selected for bookshelf ignition.; Decision 139, log lines 382-383: target 409 selected and flame consumption accepted.; Decision 157, log line 430: barricade 645 first publicly observed after flame expenditure.; Decision 194, log line 538: missing flame supply exhausts mandatory potion discovery.
  - Disposition: implemented

## Lessons for the next run

Keep the last identified liquid-flame potion for a possible barricade until ordinary branch discovery is finished. Optional bookshelves do not prove that the dose is surplus. Preserve existing collateral, protection, pickup and discovery requirements; never assume an unidentified potion replaces the spent supply.

Update: **accepted**.
