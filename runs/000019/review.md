# ShatteredAI run 000019

Played commit: `b6ba6a94cf800b216f3f88a02d3084878b688519`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Killed by the great crab after tactical recovery stalled

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish a genuine mandatory strength target from optional food. Inspect recorded route boundaries and preparation admissions before changing selection. A supply fallback already exists; the next investigation needs an offline, recorded-input-validated state and a safe staging, protected-trip, and potion-protection fixture. Do not waive progression pickup, guess potion effects, or shorten waiting and call the problem solved.

## Analysis

The hero died to the great crab: decision 1966 accepted transition (log line 5659) reduced HP from 3 to 0, and terminal observation 5660 explicitly names the killer. Starvation was also observed. The fatal episode began earlier: after three doorway strikes, decisions 1774 and 1805 reported no admitted fresh surprise or escape-backed doorway, and recovery eventually waited beside the awake crab. Recharging alone could not defeat its guard. Separately, a supported initiating navigation defect wasted advancing turns before quest acceptance: the ghost was last observed at 731 in decision 1657; decision 1669 approached that already visibly empty cell, followed by the 690/691 orbit and navigation-loop at decision 1681. The proposed narrow correction declines this stale approach only after reaching interaction range and seeing the remembered cell empty. A reduced public-derived fixture reproduces the original selected cells; it is not a full runtime reconstruction. Six new regression tests fail with two expected assertions on original source and pass on the candidate; the full suite passes 1,546 tests with four skips. The correction does not establish safe ghost reacquisition or repair the fatal crab encounter. Pre-death potions remained unidentified; death-revealed identities are not usable preparation evidence. Mandatory progression pickup and pending reward return remain intact.

## Recommendations

- **000019-visible-empty-ghost-memory — Stop circling a visibly empty last-seen ghost cell after reaching interaction range.** (medium, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1657, log line 4709: ghost observed at 731.; Decisions 1669–1671, log lines 4733–4740: empty visible prior selects 732, 691, then 690 while time advances.; Decision 1681, log line 4769: navigation-loop on the stale ghost approach.
  - Disposition: implemented
- **000019-crab-surprise-recovery — Establish a bounded admitted surprise alternative before crab recovery degenerates into adjacent waits.** (high, deferred): The complete selecting chain is available, but no safe replacement has been established. Needed evidence is a recorded-input-validated policy state resolving crab-door attempts, pursuit exhaustion and escape commitment, plus an isolated fixture admitting a bounded surprise approach and second exit under the existing health and hazard checks. Without that, selecting a new route or guessing an unidentified potion would be speculative. This patch addresses only the independent stale-ghost orbit.
  - Evidence: Decisions 1708, 1718 and 1737, accepted log lines 4852, 4885 and 4938: doorway strikes leave the crab alive.; Decision 1774, log line 5039: no fresh surprise or admitted escape-backed doorway.; Decisions 1805 and 1863, log lines 5164–5165 and 5352–5353: tactical decline becomes adjacent waiting.; Decision 1966, log lines 5659–5660: lethal accepted wait and explicit crab death message.
  - Disposition: deferred
- **000018-strength-preparation-admission — Establish an admitted preparation route for the mandatory strength potion instead of exhausting resources in fallback.** (high, deferred): Complete source browsing resolves the selector and helper chain, but not a safe replacement. Recorded diagnostics establish the target and route veto, not an admitted unknown-potion preparation. Needed follow-up is an offline policy state validated against earlier recorded selections and a fixture demonstrating a safe approach/test bank, bounded protected strength retrieval, and protection of the other potions, or observed non-drinking identification. Snapshot-only probes do not establish these conditions; changing movement, potion assumptions, hunger admission, or the mandatory pickup gate would be speculative.
  - Evidence: Decision 2826, log line 8000: publicly revealed strength potion at cell 999.; Decision 2827, log lines 8002–8005: unreachable mandatory target, descent veto, and waterskin fallback.; Decisions 2829–2854, log lines 8009–8084: repeated advancing fallback waits.; Decision 3903, log lines 11150–11151: accepted wait and explicit starvation death.
  - Disposition: deferred
- **000013-pool-preparation-admission — Establish safe unknown-supply preparation for the mandatory piranha chest.** (high, deferred): This recording does not resolve the earlier pool-specific admission gap. The needed evidence remains a recorded-input-validated preparation state demonstrating a safe dry test bank, budgeted protected trip, and protection of other carried potions, or observed access to non-drinking identification. A strength-room diagnosis does not certify that pool repair.
  - Evidence: Run 000013: decisions 3014–3016 and 4063, retained backlog evidence.
  - Disposition: deferred

## Lessons for the next run

Do not orbit a remembered NPC coordinate after reaching interaction range and observing it empty. Preserve distant approach and mandatory reward return. For the crab stall, validate attempt and pursuit bookkeeping against recorded selections before testing a bounded surprise alternative; do not treat recharging or death-revealed potion identities as a solution.

Update: **accepted**.
