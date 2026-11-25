# Shattered Bot

Mage automation for the [Shattered Pixel Dungeon player API](https://github.com/jarv/shattered-pixel-dungeon/blob/master/docs/player-api.md).
This repository contains the current bot, API client and regression tests. The
game itself lives in `jarv/shattered-pixel-dungeon`; deployment, recording,
OpenCode investigation and publication are managed in `jarv/config-mgmt`.

## Run locally

### Prerequisites

- Git, Python 3.10 or newer, and a **Java 21 JDK**.
- A working graphical desktop with OpenGL support. The bot drives the actual
  desktop game, not a headless simulator.
- Internet access for Gradle's first build. The game includes its Gradle wrapper;
  no separate Gradle installation is needed. Python uses only its standard library.

Use the [API-enabled game fork](https://github.com/jarv/shattered-pixel-dungeon),
not the upstream game or a store installation.

### Clone and build

Clone both repositories into the same parent directory:

```sh
git clone https://github.com/jarv/shattered-pixel-dungeon.git
git clone https://github.com/jarv/shattered-bot.git

cd shattered-pixel-dungeon
java -version  # should show Java 21
./gradlew :desktop:classes --console=plain
cd ../shattered-bot
```

If Java 21 is not your default, set `JAVA_HOME` to its JDK directory before
building, and use `--java-home /path/to/jdk-21` when launching below.
On Windows, use `gradlew.bat` for the build; the automatic launcher uses the
Unix `gradlew` script, so Windows users should use the manual-launch option.

### Launch the game and bot together

From the `shattered-bot` directory:

```sh
python3 -m tools.survival_bot --launch --game-dir ../shattered-pixel-dungeon --watch
```

This builds/starts the fork, creates an isolated temporary save/settings
profile and API token, and plays Mage with normal rules and a random seed.
`--watch` pauses 0.3 seconds between decisions so you can follow the game.
No AI provider, API key, or server deployment is needed to play locally.

The launcher prints the profile directory; its `game.log` contains game/build
output. It waits up to two minutes for startup, so prebuilding as above helps
avoid a timeout during the first dependency download.
The game normally closes when the bot stops; add `--keep-open` to inspect it.
To keep saves/settings in a chosen directory, add `--profile /absolute/path/to/profile`.
Use a dedicated bot profile, not your personal game saves.

To save observations and decisions, add `--log decisions.jsonl` with a new
filename; existing logs are never overwritten. The bot runs until death or
planner exhaustion; unsupported UI/API faults pause it.

### Connect to a manually launched game

For separate game/bot terminals, use the same token in both. These examples use
a POSIX shell. In the first terminal, from the game fork:

```sh
cd shattered-pixel-dungeon
export SPD_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export SPD_API_PORT=8765
export SPD_DATA_DIR="$(mktemp -d)"
# Copy this token into the second terminal; keep it private.
printf '%s\n' "$SPD_API_TOKEN"
./gradlew :desktop:debug --console=plain
```

In the second terminal, from the bot checkout:

```sh
cd shattered-bot
export SPD_API_TOKEN='paste-the-token-from-the-first-terminal'
python3 -m tools.survival_bot --url http://127.0.0.1:8765 --watch
```

The game API listens only on localhost. Without `SPD_API_PORT`, it does not
start; without `SPD_DATA_DIR`, the game uses your normal saves/settings.
Do not commit tokens or game profiles.

The bot uses `GET /state` to observe and `POST /action` for ordinary player
inputs. The client requires API version 1 (`api_version: 1`); update the fork
and client together. Structured failures expose `PlayerAPIError.code` and
`action_may_have_executed`. Requests are never automatically retried, and
failures invalidate cached observation handles.

### Tests and options

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
python3 -m tools.survival_bot --help
```

For another local game instance, choose a free API port with `--port 8766`
when using `--launch`, or set `SPD_API_PORT` and the matching `--url` for a
manual launch. Explicit challenge modes and other options are listed in `--help`.

## Bot behavior

### Select an implementation

Both implementations share the same combat, item handling, safety and API code.
Select a named objective/navigation profile:

```sh
python3 -m tools.survival_bot --bot-implementation legacy-bot --launch --watch
python3 -m tools.survival_bot --bot-implementation simple-bot --launch --watch
```

`legacy-bot` is the default and retains the existing policy. `simple-bot` keeps
combat/enemy strategies, alchemy, seeds/runes/scrolls/artifacts, shops, wells,
equipment, talents, ordinary pickups and safe strength-potion discovery. It
does not initiate quests, solve special rooms, reserve puzzle supplies, hunt
secret rooms, or require full map coverage.

Simple-bot requests descent after gaining one character level since first
entering the floor, or exhausting reachable ordinary doors and observation
frontiers. It first collects all known safely reachable ordinary loot (including
loot out of current sight), consumes/identifies strength as required, and
finishes owned-item retrieval. Inaccessible/unsafe/special loot is explicitly
reported as excluded, not claimed collected. Level-up exits stop optional
exploration; unknown stairs still require ordinary navigation to find them.
Boss locks and immediate threats cannot be bypassed.

Incidental dead-end searches remain: no search expeditions, at most two accepted
searches per location and sixteen per floor/branch, and no optional searches
after leveling when stairs are known. Search proposals/rejections spend no
accepted-input budget. Neither profile claims a full floor clear merely from
descending. Combat engine selection (`--engine`) is separate from bot profile.

The bot uses public observations and ordinary game actions only. It does not
read save files, inspect hidden game state or infer unidentified potion effects.
Collection, crafting and movement require observed receipts rather than assumed
success. API, runner/startup rules and existing tests are protected from automatic
review patches.

See [pickup, key-room, and trinket policy](docs/pickup-and-trinket-policy.md)
for inventory retention tiers and the Mage-specific catalyst/trinket ranking.
The [Sad Ghost policy](docs/ghost-quest-policy.md) covers exploration-first
quest timing and escape-backed Great Crab doorway ambushes.
See [DM-100 door escape](docs/dm100-door-escape.md) and
[room supplies and alchemy energy](docs/room-supplies-and-alchemy.md) for
lightning response, potion testing/retrieval, and minimum-energy crafting gates.
The [special-room status list](docs/special-room-status.md) lists recognized
room families, required supplies, known limits, and the shared reserve-or-defer rule.

If normal planning and admitted rescue actions are exhausted, survival runs end
as **stuck planner (bot unable to proceed)** instead of spending fallback turns
until starvation. This is a terminal bot failure (`stuck-planner`), not a claim
that the hero died. The final observation, original blocker and policy report
are retained for high-priority diagnosis and regression-backed repair. Ordinary
bounded healing, tactical approach waits and safe rescue actions remain available.

## Fresh run history

The initial commit intentionally contains **no historical runs, recommendations,
recordings or trial artifacts**. The server starts at `runs/000001/`. Future run
records identify both the exact bot commit and the independently pinned game
commit. Only bot policy changes and new regression tests are eligible for
automatic repair; the game/API repository is read-only to the reviewer.

## License

The bot is licensed under the [MIT License](LICENSE).
The separate [Shattered Pixel Dungeon game fork](https://github.com/jarv/shattered-pixel-dungeon)
remains GPLv3; this license change applies only to the bot repository.
