# Sad Ghost timing and Great Crab tactics

## Explore before starting

Starting the Sad Ghost dialogue can spawn its quest enemy. Before approaching or
speaking to start a quest, finish the observed floor's exploration:

- No reachable fog frontier or mapped-but-unobserved floor remains.
- No unopened ordinary door or unresolved required lock remains.
- No known ordinary floor remains unreachable behind an unresolved obstacle.

An exhausted navigation attempt is not evidence that a frontier was explored.
These checks do not claim that hidden secrets or deferred hazardous rooms are
clear. Existing health, charge, threat, and hunger safeguards still apply.
Quest-specific recovery waits also wait until exploration is complete, rather
than spending turns preparing to spawn a foe in a partly unknown map.

Returning for a completed quest's reward, collecting a dropped reward, or asking
for public completion evidence is not starting a new quest and is not held up by
new exploration work.

## Great Crab: plan a doorway with a way out

An awake crab that sees the hero blocks direct attacks, including wand damage.
Do not treat a charged staff or standing next to a door as a solution.

The dedicated controller selects an observed ordinary doorway with a hiding
square on the other side of its sight line. That hiding square must retain a
route to **a different ordinary door**, with two clear onward cells beyond that
second exit. The route excludes the ambush door: retreat cannot depend on
passing back through the crab. Traps, plants, damaging effects, unknown terrain,
loot piles, occupied cells, and rendered warnings do not count as clean escape
space.

This rejects the one-entrance special-room pocket used in run 9. Shared navigation
also checks escape space while the crab is visible or recently remembered, so
an ordinary fallback retreat cannot immediately undo the pocket-room veto.

After reaching the ambush door, step off it to break sight. A surprise attempt
requires an observed accepted departure plus a closed door or immediate fresh
crab entry. When the crab newly enters that threshold, make **one** doorway
surprise strike. The same open door/entry cannot authorize repeated attacks.
Sleeping or hero invisibility remain valid public surprise alternatives.

Recheck the doorway and second exit on each observation. Abandon a lure if
another active enemy appears, the escape route changes, health falls below half,
more than 20% of maximum health is lost during that setup, or its input/wait
budget expires. A setup allows at most 24 inputs and 8 waits; each door has a
bounded attempt count. No missing crab is attacked or treated as a kill.

Without an admitted doorway, use available invisibility or an observed
escape-backed reposition. Do not issue blocked direct attacks or deliberately
enter a confined dead end. Public quest-completion dialogue releases the lure
and its movement restrictions so reward collection can proceed.

The geometry and crossing receipts qualify a tactical attempt, not a guarantee
of enemy movement, surprise damage, survival, or quest completion.
