# ShatteredAI run 000020

Played commit: `515dee1a5721898463df9a14bfbb7cf8600458a5`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Starved while mandatory strength loot remained behind magical fire

## Improvements since the last run

- The bot no longer circles a remembered Sad Ghost location after reaching interaction range and seeing it empty. It still approaches distant remembered locations and returns for pending rewards.

## Incoming learnings

Do not orbit a remembered NPC coordinate after reaching interaction range and observing it empty. Preserve distant approach and mandatory reward return. For the crab stall, validate attempt and pursuit bookkeeping against recorded selections before testing a bounded surprise alternative; do not treat recharging or death-revealed potion identities as a solution.

## Analysis

The hero starved to death: decision 4553, accepted log line 12986, advances a wait from 1 HP to 0, and the final public message explicitly confirms starvation. The initiating unresolved work was the strength potion seen behind magical fire at decisions 3990 and 3992 (log lines 11306 and 11312). Recorded routing diagnostics reject access through the fire buffer. At first sighting HP was 66/75, below the unknown-potion test threshold; indigo and amber potions were unidentified. At decision 4438 (lines 12647–12650), the still-uncollected mandatory resource vetoed descent and fallback continued while starving. Source browsing resolves the priority-pickup, puzzle-supply, recovery and descent-veto chain. A snapshot-only probe finds local test banks but does not admit protecting the other carried potions. No patch is proposed: a safe preparation alternative has not been established, and relaxing hazards, guessing potion effects or waiving the mandatory pickup would be unsupported. No post-death identities are treated as earlier knowledge. The unchanged full unittest suite passes 1,546 tests, with four skipped. Offline bookkeeping reconstruction matched recorded actions and reasons through decision 3989, then stopped before selecting 3990 because its scratch state-export step could not serialize immutable configuration. This was not a gameplay crash. The local preparation probe was snapshot-only, not validated recovered runtime memory; no changed-policy continuation was evaluated. No patch or regression is supplied because a safe replacement preserving potion protection and health admission was not established.

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

## Lessons for the next run

Resolve preparation before health and food are exhausted, but require a demonstrated safe test/stash approach or observed non-drinking identification. Keep mandatory strength pickup, actual-effect verification and honest collection evidence. A preparation selection alone would not prove retrieval or survival.

Update: **review-only**.
