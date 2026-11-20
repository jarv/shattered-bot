# Pickup, keys, and trinket policy

## Full inventory

Food is a priority pickup alongside strength potions, upgrade scrolls, and
observed matching keys. Combat, status effects, dangerous routes, and active
resource plans still take precedence: priority does not authorize unsafe movement.

Only a **fresh public can't-carry receipt** permits disposal. Inventory length
alone is not evidence that a bag is full. Drop the lowest-value eligible item,
and only for a strictly higher-priority pickup:

1. Strength potions, upgrade scrolls, food (including raw food), ankhs.
2. Wands, rings, artifacts, trinkets, scrolls, potions, arcane styluses,
   runestones, spells, and unknown items/equipment whose power is not established.
3. Thrown weapons.
4. Seeds, catalysts, arcane resin, liquid metal.
5. Bombs and honeypots.
6. Duplicate-looking spare weapons/armor: retain another equally described copy,
   never equate visibly different upgrades.
7. Identified weapons/armor weaker than the equipped item, using rendered
   damage/blocking, upgrades and strength requirements. Both must be usable at
   current strength; unknown or stronger future gear is not labeled inferior.

Within a tier, discard **known cursed** before non-cursed/curse-unknown items.
Do not guess curses or identities. Cursed equipment does not automatically rank
below every uncursed item in other tiers.

Never automatically drop equipped gear, the Mage staff, keys, quest items, bags,
waterskin, torches, or essential class/quest utilities. Also retain the current
upgrade target, selected quest reward, and reserved ghost equipment. Dropping
only occurs on a clean safe bank, never on the desired pickup. Whole-stack drops
require matching inventory removal and ground quantity before being credited.
Failed or ambiguous drops are not retried automatically.

Bag rules matter: seeds/runestones in a velvet pouch do not free backpack space
for food. Use the pinned game's specialist-bag rules to select compatible
discards conservatively; the flattened inventory does not expose actual parent
bags or prove available slots. A pickup still needs its own receipt after cleanup.
Intentionally discarded loot is excluded from recollection until that observed
ground item changes.

## Locked and crystal rooms

The silver-looking room locks are **crystal doors/chests**, not iron-key locks.
Ordinary locked doors require iron keys; locked chests require golden keys.
All keys must match the current floor. Missing matching keys remain explicit
obligations, and observed matching-key pickups get collection priority.

Finish a reachable iron-key door before descending. For crystal branches, use
remembered public geometry and observed rewards, not only currently visible
doors. An ordinary chest is a legitimate observed reward even though its contents
are unknown; it must not be scored as worthless. Its contents are never inferred.
Crystal chests use their rendered wand/ring/artifact hints, not hidden contents.

Only local paired choices may be treated as alternatives: two crystal chests in
one room, or two doors sharing an observed vestibule with a chest branch.
Do not group unrelated locks elsewhere on the floor or treat multi-door
key-budgeted paths as a two-room choice. An alternative is resolved only after
both a visible opened target and consumption of the last held crystal key are
observed. Additional found crystal keys reopen alternatives. Merely selecting a
door/chest does not count as opening it or collecting its reward.

## Catalyst and trinkets

An observed **magical catalyst** can make a trinket at an observed nearby alchemy
station or usable toolkit. The pinned recipe costs **6 energy**, with the existing
2-energy reserve retained for optional crafting. Urgent cooking/recovery and
room preparation remain ahead of this recipe. No supplies are automatically
energized; trinkets are not automatically upgraded.

This is a **Mage bot safety ranking**, not a universal player tier list:

| Rank | Trinket | Reason/trade-off |
| --- | --- | --- |
| 1 | Petrified seed | More grass drops, with runestones replacing some seeds. |
| 2 | Mossy clump | More grass/water floors; useful resources and terrain. |
| 3 | Cracked spyglass | Extra hidden items; benefit depends on finding them. |
| 4 | Ferret tuft | Evasion helps the hero; enemies also evade more, favoring wand use. |
| 5 | Exotic crystals | More exotic consumables; not every exotic is supported equally. |
| 6 | Parchment scrap | More enchantments/glyphs, but also more equipment curses. |
| 7 | Thirteen leaf clover | More extreme damage rolls; increased variance. |
| 8 | Wondrous resin | Wand benefit, but extra cursed-zap effects reduce predictability. |
| 9 | Salt cube | Longer satiety at the cost of slower natural healing. |
| 10 | Dimensional sundial | Real-time day/night spawn trade-off; do not assume favorable time. |
| 11 | Vial of blood | More total healing, but delays emergency recovery. |
| 12 | Rat skull | More exotic enemies, with extra combat risk. |
| 13 | Eye of newt | Nearby mind vision at the cost of normal vision. |
| 14 | Trap mechanism | Reveals more traps but adds trap/chasm-themed floors. |
| 15 | Chaotic censer | Random harmful gases complicate safe movement. |
| 16 | Shard of oblivion | Equipment identification needs manual handling. |
| 17 | Mimic tooth | More dangerous, harder-to-detect mimics. |

Choose only among the **actually offered** named trinkets, then inspect and
confirm the matching item. Do not select a hidden random reward. Craft previews
and button clicks are not acquisition: report catalyst consumption and an
inventory increase of the chosen trinket only when observed.

These rules have selector/regression tests; they do not prove that a future game
will successfully collect every reward or survive changed trinket effects.
