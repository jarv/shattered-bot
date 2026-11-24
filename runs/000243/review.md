# ShatteredAI run 000243

Played commit: `5be6e017af6c3149cc8b0a49f104fe5d724e404a`

Outcome: dead

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: Died to the great crab after repeated tactical-recovery waits

## Improvements since the last run

- The bot now recognizes a narrowly verified prismatic-light kill of a DM-100 even when its health bar was missing. Ambiguous evidence still leaves the lightning threat active.

## Incoming learnings

A missing enemy health bar must not erase independently verifiable kill evidence. For a known uncursed prismatic zap, require consumed charge, one-turn six-XP receipt, Arcane Vision, a freshly observed clear ray, a single eligible target and no surviving caster before retiring its matching lightning memory. Keep ambiguous sightings, mandatory pickups, hazard gates and terminal planner exhaustion unchanged.

## Analysis

The hero died, not a stuck planner. The complete terminal observation explicitly says the great crab killed the Mage (decision 1924, accepted transition at log 5677), resolving the packet’s unknown killer. Earlier, a doorway-surprise plan survived intervening fly combat: its last dedicated wait was decision 1846 at turn 1838, but decision 1863 at turn 1847 attacked a crab already repeatedly observed in doorway 918 (logs 5426–5454). The accepted attack did not reduce its visible health bar, and the next observation reported its claw block. The selector mistook stale plan history for fresh entry. A focused correction now retires a lure’s surprise claim after a multi-turn interruption and reuses unchanged escape admission. A reduced public-map fixture selects retreat to 856 instead of that blocked strike; original policy fails its assertion and the candidate passes both new tests. The full Python suite passes 2,269 tests with four skips. Plan fields in the fixture are explicitly reconstructed, not recorded runtime memory; contiguous local original-controller selections 1841–1846 were checked against the recording. This does not establish survival or quest completion. A separate unresolved retreat contradiction remains: decisions 1885–1888 moved toward the room edge, then decisions 1889–1924 waited at 790 as health declined. No planner incidents were recorded. Unknown potions remain unknown, and unfinished rewards are not credited. The adapter derives changed files; the files list is intentionally empty.

## Recommendations

- **000243-interrupted-crab-surprise — Invalidate stale doorway-surprise claims after intervening combat.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: Decision 1846, log 5408: last dedicated lure wait at turn 1838.; Decisions 1853–1862, logs 5426–5453: fly combat while the crab occupies doorway 918.; Decision 1863, logs 5454–5456: purported fresh surprise has zero observed health-bar loss.; tools/great_crab_tactics.py:102–127; tools/ghost_quest.py:392–397.
  - Disposition: implemented
- **000243-crab-room-edge-retreat — Establish an executable crab escape before retreating toward a room edge.** (high, deferred): Not repaired by surprise freshness. At decision 1889, the observed clean alternatives 760 and 791 are both adjacent to the crab at 759; existing escape routes cross its immediate approach. Relaxing separation, second-exit or exposure checks would not certify safe movement. No known invisibility or healing supply is recorded. Next derive paired decision-1885 and decision-1889 fixtures, prove a threat-separated exit continuation or receipt-checked camouflage preparation from public terrain, and require a positive progress regression before changing retreat scoring. Do not extend waits or guess the magenta potion.
  - Evidence: Decisions 1885–1888, logs 5543–5556: separation retreats end at 790.; Decision 1889, logs 5559–5561: quest combat declines and recovery waits.; Decision 1924, logs 5676–5677: final wait and explicit great-crab death message.; tools/great_crab_tactics.py:187–208; tools/tactical_recovery.py:113–186.
  - Disposition: deferred

## Lessons for the next run

A doorway entry claim must expire when intervening combat consumes multiple turns; a cached last-seen position is not fresh surprise evidence. Preserve observed second exits and direct-attack restrictions. Separately, inspect crab retreat continuation before choosing room-edge separation over executable exit progress.

Update: **accepted**.
