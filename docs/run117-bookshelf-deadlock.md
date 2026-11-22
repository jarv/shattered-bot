# Run 117: speculative shelf supply deadlock

The living, full-health hero stopped at depth 1 because shelves 894–897 created
a missing-liquid-flame prerequisite for mandatory strength discovery. Only
amber remained unidentified; crimson had been identified as haste. Cells
857–860 behind the shelves were unobserved, not confirmed walls.

Pinned game source `dc6687b3` distinguishes LibraryRoom (shelves, no scheduled
flame potion) from StorageRoom (barricade and scheduled flame). Shelf scenery is
therefore not sufficient evidence of a mandatory potion-supply room.

## Policy correction

Only the mandatory-discovery prerequisite list changes. Known liquid flame
remains reserved through the ordinary room-supply rules. Any observed barricade
anywhere on the floor preserves the missing-flame gate, even if the nearest-kind
classifier chooses a bookshelf instead. A known reward in a non-reachable,
observed non-wall component connected to shelves also preserves the gate.
That connectivity is conservative reservation evidence, never permission to
walk across hazards or locks.

With neither form of evidence, shelves are recorded as deferred, unfinished
exploration. Unknown shelf backs remain unknown. This deliberately prioritizes
mandatory strength discovery over saving every unknown color for a hypothetical
secret alcove. It can expend a color that later proves useful for optional
shelves; it does not claim those shelves were empty, cleared or collected.
Existing bank visibility, water escape, inventory protection, hunger, health,
accepted-consumption and bounded-transit checks remain in force.

## Evidence and limits

An observation-only scan of run 117, using `update` plus the existing
`remember_bank` admission on saved observations, finds witnessed banks with the
terminal potion inventory. Candidate terminal selection chooses cell 750 on
route 749 → 750 → 714 → 678 → 716 to reobserve a previously admitted bank.
Without those receipts it still explicitly exhausts rather than inventing a
safe bank. This scan is not a reconstruction of all runtime memory or a replay;
no post-change game trajectory was generated.

Regression fixtures cover wall-backed and unknown-backed shelves with and
without a protective bag, known rewards behind shelves, farther barricades,
known-flame reservation, low health and actual-consumption/strength receipts.
The original blanket-reservation behavior blocks all four optional-shelf
fixtures. A separate synthetic receipt sequence completes strength discovery
while leaving shelf exploration unfinished. No improved survival or successful
retrieval in the original game is claimed.
