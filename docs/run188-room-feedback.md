# Run 188 room feedback

## Evidence and scope

Run 188 used bot `0d82ea4e758c7b9de0fc0088f18add45699252f8`
and game source `a107d1fd1e737ccc71fa52020fa1c6bc58e58b4e`.
The local implementation starts from `cffdbcc2fee632406b5cfe7a230cfc6ceb95f732`.
Saved public inputs are in `/tmp/opencode/run188-decisions.jsonl`.
No live game was replayed, interrupted, or repinned.

The selector probes below accumulate publicly observed geometry, not recovered
runtime controller memory. They are not full-policy replay or collection evidence.

## Implemented locally

### Crystal-room search precedence

The silver-looking doors are `Terrain.CRYSTAL_DOOR` (31), not iron-key doors.
`CrystalPathRoom.paint` creates six doors and spawns three crystal keys.
`SpecialRoom.maxConnections` permits only one external connection.

Search hypotheses now exclude observed walls surrounding crystal-door/chest
interiors, delimited by ordinary doors. This applies to required corridor tips,
ordinary wall search, broad missing-exit fallback, and pending search goals.
It does not disable search on the rest of the floor, spend a search receipt, or
certify unknown geometry. Remembered exclusions survive opening the chest/doors
and reset on the next floor.

### Gather the path room's keys before unlocking

Six observed crystal doors in a connected enclosure establish the three-key
path-room requirement. Recognition may connect across crystal thresholds, but
ordinary doors delimit the enclosure; that recognition flood is never a
movement route. Nested inner doors must count, not just the four doors directly
adjoining the vestibule.

Both crystal reward selection and ordinary path admission refuse a first spend
until three keys have actually been observed held/collected. Subsequent spends
retain the witnessed total. One-key chest/door choices and single pit exits are
not given a three-key requirement.

### Known flame at a narrow barricade

Floor 1 has the barricade at 533 and a nonflammable approach through 534/535,
with an ordinary door at 536. The old throwing-bank neighborhood restriction
rejects that corridor. Known flame can now use a bank two cells away, outside
the splash/fuel area, with a distant door allowed only outside the expanded
exposure area. Exposed doors, fuel, plants, traps, valuable loot, and actors
remain vetoes.

This uses `PotionOfLiquidFlame.shatter`'s radius-one splash and `Fire.evolve`'s
flammable-only propagation. It does not admit entering active fire or infer that
the barrier burned away. The existing verified-clearance workflow remains.
An isolated public-geometry probe selects a staging move at input 120; it is
not evidence that a changed live run reached or cleared the barricade.

### Flight-room water alcove

At input 959, the reward is the chest at 1444. A budgeted flight trip can start
at 1152, but the safe-test-bank gate rejects it: it has one ordinary water
retreat through 1110, not two. That retreat continues onto observed ordinary
floor/water. A water flight alcove may now use that one continuing retreat,
provided both retreat steps are freshly visible, observed and hazard-free, and
its adjacent entrance has an accepted scout receipt. Inputs 816–817 show the
earlier real doorway arrival. An unexecuted opening or a merely open door does
not qualify.

With that explicit receipt in the isolated fixture, the selector can admit 1152
rather than another generic approach revisit. Stash isolation, fresh arrival checks, entrance receipts,
near-full health and actual levitation/return budgeting still apply. No drinking,
protection, or collection is claimed from this probe.

### Ghost continuation

Inputs 1064–1065 contact the Ghost and accept its fetid-rat request. Input 1066
immediately selects a stair-bound move. Activation was not the missing step:
there was no bounded search for the newly spawned, unseen quest enemy.

An active, same-floor quest now gets ordinary-floor reconnaissance before
generic exploration/descent. It yields to threats and impaired/low health,
requires a funded route, preserves its selected vantage through travel, and
has a 64-input budget. Only actual standing arrival records a visited vantage.
Exhaustion or unsafe geometry leaves the quest unfinished, never rewarded or
completed. Existing quest combat and reward receipts are unchanged.

### Goo sales

`GooBlob.value()` is 30 gold per blob; `energyVal()` is 3 energy per blob.
Goo can now enter the existing nearby-shop sale workflow, including stacked
items and the public “Sell 1 for …g” quote. A sale still requires both one
inventory removal and the exact observed gold gain. Goo is not added to
ground-discard candidates, and no unsupported alchemy recipe is invented.

## Follow-up implementation: multi-reward trips and early recognition

### Floor 3 piranha preparation

**Correction to the initial investigation:** fish first appear at input 1474,
without a chest. Input 1511 briefly shows the chest at 1086, alongside fish at
991, 1040 and 1088. The earlier statement that the recording never showed a
chest was wrong. Before that sighting, reward-keyed memory and preparation
cannot bridge the information gap.

`piranha_profile.py` now creates habitat memory at the first fish sighting,
without a reward coordinate. Observed water against a wall plus a special-floor
entrance strip and ordinary doorway is a treasure-pool profile; a fully observed
dry ring instead identifies an aquarium. Partial geometry stays a candidate,
with up to four dry scout arrivals / 48 approach inputs. Ordinary scouting
retains the whole fish habitat/shore exclusion, not a last-seen fish-distance
guess (piranhas have double movement speed).

A matched profile can plan an invisibility survey without a chest. That survey
can admit the existing isolated unknown-potion workflow, but cannot enter until
actual invisibility and its remaining duration are observed. It travels only
observed cells, toward an observation opportunity, and can retarget a newly
observed chest if retrieval plus return still fits. Surveying alone never earns
collection or room-clear credit.

An additional staging issue was exterior puddles: input 1511's ordinary banks
807, 759 and 712 were rejected solely by the old blanket no-nearby-water pool
test rule. Recognized profiles can use ordinary exterior banks near unrelated
water, still requiring nonflammable visible surroundings, safe exits, isolation
and complete exclusion of the fish habitat and shore. This is not permission
to drink at 1511's actual 31/35 HP; near-full test health remains mandatory.

### Floor 4 gas-room sweep

The potion at input 1800 is **purity**, with an observed purification barrier,
not poison resistance inferred from a potion's appearance.

The controller plans the chest at 729 as its one reward and leaves the skeletal
remains at 801. At input 1807, the first chest is opened remotely; input 1808
shows gold x70; input 1809 reaches/picks up that gold. The barrier then has
11 turns remaining and the existing return path consumes most of that budget.
The journey turns back rather than planning a complete room sweep.

`protected_rewards.py` now supplies gas-specific multi-reward plans when at
least two admissible observed heaps share an enclosure, or when a recognized
toxic-vent/statue room initially exposes only one heap. A small subset-DP tour
maximizes heaps collected, then minimizes timed actions. Known-purity staging
prefers banks funding more rewards, then lower protected action cost, rather
than simply drinking wherever the hero currently stands.

Every execution step recomputes a separate return route to the owned bank and
uses the actual remaining barrier, movement impairment and per-heap interaction
budget, retaining a three-turn margin. Opening, moving onto and picking up a
heap are separate costs. New rewards can join the tour only when affordable.
Enclosures, statues, active traps, other effects, occupied cells and suspicious
containers remain physical constraints. Toxic-vent/statue recognition may admit
the gas-room skeletal heap only with the existing health, magic-charge and
non-hungry preparedness requirements.

Accepted pickup receipts are copied before the ordinary loot ledger clears
them. Missing heaps without receipts are unresolved; a chest opening is not a
pickup. Each returned, fully retrieved heap may earn individual reward credit,
but neither a partial tour nor unseen generated positions earn room-clear
credit. Short protection or interruptions trigger return, not additional loot.

## Validation

`tools/test_run188_room_feedback.py` covers local search precedence and scope,
key accumulation/reset, bounded Ghost continuation, stack sale receipts, narrow
flame-bank admission/vetoes, and the water-alcove retreat requirement.
These are reduced/synthetic selector contracts, not live success claims.
`tools/test_protected_reward_tours.py` adds synthetic multi-heap open/pickup/
return sequences, duration/obstruction failure gates, missing-receipt cases,
chest-independent recognition, aquarium rejection and protected survey tests.
These changes have not been deployed or verified by a new live run.
