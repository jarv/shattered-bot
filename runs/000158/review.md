# ShatteredAI run 000158

Played commit: `ae207fa94dbfc168b5a6e05e2be3a38ca2588bf1`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Killed by a gnoll scout after prolonged fly pressure

## Improvements since the last run

No code changes since the last run.

## Incoming learnings

A preparation bank admitted from a departure observation may become unusable after door closure or loss of storage visibility. Validate departure effects and an executable protected-storage transaction before committing transit. Keep unknown identities, hazard checks, mandatory pickup and explicit planner exhaustion intact.

## Analysis

The full recording confirms death: decision 1230, accepted log line 3737, explicitly identifies a gnoll scout as the killer. Earlier fly exchanges depleted health while magic was exhausted. A concrete preparation omission precedes that fallback: decision 867, accepted line 2478, publicly reveals a cursed disintegration wand. Decisions 878 and 888 (lines 2502 and 2532) retain that spare and an identified remove-curse scroll during quiet observations, but the equipped-only cleanse selector ignores the wand. Decision 1126 (line 3297) still carries both while the staff is empty and physical fly fallback begins. The focused correction permits conservative quiet spare-wand cleansing and preserves its menu target across bags, without claiming cleansing or charges before public confirmation. The new five-test regression has three expected assertion failures against original selectors and passes on the candidate; the full suite passes 2,005 tests with four skips. Fixtures are public-evidence reductions and independent UI contracts, not reconstructed original runtime memory or a changed-policy replay. This establishes a preparation defect, not that repairing it would prevent death. Historical backlog cases were not revalidated.

## Recommendations

- **000158-cursed-spare-wand-preparation — Cleanse a publicly known cursed spare wand during safe preparation instead of leaving the resource unusable.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 867, accepted log line 2478: the disintegration wand is publicly revealed cursed.; Decisions 878 and 888, selection lines 2502 and 2532: the known cursed spare and identified remove-curse scroll remain carried during quiet observations.; Decision 1126, selection line 3297: empty staff, cursed spare and unused cleanse scroll accompany physical fly fallback.; tools/policy_tree.py:34; tools/policy_nodes.py:153-175; tools/consumable_tactics.py:215-245.
  - Disposition: implemented

## Lessons for the next run

A wand need not be equipped to justify cleansing. Prepare a publicly known cursed spare during a quiet, freshly observed opportunity, preserve worn-curse priority, and keep its target through bag navigation. Do not infer successful cleansing, charge capacity or survival from choosing preparation.

Update: **accepted**.
