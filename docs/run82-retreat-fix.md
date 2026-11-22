# Run 82: false doorway escape preference

Run 000082 played `04a770b`, before the prerequisite and stash/summoning changes.
It died on depth 6 after 2,451 inputs. The accepted final transition explicitly
says “Skeleton killed you...”.

At decision 2442 the hero had 9/55 HP, no staff charges, and a skeleton at 1425.
The selected retreat from 1462 to 1461 began an approach to door 1383. Subsequent
retreats reached that door, whose only usable onward tile was 1345; the next
tile, 1346, held a known active shocking trap. The bot then threw two clubs and
traded a final melee attack instead of continuing a retreat.

`MagePolicy.retreat_preferences` rewarded a nearby door if any cardinal neighbor
beyond it was walkable **or unknown**. That one-square check certified neither
continued travel nor a holding position. Its bonus ranked above ordinary escape
distance and available-space scoring.

The repair retains the cardinal-exit requirement and adds the existing bounded
`onward_runway` check: two connected observed onward steps, admitted terrain,
no loot/plant/effects/warnings, and the existing threat margin. The whole
approach route is excluded so doubling back toward the pursuer cannot count.
Unknown terrain no longer earns a doorway preference. Telegraph and rinse
emergencies keep their existing separate admission.

On the original saved D2442 observation, current full selection chooses 1499,
into the open room. A reduced public-map fixture reproduces the old choice 1461
and the new choice 1499. Another regression proves unknown space used to earn a
false bonus. Both fail with the original method. A four-step synthetic pursuit
sequence verifies continued admitted retreat, and tests preserve real-door
preference and emergency evasion.

This fixes the evidenced navigation defect, not every preceding resource loss.
The run was already starving and had lost food to a thief. No replayed survival,
hidden potion identity, or post-death equipment knowledge is used as evidence.
