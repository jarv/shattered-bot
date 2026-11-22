# ShatteredAI run 000128

Played commit: `3c74ad985840c6cde4fd23da5e8ca177d47bdf31`

Outcome: dead

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: Died to a gnoll scout after fly pressure and a failed invisibility escape

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

Collection can invalidate every remembered discovery bank even when the added potion is identified. Preserve pickup, but plan bounded reobservation and freshly verified remote storage for the changed inventory before allowing the preparation obligation to exhaust. Reachability alone is not preparation safety.

## Analysis

The complete public death message confirms a gnoll scout killed the Mage. An earlier optional wand test cursed the worn armor with multiplicity (decisions 601–603, lines 1722–1726). Later, exhausted staff charges, physical fly splitting and converging enemies led to a boxed corridor; not every extra swarm can be attributed to the armor. Decision 842 retreats to an endpoint that is not a verified choke, and decision 843 observes a rat blocking the opposite side. At decision 856, all three ordinary exits are occupied, yet the bot drinks known invisibility. At decision 857 it cannot withdraw, then its last-resort attack immediately cancels that protection and loses four HP. Death follows after further combat and retreat.

Offline bookkeeping reconstruction of the played source matches all 861 recorded selections. The focused proposal prevents low-health last-resort attacks from overriding observed invisibility when existing rescue options decline. A new three-test regression fails with two expected assertions on original policy and passes on the candidate. All 1,919 tests across 198 independently run unittest modules pass; monolithic discovery was killed before completion. Candidate reconstruction matches decisions 0–856 and stops at its first divergence: planner exhaustion instead of decision 857’s attack. This prevents the protection bypass but does not establish an escape or fix the earlier encounter. No movement, recharge timing, loot collection or survival is invented. Files are left empty for trusted change extraction.

## Recommendations

- **000128-boxed-invisibility-fallback — Keep low-health last-resort recovery from attacking away observed invisibility when no escape is admitted.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decisions 601–603, lines 1722–1726: optional wand testing curses worn equipment.; Decisions 842–843, lines 2412–2418: retreat reaches an unverified endpoint, then opposing pressure blocks progress.; Decision 856, lines 2470–2471: known invisibility is activated with all ordinary exits occupied.; Decision 857, lines 2473–2474: last-resort melee cancels invisibility and HP falls from 14 to 10.; Decision 860, line 2484: the complete public message confirms a gnoll scout kill.; Source-pinned offline reconstruction matches all original selections; the candidate stops at the first changed decision, 857.; New boxed-invisibility regression: original assertion failures; candidate passes. Complete isolated unittest sweep: 1,919 tests pass.
  - Disposition: implemented

## Lessons for the next run

An empty escape route must not silently turn defensive invisibility into an attack. Preserve observed protection and report genuine planner exhaustion when no rescue is admitted. The next progress repair needs an earlier verified retreat or a bounded blocker-clearance plan funded by public protection, charge and damage evidence; target distance does not contain every cursed-wand effect.

Update: **accepted**.
