# Potion-room supplies and alchemy energy

## Strength identification before descent

Until strength is publicly identified, an otherwise admitted descent first
triggers one-at-a-time drink tests of carried unidentified potions. This is a
departure phase, not an exploration activity: it does not require revisiting
every optional tile that the floor policy has already elected to leave.
Prefer a nearby safe water tile; a dry alternative requires an adjacent observed
water escape. Tests retain health, threat, impairment, Pharmacophobia, safe-route
and potion-inventory protection checks. Unsafe tests are explicitly deferred,
not forced and not represented as successful identification.

Do not spend unknown supplies on this phase while a recognized potion-room
requirement or an unrelated retrieval/journey remains. Safe room-specific tests
retain their own purpose and protection checks. Ordinary generic strength drink
tests no longer run during Mage exploration. Safe scroll identification remains
available earlier; when the preferred potion is inside a bag, open the bag
instead of spending Identify on a lower-ranked visible backpack item.

Accepted inventory loss confirms each test. An observed standard strength gain
from that drink, or a publicly named strength potion, ends the search across
later floors too. Color, stack counts and floor-placement clues never establish
identity. Recover from actual test effects before another experiment, and
retrieve any stashed potions even when the test finds strength.

## Same-floor room supplies

The pinned game's potion-gated special rooms place a matching potion on the
same floor:

| Observed room hypothesis | Required potion | Generator |
| --- | --- | --- |
| Piranha pool/chest | Invisibility | `PoolRoom` |
| Magical fire barrier | Frost | `MagicalFireRoom` |
| Barricaded storage | Liquid flame | `StorageRoom` |
| Levitation/trap room | Levitation | `TrapsRoom` |
| Toxic-gas room | Purity | `ToxicGasRoom` |
| Red sentry room | Haste | `SentryRoom` |

Use this as a **search and identification prior**, never a potion-color identity.
Prefer observed current-floor potion candidates; use identification/intuition
when available, otherwise controlled drinking tests. Each distinct unknown
potion type is tested at most once per floor, up to 12 types rather than the old
two-test limit. Keep the existing near-full-health, threat, status, safe staging,
and potion-stashing checks. The generation rule does not mean that a potion
already consumed or destroyed is still available, and does not apply to every
arbitrary trap or damaging effect.

Plan the protected reward round trip before testing. Open observed ordinary
entrances **before** spending the potion, reobserve, and verify the resulting
actual buff before crossing hazards. A route hypothesis is not protection.
Known purity also gets explicit staging outside gas.

## Piranha chest: persistent obligation

Remember the observed water habitat and chest even after moving fish leave
view. Do not treat a missing actor or chest as proof of a kill or collection.
Use carried invisibility to return to a safe dry approach from elsewhere on the
floor; reserve its last carried copy from ordinary inventory disposal.

The chest takes precedence over nearer incidental gold for the invisibility
trip. A closed pool entrance is opened before drinking. The return controller
can reopen that known entrance if it closes behind the hero, while retaining
its protection-time checks. Current fish occupancy, actual buff duration, and
the return route are rechecked on each step.

Record chest collection only from an accepted pickup receipt. Reserve supplies
for this objective. If an accepted off-purpose action consumes the floor's
collected supply and no known replacement remains, defer the affected room and
descend without collection or floor-clear credit. Ordinary unfinished-loot
permission alone does not waive a still-supplied pool objective. See the
[shared potion rule and complete room status](special-room-status.md).

### Unknown supplies: the bandolier is protection, not a potion

Run 16 never identified its invisibility supply before the pool stall. Its
inventory did include a potion bandolier, but the old stash helper classified
the bag itself as a potion and still required remote drops. The largest unknown
stack also failed the single-dose rule, even though a protected stack does not
need splitting.

Track the bag's acquisition through public inventory observations. When it has
not possibly overflowed since acquisition, its cold protection replaces remote
potion stashing, including for stacked candidates. Count all 19 bag slots,
including waterskin and liquid metal, not individual doses. Keep possible
overflow uncertain across consumption and floor changes. A standalone snapshot
of an already-owned bag is not a container receipt. Without confirmed bag
protection, retain ordinary stashing and single-dose drinking requirements;
safe identification of stacks is still allowed.

Unknown pool testing still requires a visible dry bank, near-full health,
no threats and a planned protected return. Choose the bank using the actual
round-trip budget, not the old five-cell distance to the remembered chest:
run 16's admitted dry approach was seven cells from its reward. Open observed
entrances before drinking, verify the actual buff, and retain pickup receipts.

### Unreachable strength rewards: discover the connecting passage

Run 18's awareness well revealed a strength potion without revealing its entire
connecting route. It had a known magic-mapping scroll, but mapping required two
earlier searches while the mandatory-pickup path never initiated those searches.

If an observed strength potion or upgrade scroll has no admitted ordinary
pickup route, first offer existing protected-room preparation. If that declines,
allow a known mapping scroll without the optional-search prerequisite. Retain
threat/status checks, the per-floor attempt limit and actual mapping receipts.
Do not spend this exception on optional food, repeat it on a fully mapped floor,
guess a hidden entrance, cross a trap unprotected or waive the pickup obligation.
Reassess routes from the new observation; mapping is discovery, not collection.

## Minimum energy before crafting

There is no universal crafting minimum: costs depend on the recipe. The magical
catalyst costs **6** energy; single-meat cooking costs **1**; some seed/runestone
recipes are free. Optional paid recipes retain the existing 2-energy reserve,
while urgent starvation cooking can use the exact recipe minimum.

The toolkit uses global energy plus its displayed available charge; a pot uses
global energy. A toolkit warm-up **percentage is not energy**, and an unequipped
toolkit cannot fund a pot recipe. The toolkit's separate 6-energy `ENERGIZE`
upgrade is not a universal brewing requirement.

When energy is already known to be insufficient, do not open alchemy or select
ingredients. If energy is not observable yet, inspect the alchemy energy label
once and leave immediately if insufficient, **before loading any ingredient**.
Recheck the live label on entry even when the cached value was sufficient.
Missing/unparseable energy never authorizes a paid recipe.

Continue ordinary play rather than repeatedly entering menus or idling for
energy. A toolkit charge/level change or an observed possible energy pickup
allows reevaluation; a pickup invalidates the cache rather than inventing the
new amount. Free recipes and known free fallbacks do not require paid energy.
Do not automatically energize valuable inventory.
