# Recognized special rooms and current handling

Recognition uses observed actors, terrain, effects, dialogue and loot—not hidden
room IDs. Recognition does **not** mean that every layout has a working solution
or that the reward has been collected.

## Shared potion rule

For an unfinished recognized potion puzzle, reserve its last required dose from
routine combat and inventory disposal. Explicit room preparation can use it;
existing emergency survival actions can still override the reservation.

Track actual same-floor ground pickups, public identification and **accepted**
consumption. If that supply is used for another purpose and no known carried or
ground replacement remains, stop demanding the impossible room, log its reward
as uncollected, and choose an observed safe descent route. Do not keep waiting for
the floor-generation guarantee to produce another bottle.

This applies to frost, flame, invisibility, levitation, purity and haste puzzles,
plus supported distant-well supplies. Shared levitation demands and alternative
drop protections are tracked without inventing an identity for unknown bottles.
An unambiguous observed protective effect can establish a singleton drink's
effect; burning/chill alone are not used to guess a consumed potion's identity.

A proposal, drop, cancelled targeting dialog, missing inventory entry by itself,
or potion carried from another floor is not a receipt that this floor's supply
was consumed elsewhere. Intended room use does not waive a failed retrieval.
Finding another known dose restores the room's priority.

Only observed rewards behind the matching exhausted barrier are deferred.
Other hazards, locks, mandatory progression pickups, active stash retrieval and
quest rewards keep their checks. Deferred rooms remain hazardous and uncollected;
leaving them never earns floor-clear credit.

## Potion puzzles

| Recognized room / landmark | Required supply | Current handling and limits |
| --- | --- | --- |
| Piranha pool and chest | Invisibility | Persistent chest/habitat, guarded dry/water/doorway approaches, protected round trip and pickup receipts. Known-potion staging is implemented. Unknown-supply staging is not reliable for every layout; run 24 still demonstrates a separate unresolved preparation/scouting case. |
| Magical fire barrier | Frost | Known frost throw or guarded unknown-potion testing; verify actual fire removal before crossing. Hunger/health/staging can still prevent preparation, as in run 22. |
| Barricaded storage / wooden barrier | Liquid flame | Guarded known throw or controlled unknown test, water escape, then observe fire expiry before entering. It is not permission to walk into active fire. |
| Trap field / chasm reward | Levitation | Observed reward round trip, explicit buff/duration and return budget. Mapping can first reveal an incomplete connecting passage. Arbitrary isolated traps are not proof of a generated potion room. |
| Toxic-gas reward room | Purity | Stage outside the gas, verify purification barrier and budget the return. Unknown testing keeps its health, safe-bank and inventory-protection checks. |
| Red sentry room | Haste | Reconstruct the observed enclosure and crossing delay; stage off exposed carpet, then verify haste and the round-trip budget. Incomplete geometry or impairment can prevent entry. |
| Distant-well ledge / pit-room drop | Feather fall, or cleansing plus a survivable fall budget | Optional guarded drop, landing and return workflow. Levitation can be an alchemy ingredient for feather fall; raw levitation is **not** the falling protection. This is not a claim that this optional room generates every required exotic supply on the same floor. |

## Other recognized room and reward families

| Recognized family | Potion requirement | Current handling |
| --- | --- | --- |
| Ordinary locked rooms / locked reward chests | None | Match observed locks to held iron, golden, worn or skeleton keys; retain pickup obligations. |
| Crystal doors / crystal chests | None | Crystal-key-aware choices, inspect visible reward information, record mutually exclusive alternatives. |
| Crypts, tombs, skeletal remains | None mandatory | Conservative health, hunger, magic-charge and approach checks before opening. |
| Suspicious chests / mimics, including crystal mimics | None mandatory | Guarded ranged provocation, escape/interception planning and durable reward collection; not every encounter is certified safe. |
| Maze reward areas | None mandatory | Observed maze-route/goal commitment and actual collection evidence. |
| Animated / armored statue rooms | None | Recognized; normally avoid waking optional high-risk guardians. |
| Wandmaker rot garden | None mandatory | Enter for the active rotberry quest, avoid lasher melee/gas and preserve the seed from fire. |
| Wandmaker ritual / fire elemental | None mandatory | Candle placement, summon observation and elemental combat. Frost can help but may not steal another room's reserved last dose. |
| Wandmaker corpse-dust crypt | None mandatory | Quest-item handling, wraith pressure and return/reward verification. |
| Ordinary gardens / blandfruit | None | Garden recognition, plant/food preparation and inventory safeguards. |
| Healing / awareness / cleansing wells | None | Inspect public effects before use; distinguish inventory awareness from full-floor mapping. |
| Alchemy labs | Recipe-specific, not a fixed room potion | Check actual recipe energy and ingredients before crafting; optional recipes retain supplies. |
| Shops | None | Observed stock, prices, affordability and verified purchases/sales. |
| Hidden rooms / secret passages | None mandatory | Bounded observed-wall searches and known mapping resources, never generated coordinates. |

## Runs 23 and 24

Run 23 identified invisibility, failed doorway staging, then spent the last dose
on a snake at full health. Its next wand zap immediately cancelled the full
20-turn invisibility effect. The accepted run-23 patch fixed doorway staging;
the shared rule above additionally prevents that routine combat expenditure and
provides honest descent after confirmed off-purpose use.

Run 24 did not drink invisibility. Its proposed approach-arrival bookkeeping
patch was rejected by trusted validation because the new regression did not
reproduce an assertion failure on the played source. No fix was promoted.
Failure to find a safe unknown-potion test is **not** evidence that a supply was
spent, so it does not trigger the new exception.
