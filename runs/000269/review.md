# ShatteredAI run 000269

Played commit: `764a93f3e9ece175422fe9346e155a91a32f08ae`

Outcome: stuck-planner

Java build: `51bdb688a8fed22859aa80c5a30a841418fb3c1d6da0f7e728dd727d4914879c`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now recognizes a tracked frost-wand kill of a DM-100 from a spent charge and observed experience gain, even without a defeat message. Chilled targets are supported, but frozen targets still require other evidence.
- After actually reaching a gas-room scouting approach, the bot remembers that visit instead of repeatedly turning back from other floor work. Returning there still does not authorize potion testing or claim the reward was collected.

## Incoming learnings

A tracked frost kill can award XP without a rendered defeat message. Validate the consumed charge, clear ray, one-turn six-XP receipt and absence of a tracked survivor before retiring only that matching threat. Chilled targets remain hittable; frozen targets do not establish this receipt. Retirement must not grant loot or floor-clear credit.

## Analysis

The run ended with a living hero at 23/30 HP, not an observed death. D815 (log lines 2375–2377) reports mandatory potion-discovery exhaustion: unknown drinking requires 85% health, while the natural-recovery allowance was already spent. Earlier combat attrition and bounded recovery explain the shortfall; the final accepted movement still advanced the clock. Emergency healing only activates at much lower peaceful health, leaving an observed 11/20 waterskin unused. Source inspection resolved the selecting-chain gap. A reduced public-evidence fixture and a separate fresh-policy terminal-snapshot probe admit existing bank staging at full health, but neither recovers original mutable memory. The proposed correction funds this specific prerequisite with sufficient known dew only when a detached preview admits a continuation. It preserves unknown-drink safety, inventory protection, mandatory pickups, emergency healing supplies and terminal exhaustion. The new regression fails with two expected assertions on original policy and passes after the change; the full suite passes 2,474 tests with four skips. No game execution or changed-decision continuation was performed. Preparation selection does not establish successful healing, discovery or survival.

## Recommendations

- **000269-discovery-dew-preparation — Provision admitted mandatory discovery with sufficient known dew before declaring health-preparation exhaustion.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D775–780, logs 2255–2282: combat retreat reduces health from 30 to 21.; D791–795 and D807–812, logs 2318–2368: bounded natural healing leaves 23/30 HP.; D815, logs 2375–2377: mandatory discovery stops despite an observed waterskin at 11/20.; tools/policy_nodes.py:135–146; original tools/descent_potions.py:278–336: low emergency-healing threshold and mandatory unknown-drink health veto.
  - Disposition: implemented

## Lessons for the next run

Mandatory discovery needs an explicit health prerequisite, not just a health veto after natural recovery runs out. Known displayed dew can fund that prerequisite without guessing potion identities, but actual healing and every subsequent testing or retrieval step still require fresh public observations.

Update: **accepted**.
