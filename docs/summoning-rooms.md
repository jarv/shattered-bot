# Summoning-room preparation

The pinned game's `SecretSummoningRoom.paint` fills its 3–6 by 3–6 interior
with hidden summoning traps, places skeletal remains near the center, and uses
a hidden entrance. A Trap Mechanism can reveal some plates; without it there
need not be any visible plate. Other room generators also place bones, so bones
alone are not a unique room identity.

Run 81 decision 466 publicly shows a plain 3-by-4 chamber, central remains at
605, and doorway 558, with no trap fields. The new recognizer treats a small
plain rectangular chamber with central bones and one observed entrance as
suspect. It permits one unseen perimeter square for this *hypothesis*, not for
activation geometry. It searches from the doorway, bounded by accepted search
receipts, and blocks interior entry. Exhausted searching is not clearance.

A revealed summoning field is also blocked for ordinary collection/navigation.
Intentional activation requires:

- Quiet, near-full-health conditions and identified, usable equipped gear.
- Conservative initial admission limited to sewer floors without champion
  spawns or reduced-armor challenge rules; average armor blocking at least 3
  and effective weapon score at least 8. These are heuristics, not survival
  guarantees. Unknown upgrades and mere possession of AoE do not qualify.
- A fully observed enclosing boundary and one doorway, an exterior stand
  separated from every interior square, and an admitted retreat square.
- A visible active plate, clear throw trajectory, no reward on the target,
  and an ordinary reusable/eligible payload.

The hero stands outside the doorway rather than inside it: three room squares
can attack a hero in the doorway itself. `SummoningTrap.activate` can recursively
trigger neighboring hidden traps as monsters spawn, so the whole interior is
treated as a possible crowd, not just the selected plate.

After a throw the room stays quarantined until the interior is visibly inactive
and no observed/recent threats remain. Payload recovery uses the existing
disarm-and-retrieval contract. No throw proposal grants room completion.

Gas/seed preplacement remains optional and is not automated here. Gas can spread
through the open doorway; possession of a gas potion is not proof of a safe
prethrow or crowd-control outcome.

Tests cover the reduced run-81 observation, accepted search accounting, negative
room signatures, staging/throwing/quarantine, weak or unknown equipment, and
invalid boundaries or retreat paths. Synthetic post-trigger observations are
not gameplay replays or survival results.
