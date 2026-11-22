# ShatteredAI run 000130

Played commit: `0a4d2af0989bd84dfbff305ea8c8f60910f6b366`

Outcome: stuck-planner

Java build: `2f7b8780b93bf3121fe76e3bff17e440ee3d53bf17437817c212a9b738403137`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- At an established doorway, the bot can now attack a lone visible necromancer with an already-approved ranged attack instead of waiting for another summoned minion. It stays in place and preserves invisibility and targeting safeguards.

## Incoming learnings

A doorway controls approaching melee enemies, not a summoner’s ability to replace them. When the minion is gone, use an already admitted stationary ranged attack on the visible caster rather than granting free lure turns. Keep the established bank, protection, resource and targeting checks; do not assume the shot kills or the room is cleared.

## Analysis

The hero remained alive at full health when mandatory potion discovery exhausted. The initiating failure was exploration leaving the component permitted for preparation return: decision 312, accepted line 917, crosses from 1061 to grass 1062; at decision 313, line 919, the constrained return graph contains only the current cell. Offline reconstruction of the played source matches all actions and reasons for decisions 0–345 and reproduces the terminal blocker at decision 346, line 1013. Reconstructed bookkeeping retains 66 inventory-compatible bank receipts, but none is reachable through the terminal preparation graph. This is not inventory mismatch, hunger exhaustion or death. Both recorded preparation prerequisites decline. No patch is supplied: admitting the grass return would weaken an explicit flammable-terrain restriction, while an earlier preparation reservation still needs validated timing, storage, interruption and return-to-exploration semantics. Complete source and reconstruction resolve the selecting-state gap, not replacement safety. The unchanged full suite passes 1,926 tests with four skipped; no new regression or candidate success is claimed.

## Recommendations

- **000061-descent-bank-return — Establish preparation reservation before exploration disconnects every remembered discovery bank.** (high, deferred): Revalidated in this recording. The exact blocker is the strict return whitelist excluding flammable grass, not missing source or incompatible inventory. Terminal inventory has no known identification or reconnaissance resource. Adding grass would relax an existing safety restriction; early discovery alone does not establish legitimate timing and resumption of unfinished exploration. Next derive paired decision-307/312/313/346 fixtures around banks 919/921 and grass 1061/1062, then validate bounded preparation reservation before disconnection, fresh inventory-compatible bank/storage admission, accepted movement accounting, interruption handling and return to mandatory exploration/pickup. No safe complete transaction or new red/green regression is established, so no policy patch is proposed.
  - Evidence: Decision 307, selection line 901 and accepted line 902: exploration leaves 966 for 1012 with compatible preparation receipts.; Decision 312, selection line 916 and accepted line 917: exploration moves from 1061 to grass 1062.; Decision 313, line 919: reconstructed strict preparation-return graph contains only the current cell.; Decision 345, accepted line 1011: movement advances the clock at full health; decision 346, line 1013, exhausts mandatory discovery.; Source-pinned offline reconstruction matches decisions 0–345 and reproduces terminal exhaustion; all 66 compatible receipt probes decline.; tools/descent_potions.py:102–143,376–417; tools/mage_policy.py:492–495; tools/preparation_prerequisites.py:16–65.
  - Disposition: deferred

## Lessons for the next run

Reserve an executable preparation opportunity before exploration disconnects every compatible bank. Remembered feasibility alone cannot guarantee an admitted return. Preserve fresh bank and storage validation, actual consumption and pickup receipts, reserved supplies and terminal exhaustion.

Update: **review-only**.
