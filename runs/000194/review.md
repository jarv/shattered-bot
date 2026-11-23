# ShatteredAI run 000194

Played commit: `0beaaaae6cbf404166af834317944678ff5405d6`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Distinguish a route back to a sentry entrance from an observation route that can actually reveal its missing perimeter. A meal and a known chest do not establish preparation feasibility. Preserve unknown potion identities, defended-carpet exclusions, mandatory pickups and explicit planner exhaustion.

## Analysis

The run ended in planner exhaustion with the Mage alive at full health, not an observed death. At decision 838 (log line 2429), a lone visible snake interrupted protected-potion preparation. The bot started a doorway lure even though its charged magic-missile staff had an admitted clear shot. That retreat created an escape commitment which later rejected the route back to the stored potions. Decisions 842 and 844 encountered reversal failures; decision 848 exhausted recovery. Abandonment correctly refused to leave owned retrieval unfinished. The later snake disappearance and experience gain are not used as a confirmed kill or evidence that separate sightings identify one actor. Offline reconstruction against the played source matched all 848 original action/reason selections. The candidate first differs at decision 838 and stops there. The focused proposal prefers the existing admitted ranged attack over a new optional lure during isolated-snake potion retrieval. Its new regression failed by assertion on original code, passed on the candidate, and the full suite passed 2,138 tests with four skips. This establishes selection and obligation preservation, not successful retrieval, identification or survival.

## Recommendations

- **000194-stash-snake-opening — Prefer admitted magic over a new isolated-snake lure while protected potions await retrieval.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 838, log line 2429: new doorway lure despite an admitted charged staff shot and owned potion retrieval.; Decisions 842 and 844, log lines 2445 and 2452: retrieval conflicts with escape reversal.; Decision 848, log lines 2464–2466: recovery exhausts while owned retrieval blocks abandonment.; tools/survival_policy.py:794–830; tools/potion_stash.py:165–214; tools/mage_policy.py:416–422.
  - Disposition: implemented

## Lessons for the next run

Do not let an optional new snake lure displace owned potion retrieval when an existing charged, permitted clear shot is available. Preserve the stash obligation, unknown potion identities, hazard checks and explicit planner exhaustion. A changed attack choice does not prove collection or eventual progress.

Update: **accepted**.
