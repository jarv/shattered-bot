# Shattered Bot

Mage automation for the [Shattered Pixel Dungeon player API](https://github.com/jarv/shattered-pixel-dungeon/blob/master/docs/player-api.md).
This repository contains the current bot, API client and regression tests. The
game itself lives in `jarv/shattered-pixel-dungeon`; deployment, recording,
OpenCode investigation and publication are managed in `jarv/config-mgmt`.

## Run locally

Clone the game alongside this repository and use Java 21 for its Gradle build.
Python needs only its standard library.
The client requires player API version 1 (`api_version: 1`); update the game and
client together. Structured failures expose `PlayerAPIError.code` and
`action_may_have_executed`. Requests are never automatically retried, and failures
invalidate cached observation handles.

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
python3 -m tools.survival_bot --launch --game-dir ../shattered-pixel-dungeon --watch
```

Alternatively connect to an already running game API with `--url`. API
authentication uses `SPD_API_TOKEN`; do not commit tokens or game profiles.
The default policy is Mage with regular rules. Explicit challenge modes and
other launch options remain available via `--help`.

The bot uses public observations and ordinary game actions only. It does not
read save files, inspect hidden game state or infer unidentified potion effects.
Collection, crafting and movement require observed receipts rather than assumed
success. API, runner/startup rules and existing tests are protected from automatic
review patches.

## Fresh run history

The initial commit intentionally contains **no historical runs, recommendations,
recordings or trial artifacts**. The server starts at `runs/000001/`. Future run
records identify both the exact bot commit and the independently pinned game
commit. Only bot policy changes and new regression tests are eligible for
automatic repair; the game/API repository is read-only to the reviewer.

Source inherited from the existing ShatteredAI bot is preserved under GPLv3;
see `LICENSE.txt`. Game/API development remains in the separate game fork.
