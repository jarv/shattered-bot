# ShatteredAI run 000011

Played commit: `ad9b3e2b25aa5fc5228c35d9a4292c9f582abaef`

Outcome: blocked

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Blocked alive after secret discovery suppressed missing-exit searches

## Improvements since the last run

- Delay new Sad Ghost dialogue and quest preparation until observed exploration and required locks are resolved; preserve reward-return behavior.
- Route Great Crab combat through a dedicated controller and release its plan on public quest-completion dialogue.

## Incoming learnings

Before exhausted ranged arbitration enters best-effort continuation, consider carried, identified point-target control. Preserve clear-shot, eligibility, cooldown, hazard and mandatory-pickup constraints. Selecting sleep is not evidence that it landed or that escape became safe.

## Analysis

Blocked alive after fallback waiting, not a death or frozen clock. Decision 1055's public input showed wall 565; decision 1056 showed a closed door there (log lines 3069 and 3072). The discovery correctly sets a floor-local secret flag. The defect is downstream: tools/survival_policy.py:1104–1108 then suppresses general wall searches even when no reachable exit exists. At decision 1075 (lines 3128–3130), there were no frontiers or corridor-end candidates, zero searches and available search budget; exploration raised a blockage and continuation selected waiting. All 256 decisions from 1075 through 1330 were last-resort waits. The final accepted wait advanced the clock and left HP at 35/35. Offline bookkeeping reconstruction, not originally recorded memory, validated original actions and reasons through decision 1075 against the pinned source and saved public inputs. Candidate reconstruction matched through 1074 and stopped at its first changed selection, a search-vantage approach at 1075. The focused correction retains bounded missing-exit searches after secret discovery while preserving optional suppression when an exit exists. The new regression fails by assertion on original policy and passes on the candidate; all 1494 suite tests pass, with four skipped. No search result, exit discovery, completed loot or survival improvement is established. The trusted adapter supplies changed files; files is intentionally empty here.

## Recommendations

- **000011-missing-exit-after-secret — Retain bounded missing-exit wall searches after a secret discovery.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1055, log line 3069: visible wall 565; Decision 1056, log line 3072: visible closed door 565; Decision 1075, log lines 3128–3130: zero searches, no reachable exit, accepted fallback wait; Decision 1330, log lines 3894–3895: final wait advanced time; hero remained alive
  - Disposition: implemented

## Lessons for the next run

Finding one secret does not establish that an exit is reachable. Keep necessary bounded missing-exit search distinct from optional secret-room hunting. A search-vantage selection is preparation, not evidence of a door or successful progression.

Update: **accepted**.
