# ShatteredAI run 000248

Played commit: `b2f236f0d5930513bb3f71d713cd697bdc3a6184`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- When a special-room potion has been spent elsewhere, the bot now checks for unexplored passages and unopened doors before taking the early stairs option. It leaves the unfinished room deferred rather than treating the rest of the floor as finished.

## Incoming learnings

A spent supply defers its own room, not all remaining floor exploration. Preserve ordinary observation opportunities before invoking departure-only strength discovery; keep mandatory pickup, protection and actual collection receipts unchanged.

## Analysis

The recording ends with a living hero at 3 HP, not an observed death. Decision 3039 (log lines 9063–9065) reports exhausted exploration without a reachable exit; four wall searches and the final scry did not expose an admitted continuation. An earlier, repairable contributor is stale caster memory: decision 2980 (lines 8895–8897) attacks the adjacent DM-100, advances one turn, gains six XP across a level-up, and appends a second identical defeat message after retained pickup messages. tools/combat_observation.py:248–261 used text-set novelty, so it missed that new receipt. Decision 2986 (line 8913) then explicitly flees an unseen remembered caster at 1046 through decision 2996, followed by retracing the route toward the mandatory iron key. The proposed narrow correction recognizes a replacement defeat entry using its changed order relative to a unique retained pickup message; it retires only matching caster memory and its matching plan. It does not infer a kill from disappearance or XP alone, authorize movement, or waive key pickup. A reduced public-evidence regression failed on the original policy and passes with the correction; the full suite passes 2,284 tests with four skips. An isolated exact receipt-pair probe also retires the matching memory, without selecting or dispatching a subsequent action. This does not establish that the extra travel caused terminal exhaustion, that another route would survive, or that the missing exit would be found. Separately, decision 1997 (lines 6085–6088) records an unfinished piranha chest blocking descent. Recovery actually descends at decision 2039 (lines 6304–6306), without collection credit; that is not a pool-planner repair. Offline bookkeeping reconstruction validated selected inputs 0–1996 against this played source and the saved public observations; it is not originally recorded memory. At decision 1997, isolated copies have no deferred supply controller or active stash/probe, but none of 16 currently visible safe testing banks admits an actionable protected pool journey. Preparation declines. No changed decision was followed with fabricated observations.

## Recommendations

- **000248-repeat-caster-defeat — Retire matching caster memory when an identical defeat message is demonstrably newly appended.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 2980, log lines 8895–8897: accepted melee, level-up and replacement defeat entry after retained pickup text.; Decision 2986, log line 8913: remembered-caster flight begins with no visible caster.; Decisions 2986–2996, log lines 8913–8944: committed detour precedes mandatory-key retracing.; tools/combat_observation.py:248–261; tools/dm100_escape.py:47–78,200–265.
  - Disposition: implemented
- **000237-pool-round-trip-preparation — Resolve the unfinished pool preparation that triggered the earlier recovered planner incident.** (high, deferred): The stale-caster correction does not repair this independent incident. Reconstruction matches inputs 0–1996. At decision 1997, supplies are not controller-deferred and no stash/probe is active; the pool demand remains. Isolated copies admit 16 visible testing banks but no actionable protected pool journey, and preparation declines. Thus removing the hunger veto or adding a meal alone does not certify progress. Next derive the pool entrance/terminal pair and enumerate protected-return and revisit rejection conditions from the validated in-memory state, then prove a jointly executable bank, storage and actual-protection-funded return transaction. Do not infer invisibility or collection, or relax bank/hazard checks.
  - Evidence: Decisions 1334–1350, log lines 4042–4085: testing, storage and cold-effect recovery.; Decision 1997, log lines 6085–6088: uncollected chest 147 blocks descent.; Decision 2039, log lines 6304–6306: actual recovery descent without collection credit.; tools/puzzle_supplies.py:747–842,1006–1053; tools/potion_stash.py:95–133.
  - Disposition: deferred
- **000248-missing-exit-preparation — Establish a funded missing-exit continuation before terminal search exhaustion.** (high, deferred): At the terminal observation there is no reachable known exit, no food or known healing potion, starvation is active, the four-search allowance is spent, and the talisman has only 19% charge. The recorded map does not certify an additional safe progress route. Extending bounds, speculative movement or guessed potion effects would not repair this safely. Next derive paired floor-entry and first-search fixtures and validate an earlier hunger-funded missing-exit observation transaction under existing hazard admission; the caster correction alone does not prove one exists.
  - Evidence: Decision 2920, log line 8722: arrival on the final floor with no carried food.; Decisions 3023–3036, log lines 9021–9058: four searches and intervening travel reduce HP from six to three.; Decisions 3037–3039, log lines 9059–9065: final scry followed by planner exhaustion.; tools/survival_policy.py:1120–1183; tools/mage_policy.py:841–882; tools/artifact_tactics.py:200–209.
  - Disposition: deferred

## Lessons for the next run

A repeated defeat message can be newly appended even when its text is already on screen. Use a conservative ordered receipt witness to retire only the matching remembered caster; disappearance alone remains insufficient. Keep mandatory key collection and terminal planner exhaustion intact. Recovered pool abandonment and terminal missing-exit exhaustion remain separate unresolved planning failures.

Update: **accepted**.
