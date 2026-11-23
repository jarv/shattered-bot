# ShatteredAI run 000187

Played commit: `7004129070e394f8d70fbdb17c3cd6b2b7b249de`

Outcome: stuck-planner

Java build: `f3c82c492ad64189c4afc2032e615a513bcf5625732e29ed64c0886632391d0b`

Outcome summary: stuck planner (bot unable to proceed)

## Improvements since the last run

- The bot can now use a stone of intuition while hungry to investigate a potion needed for a fire barrier, as well as one needed for a gas room. It still requires a safe, healthy position before trying the guess.

## Incoming learnings

Hunger restrictions on unknown potion drinking must not exclude a separately guarded intuition hypothesis for an observed fire barrier. Track each floor, room type and color independently; a failed golden guess says nothing about bistre. Require public identification, safe extinguishing and actual pickup evidence afterward.

## Analysis

The planner stopped with the hero alive at 14/40 HP. D1543–1544 (log lines 4473–4478) show a low-health withdrawal immediately returning through the door it had just left. Doorway preference rewarded that reversal over equally separated, already admitted onward ground. Later, escape-route protection rejected the key-collection route, while bounded recovery shuttled between two squares and exhausted (D1546–1550, lines 4485–4501). The iron key remained mandatory and uncollected, so fallback descent was declined. A focused next-run correction removes only the bonus for a doorway route that reverses an accepted escape edge. Original helper probes matched the recorded withdrawal selections; the isolated candidate chose onward ground instead. The new regression fails on original source and passes on the candidate; all 2,084 Python tests pass, with four skipped. This does not establish eventual key collection, escape, or prevention of all planner failures.

## Recommendations

- **000187-reverse-door-withdrawal — Remove the doorway preference bonus for reversing a recently accepted withdrawal edge.** (high, implemented): Patch passed isolated validation and was accepted.
  - Evidence: D1543–1544, log lines 4473–4478: accepted withdrawal reverses through the same door.; D1546–1549, log lines 4485–4498: key-route reversal veto and repeated recovery detours.; D1550, log lines 4500–4501: mandatory key prevents fallback descent; planner stops alive.
  - Disposition: implemented

## Lessons for the next run

Do not reward a just-left escape door as a new withdrawal destination. Keep route protection, remembered-threat checks and mandatory key collection intact; validate actual progress after any changed withdrawal rather than assuming a safe escape.

Update: **accepted**.
