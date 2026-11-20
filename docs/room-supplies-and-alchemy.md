# Potion-room supplies and alchemy energy

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

Record chest collection only from an accepted pickup receipt. Do not descend
while that chest remains pending; ordinary unfinished-loot descent permission
does not waive this specific requirement.

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
