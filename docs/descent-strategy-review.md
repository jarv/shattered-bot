# Descent strategy review — 2026-11-22

## Objective

Go deeper with useful equipment, collecting chest, special-room and quest
rewards when their route and resource cost are admitted. Aim for approximately
one level gained per early floor: starting at level 1, the advisory departure
target is depth + 1 through floor 5. This is not an experience quota, a reason
to farm respawns, or permission to ignore starvation.

## Web research and source checks

1. [Tips and Tricks for Beginner and Intermediate players](https://steamcommunity.com/sharedfiles/filedetails/?id=2795315358)
   (updated February 2024): strength/upgrades, one-at-a-time choke fighting,
   equipment acquisition, alchemy, food efficiency and quest rewards.
2. [Mage walkthrough](https://www.youtube.com/watch?v=6AboIhx8q7o):
   early strength discovery, Ghost rewards, flexible upgrades after early staff
   investment, and alternatives to spending invisibility on fish.
3. [2024 beginner walkthrough](https://www.youtube.com/watch?v=Yzoz4E8LxFc):
   doors/surprise attacks, ranged attacks, food management, levels, identifying
   items and preparing before descending.
4. [Special rooms reference](https://pixeldungeon.fandom.com/wiki/Shattered_Pixel_Dungeon/Special_Rooms):
   room rewards and supplies; search excerpts were accessible but direct fetch
   was blocked. This reference is not used to infer hidden item identities.

Guides describe different releases and sometimes risky or build-specific
strategies. Mechanics relevant to this patch were checked against the pinned
game source `dc6687b3`: `PoolRoom` supplies invisibility, whereas this is not a
universal guarantee for every fish habitat; `Invisibility.DURATION` is 20 turns.
The existing Journey budget reserves travel, interaction and return time and
requires the actual observed buff. Knowledge of a potion's identity comes from
public inventory, never a generated-room prior.

## Coverage and changes

| Strategy | Bot assessment / action |
| --- | --- |
| Secure strength and upgrades | Already mandatory for observed progression pickups; fixed recovery stopping at 75% while discovery needs 85%. Same finite recovery allowance and hazard checks, no pharmacophobia drinking. |
| Spend first Mage upgrade productively | Existing `upgrade_tactics` invests in staff +1, then early staff power, with armor strength-breakpoint options and a flexible later reserve. Retained. |
| Collect equipment for later floors | Nearby resource-aware pickups previously recognized wands but omitted armor, weapons, rings and artifacts. Added them without auto-equipping unidentified or overweight equipment; sale and known-curse exclusions remain. |
| Resolve profitable special rooms | Added identified-invisibility activation from a visible, ordinary bank with one connected retreat corridor. Unknown-drink bank rules remain stricter. Door opening precedes spending the potion; observed buff, bounded round trip and actual reward handling remain required. |
| Avoid wasting food on indecisive travel | Run 114's published entrance-relative shop ranking retained. Run 115's contradictory pool preparation is replaced with an executable opening/activation sequence rather than repeated rejection at arrival. |
| Use doors as real tactical positions | Finished the run-82 repair: no doorway bonus for a one-square trap pocket or unknown exit; require an observed onward route. |
| Gain experience while progressing | Added an advisory level-versus-depth report. Existing ordinary exploration/combat continues; no farming or hard descent gate introduced. |
| Ghost / Wandmaker rewards | Existing quest controllers and pending reward checks retained. No wholesale abandonment of quest items based on a guide's optional special build. |
| Food/alchemy | Existing safe meat preparation, food triage and puzzle supplies retained. No speculative random-catalyst or gas use based merely on inventory possession. |

## Actual failures

- Run 113: living 19/25 HP hero, mandatory discovery rejected. Current full
  selection on its saved terminal observation chooses natural healing.
- Run 114: living full-health hero, 80 shop-search inputs exhausted. Published
  fix `83e1da6` orders entrance-side work before drifting outward.
- Run 115: full-health hero held known invisibility, but pool-bank arrival used
  unknown-potion safety assumptions. On saved D603, the candidate opens 1266;
  a synthetic accepted arrival then activates known invisibility for route
  1266 → 1265 → 1264 → 1263 → 1299 → 1335 → 1371.
- Run 115's *service* failure was separate: the review carried forward a trusted
  historical `rejected` status. Supervisor validation now permits unchanged
  historical dispositions only when they are not addressed by the new patch.
  New or changed self-assigned verdicts remain rejected.

## Validation and remaining gaps

Sequence regressions cover health recovery to the unchanged threshold, opening
the pool entrance, refusing hazard travel without a real buff, and a synthetic
protected retrieval/return. No game replay or improved win rate is claimed.

Further high-value work remains: verified ranged fish clearance for habitats
without invisibility; funded long-distance returns to special-room preparation;
fire-projectile impact and collateral accounting; and measuring equipment,
quest completion, floor turns and level progress across new runs. These are
better targets than increasing arbitrary wait limits or declaring unfinished
rewards collected.
