# ShatteredAI run 000119

Played commit: `cf2fce2e89f162e9e9a22172bb36f854918c8dfe`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot no longer saves every unidentified potion for a merely possible reward behind bookshelves before seeking strength. Observed barricades and rewards separated by shelves still keep their potion reservations, and unexplored shelves remain unfinished.

## Incoming learnings

A puzzle-backed meal and a hypothetical flight route do not establish an executable potion test. Check structural bank feasibility before attributing failure to hunger, stale visibility or door reclosure. Keep unidentified colors unidentified and preserve the chest obligation. Next derive the eleven-origin grass/water/entrance fixture and validate a contained preparation or nonconsumptive identification transaction before changing admission.

## Analysis

The hero remained alive at full health when the planner stopped. Four accepted thief interceptions had already spent the floor-wide species chase allowance (decisions 2290, 2293–2295; lines 6720, 6728, 6731, 6734). The last accepted melee at decision 2755, line 8062, left a visible thief two cells away with the staff empty. Decision 2756, line 8063, then exhausted. An identified deep-sleep stone was carried, but the thief controller stopped before disabling utility; ordinary sleep use also required low health. A reduced public-input regression reproduces this exclusion. The proposed correction retains a known targeted sleep throw for a lone visible thief after attacks and the chase allowance are exhausted, without extending pursuit or crediting a defeat. Original-source tests fail the two expected selection assertions; the candidate passes all five new tests and the full 1902-test suite, with four skips. Isolated helper probes match the preceding two recorded melee selections, but do not reconstruct all original runtime memory. Selecting sleep does not establish successful application, subsequent progress or survival.

## Recommendations

- **000119-exhausted-thief-sleep — Retain a known deep-sleep throw before exhausting against a lone thief after the bounded chase is spent.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 2290, 2293–2295; accepted movement receipts at lines 6720, 6728, 6731, 6734 reach four species-budget moves.; Decision 2755, selection line 8061 and accepted line 8062: melee leaves the hero at full health and the visible thief two cells away.; Decision 2756, line 8063: empty staff and carried identified deep-sleep stone coincide with thief planner exhaustion.; tools/unit_strategies.py:42–60 and original 120–121; tools/runestone_tactics.py:85–89.
  - Disposition: implemented

## Lessons for the next run

Exhausted pursuit does not mean every useful action is exhausted. Check known single-target disabling resources before a species-specific terminal veto, retaining visibility, clear-shot, eligibility and cooldown checks. Do not reset chase budgets or infer sleep, defeat or collection from a selected throw.

Update: **accepted**.
