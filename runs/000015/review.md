# ShatteredAI run 000015

Played commit: `e960c76615c3c4a2212441a8cef538312939bb5b`

Outcome: blocked

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Blocked alive with the piranha chest still uncollected

## Improvements since the last run

- The bot now tracks moves made while preparing potion tests or opening special-room entrances, so its checks for getting stuck include those moves.

## Incoming learnings

Preparation movement needs explicit navigation semantics. Independently feasible stash and protected-trip plans may still oscillate at an auto-closing entrance. Detect that lack of progress without guessing potion effects or crediting unfinished rewards; choosing preparation is not puzzle success.

## Analysis

Blocked alive, not dead: decision 439 (log lines 1281–1282) waits at cell 281 with 25/25 HP while elapsed turns advance from 431 to 432. Mandatory pool retrieval remained unfinished. Initiating defect: after invisibility was publicly identified (decision 169, line 485), the known-supply staging helper still reused unknown-potion test-bank restrictions and a dry-only approach filter. Decision 174 (line 495) therefore explored instead of preparing the remembered chest. Offline reconstruction using the played source and public inputs matched actions and reasons through decision 174, including runner recovery and accepted-input bookkeeping. Its dry-run alternatives showed ordinary approach water at 410 outside the remembered habitat, an adjacent closed entrance at 449, and a budget-admitted chest trip to 646. The original helper rejected every candidate. The focused correction admits only identified-invisibility staging on observed ordinary water, retaining hazard exclusions, arrival visibility, actionable entrance opening and existing protected-trip budgeting. An isolated candidate probe on the validated pre-174 state selected approach movement instead; no subsequent observations were supplied. New regression: original source has two expected assertion failures; candidate passes all four cases. Full suite: 1535 tests passed, four skipped. Policy and new regression are changed locally; files is empty as required for adapter-derived changes. This does not establish completed retrieval, a safe unknown-potion test, or improved survival.

## Recommendations

- **000013-pool-preparation-admission — Establish a safe preparation strategy for pool entrances with no jointly admitted unknown-test bank and protected reward trip.** (high, deferred): Still deferred for unknown supplies: this recording establishes an identified-invisibility staging defect, not a safe unknown-potion test bank. A publicly justified identification or preparation mechanism is still needed for entrances where unknown-test safety and the protected trip cannot both be admitted. The proposed known-supply change does not alter those gates.
  - Evidence: Decision 103, log line 278: approach the observed pool entrance; Decision 104, log line 281: leave the entrance without potion preparation; Decision 334, log lines 961-963: mandatory pool veto and first fallback wait; Decisions 459-460, log lines 1336-1340: starvation meal does not resume pool work; Decision 588, log lines 1723-1725: advancing clock and blocked termination
  - Disposition: deferred
- **000015-known-pool-water-staging — Do not require an unknown-test bank to stage identified invisibility outside the pool habitat.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 169, log line 485: invisibility publicly identified; Decision 174, log line 495: known-supply preparation declines and exploration resumes; Decision 222, log lines 631–633: unfinished pool objective blocks descent; Decision 439, log lines 1281–1282: alive, advancing-clock fallback wait
  - Disposition: implemented

## Lessons for the next run

Separate identified protection staging from unknown-potion testing. Ordinary approach water outside the remembered piranha habitat can be considered only with observed hazard checks, a visible arrival recheck, an actionable entrance and a verified protection budget. Preparation is not collection.

Update: **accepted**.
