# ShatteredAI run 000159

Played commit: `1bdd290a11b8c38fbafbc8341df4e59ab3448ea3`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now uses a quiet opportunity to cleanse a known cursed spare wand, even when it is not equipped. Cursed worn equipment keeps priority, and the bot keeps its chosen cursed target when opening another bag.

## Incoming learnings

A wand need not be equipped to justify cleansing. Prepare a publicly known cursed spare during a quiet, freshly observed opportunity, preserve worn-curse priority, and keep its target through bag navigation. Do not infer successful cleansing, charge capacity or survival from choosing preparation.

## Analysis

The run ended in planner exhaustion with the hero alive at full health, not an observed death. The upgrade scroll first appeared at decision 702 (log 2033); its square was revealed as a shocking trap at decision 717 (log 2074). An unconfirmed levitation test at decision 730 instead produced observed cold effects. Recovery moved the hero off the hypothetical route; when a gnoll interrupted recovery at decision 733, the journey checked displacement before checking whether protection ever appeared. That false obligation disabled further room journeys. The proposed narrow correction retires only unstarted hypotheses without observed protection, preserving displacement checks for actual trips. A reduced public-evidence regression fails on the original policy and passes on the candidate; the full suite passes 2,009 tests with four skips. This does not resolve the separate final pickup barrier: decision 810 diagnostics still show the mandatory scroll on an active shocking trap, without carried levitation or unknown potions. No safe electrical clearing controller is established, and neither collection nor successful continuation is claimed.

## Recommendations

- **000159-failed-protection-journey — Retire an unstarted protection hypothesis before checking displacement when its required buff never appeared.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 730, log 2107: unconfirmed levitation test.; Decisions 731-732, logs 2110-2114: actual cold recovery leaves the planned bank.; Decision 733, logs 2115-2118: false displaced-journey obligation and tactical fallback.
  - Disposition: implemented
- **000159-shocking-progression-pickup — Develop a verified electrical-trap clearing plan for mandatory loot, including connected water and observed expiry.** (high, deferred): Unaddressed by the single narrow correction. The existing remote-clearing controller admits only chilling traps; electricity also propagates through connected water, so copying its radius check is unsafe. The terminal inventory supplies no known flight. A separate repair must prove the publicly bounded water footprint, collateral safety, projectile bank and return route, then observe disarm and electrical expiry before retrieval. No such replacement is certified here.
  - Evidence: Decision 717, log 2074: upgrade scroll lies on a revealed shocking trap beside water.; Decision 810, log 2343: active trap excludes the mandatory pickup despite no general threat veto.; Decision 810, logs 2344-2345: planner exhaustion with the hero alive.
  - Disposition: deferred

## Lessons for the next run

Check whether experimental protection actually appeared before treating a dry-run route as an active journey. Failed-effect recovery can legitimately leave that route. Keep mandatory progression loot pending and retain hazard vetoes; electrical traps near water need a separately verified clearing and expiry plan, not a cold-trap shortcut.

Update: **accepted**.
