# ShatteredAI run 000235

Played commit: `669d98accb8150d3d94b5ab10d89409802027935`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot now prefers an available ranged attack against a visibly sped-up necromancer’s skeleton while holding a doorway, rather than immediately trading ordinary melee blows.

## Incoming learnings

A doorway limits approach slots, but does not remove skeleton armor or caster support. After the first surprise strike, prefer an already admitted ranged attack against a visibly adrenalized linked skeleton. Preserve caster targeting, projectile checks, critical-health handling, mandatory pickups and honest receipts; do not infer a finishing hit or survival.

## Analysis

The hero remained alive with 14 HP when mandatory preparation exhausted; this was not an observed death. D4074 (log 11645) identifies the unresolved target as an iron key behind magical fire, not the previously collected strength potion. Starvation excluded unknown-potion testing, and no known frost or safe identification supply was carried. Earlier, D3308 (log 9411) offered Craft: magefruit after blandfruit and mageroyal were selected, but the bot exited because it expected the internal name dreamfruit. Two later attempts repeated this failure. The pinned game confirms that English name alias. This lost a concrete food-preparation opportunity before the later starvation blockage, although its effect on the final outcome is unproven. The proposed narrow repair accepts that exact offered recipe alias and tracks its actual inventory name without inventing acquisition. A new regression fails by assertion on original source and passes after repair; the full suite passes 2255 tests with four skips. No gameplay replay or full runtime-memory reconstruction was used. Mandatory pickups, starvation testing restrictions and fire safety remain unchanged.

## Recommendations

- **000235-mageroyal-craft-preview — Recognize the offered magefruit name for the known mageroyal fruit recipe instead of abandoning preparation.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D3301–D3308, log lines 9397–9411: selected ingredients lead to an offered magefruit craft but Back is chosen.; D3324 and D3339, log lines 9447 and 9481: repeated recipe exits.; D3542, log line 10102: next-floor arrival already starving.; D4074, log line 11645: mandatory iron key remains behind magical fire; preparation is exhausted.
  - Disposition: implemented

## Lessons for the next run

Verify known recipes against their publicly rendered output names. A recipe preview is not acquisition: retain pre-craft counts and require actual inventory changes. Repairing the missed fruit craft does not establish later frost identification, key collection or survival.

Update: **accepted**.
