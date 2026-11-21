# ShatteredAI run 000078

Played commit: `71876354058d381b62085164a23656c21a3010f0`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now distinguishes picking up a freshly visible pile on the stairs from actually using the stairs. It permits the existing safe pickup interaction while retaining checks against unintended descent.

## Incoming learnings

Distinguish fresh adjacent heap pickup from actually using the stairs. Preserve the existing threat and observation requirements, and require an accepted collection receipt before considering the heap finished. Choosing this interaction does not establish collection or subsequent descent success.

## Analysis

The hero remained alive at full health when mandatory potion discovery exhausted the planner. Decision 109 (log line 302) recognized a sentry without enough observed enclosure geometry or reward information to plan its protected round trip. That unresolved room reserved a missing haste supply. At decision 275 (line 785), this reservation blocked discovery; reconstructed bookkeeping excludes journey, drop, stash and trap-retrieval flags as alternative causes. A known clairvoyance stone was carried, but ordinary mapping required prior searches and never selected it. Offline reconstruction matched all 275 preceding selected actions, reasons and intents and reproduced the terminal blocker. The proposed correction admits one stationary, known-stone reveal of nearby missing sentry geometry before that veto, preserving threat, health, hunger, hazard, potion-protection and mandatory pickup gates. The new regression has two expected assertion failures on original policy and passes after correction; the full candidate suite passes 1783 tests with four skipped. Candidate reconstruction first changes only decision 275 and stops there. This establishes preparation selection, not an executed reveal, complete room observation, potion identification, collection or successful descent. Policy and regression edits are supplied in the working source; files is empty for trusted change extraction.

## Recommendations

- **000075-sentry-observation-preparation — Use safe known reconnaissance before incomplete sentry geometry exhausts mandatory discovery.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Run 000078 decision 109, log line 302: sentry recognition precedes departure from its incompletely observed entrance.; Run 000078 decision 176, log line 503: a known clairvoyance stone is publicly carried.; Run 000078 decision 274, accepted transition at line 783: movement advances time without damage.; Run 000078 decision 275, log line 785: missing room supply blocks mandatory discovery despite carried reconnaissance.; Original offline reconstruction matches all preceding actions, reasons and intents and isolates only the sentry haste demand.; tools/runestone_tactics.py:146–165 excludes ordinary clairvoyance before two searches; tools/descent_potions.py now admits narrowly bounded stationary reconnaissance.
  - Disposition: implemented

## Lessons for the next run

Before treating incomplete sentry geometry as exhausted preparation, consider a carried known clairvoyance stone from an observed safe square. Mapping must remain information gathering only: reobserve afterward and require all normal protection, inventory and retrieval checks. Never infer potion identities or room completion from the proposed reveal.

Update: **accepted**.
