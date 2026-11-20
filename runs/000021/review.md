# ShatteredAI run 000021

Played commit: `f91ecf358b7d899aab51c07c42e44eca03b27e13`

Outcome: blocked

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Blocked after frost preparation failed and an uncollected key prevented descent

## Improvements since the last run

- The bot now tracks potion-bandolier protection when preparing unknown potion tests, including stacked potions. It still requires observed acquisition and treats possible overflow cautiously.
- When a strength potion or upgrade scroll has no admitted pickup route, the bot can use a known mapping scroll after puzzle preparation declines, without first requiring optional searches.

## Incoming learnings

Resolve preparation before health and food are exhausted, but require a demonstrated safe test/stash approach or observed non-drinking identification. Keep mandatory strength pickup, actual-effect verification and honest collection evidence. A preparation selection alone would not prove retrieval or survival.

## Analysis

The run blocked alive, rather than dying. Decision 219 (log 609) began a frost-test approach without an admitted route for protecting the other unidentified potions. Decisions 220–222 (logs 612–620) reached the bank, failed the stash check and deferred potion preparation for the floor. Decision 247 (logs 695–698) then hit the descent obligation; its diagnostics identify an iron key, not a newly observed strength potion. The generic progression warning covers keys too. Fallback advanced the game clock but did not resolve that obligation. Offline bookkeeping reconstructed from this source and recorded public inputs matches original actions and reasons through decision 222. Isolated probes on validated state find no stash route from the selected banks. The proposed correction checks protection before starting a remote frost approach, while preserving actual current-bank checks, hazard restrictions and mandatory progression pickup. Candidate reconstruction stops at its first changed decision, 219; no later observations are fed to it. This establishes an approach-admission defect, not a safe replacement route or puzzle success.

## Recommendations

- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): This fire-room recording does not establish a safe crab surprise alternative. The earlier case still needs recorded-input-validated doorway-attempt, pursuit and escape bookkeeping plus an admitted bounded surprise approach with a second exit under existing health and hazard checks.
  - Evidence: Decisions 1708, 1718 and 1737, accepted log lines 4852, 4885 and 4938: doorway strikes leave the crab alive.; Decision 1774, log line 5039: no fresh surprise or admitted escape-backed doorway.; Decisions 1805 and 1863, log lines 5164–5165 and 5352–5353: tactical decline becomes adjacent waiting.; Decision 1966, log lines 5659–5660: lethal accepted wait and explicit crab death message.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish an admitted preparation route for the mandatory strength potion instead of exhausting resources in fallback.** (high, deferred): Full source browsing resolves the selecting helper chain. However, the first-sighting hero is below the unknown-test health threshold, and a public-snapshot probe rejects potion protection at both local test banks. Needed follow-up is a recorded-input-validated bounded preparation state admitting a stash/test approach and subsequent retrieval, or observed non-drinking identification. Neither removing the hazard buffer nor waiving the strength obligation is justified.
  - Evidence: Decision 2826, log line 8000: publicly revealed strength potion at cell 999.; Decision 2827, log lines 8002–8005: unreachable mandatory target, descent veto, and waterskin fallback.; Decisions 2829–2854, log lines 8009–8084: repeated advancing fallback waits.; Decision 3903, log lines 11150–11151: accepted wait and explicit starvation death.; Run 000020: decisions 3990 and 3992, log lines 11306 and 11312, reveal strength beyond magical fire with HP below unknown-test admission.; Run 000020: decision 4438, log lines 12647–12650, retains the mandatory pickup veto; decision 4553, accepted line 12986, ends in confirmed starvation.
  - Disposition: deferred
- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): This fire-room recording does not establish a safe pool preparation alternative. The earlier case still needs recorded-input-validated dry test-bank and remote potion-protection admission plus a budgeted protected chest trip, or observed non-drinking identification.
  - Evidence: Run 000013: decisions 3014–3016 and 4063, retained backlog evidence.
  - Disposition: deferred
- **000021-frost-approach-stash-admission — Check potion protection before starting a remote frost-test approach.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 219, log 609: frost staging begins without an admitted stash route.; Decisions 221–222, logs 615–620: arrival leads to stash veto and floor-wide potion-preparation deferral.; Decision 247, logs 695–698: uncollected matching key prevents descent.
  - Disposition: implemented

## Lessons for the next run

Check potion-protection feasibility before walking toward an unknown frost test. An infeasible unstarted approach should not consume floor-wide preparation availability. Continue to require real stash, effect and collection evidence; selecting another action does not establish retrieval or survival.

Update: **accepted**.
