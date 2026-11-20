#!/usr/bin/env python3
"""Experimental Mage controller: descend using only PlayerAPI observations/actions.

--watch reruns the policy live; it does not replay a nondeterministic run.
The policy and its compatibility exports remain usable without launching a game.
"""
import argparse
import json
import math
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error

try:
    from .player_api import PlayerAPI, PlayerAPIError
    from .policy_decision import Decision, Finished, Intent
    from .policy_geometry import distance, neighbors, line_clear
    from .survival_policy import SurvivalPolicy, NavigationLoopGuard, MenuLoopGuard, is_hostile, is_container, is_passive
    from .policy_runner import run
except ImportError:
    from player_api import PlayerAPI, PlayerAPIError
    from policy_decision import Decision, Finished, Intent
    from policy_geometry import distance, neighbors, line_clear
    from survival_policy import SurvivalPolicy, NavigationLoopGuard, MenuLoopGuard, is_hostile, is_container, is_passive
    from policy_runner import run


def launch_game(args, *, log_path=None):
    root = Path(getattr(args, "game_dir", None) or os.environ.get("SHATTERED_GAME_DIR")
                or Path(__file__).resolve().parents[2] / "shattered-pixel-dungeon").resolve()
    if not (root / "gradlew").is_file():
        raise ValueError("Game checkout not found; pass --game-dir pointing to the separate game repository")
    base = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else Path(tempfile.gettempdir())
    profile = Path(args.profile).resolve() if args.profile else Path(tempfile.mkdtemp(prefix="spd-survival-", dir=base))
    profile.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SPD_API_PORT=str(args.port), SPD_API_TOKEN=secrets.token_urlsafe(32), SPD_DATA_DIR=str(profile))
    env["SPD_API_HIDDEN"] = "1" if args.hidden else "0"
    if args.java_home:
        env["JAVA_HOME"] = args.java_home
    game_log=Path(log_path) if log_path else profile / (f"game-{time.time_ns()}.log" if args.profile else "game.log")
    log = game_log.open("x")
    process = subprocess.Popen([str(root / "gradlew"), ":desktop:debug", "--console=plain"],
                               cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    log.close()
    api = PlayerAPI(f"http://127.0.0.1:{args.port}", env["SPD_API_TOKEN"])
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Game exited during launch; see {game_log}")
            try:
                api.state()
                if getattr(args,'workspace',None) is not None:
                    try:
                        from .workspace_launch import place
                    except ImportError:
                        from workspace_launch import place
                    placement=place(args.port,profile,args.workspace)
                    print('Game workspace: '+json.dumps(placement),flush=True)
                print(f"Game profile: {profile}", flush=True)
                return api, process, profile
            except urllib.error.URLError:
                time.sleep(0.25)
            except PlayerAPIError as error:
                # A fresh server may not be listening yet. Only retry a failed
                # observation transport request, never a protocol error or input.
                if error.code != "TRANSPORT_ERROR" or error.action_may_have_executed:
                    raise
                time.sleep(0.25)
        raise RuntimeError(f"Game did not become ready; see {game_log}")
    except BaseException:
        stop_game(process)
        raise


def stop_game(process):
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def configured_policy(args,policy_factory=None):
    """Resolve explicit options before launch; no game/API side effects."""
    try:
        from .mage_policy import MagePolicy
        from .challenge_rules import configured_rules
    except ImportError:
        from mage_policy import MagePolicy
        from challenge_rules import configured_rules
    explicit=args.challenge_preset is not None or args.challenge or args.disable_challenge
    overrides=None
    if getattr(args,'unit_strategies',None):
        if policy_factory is not None and not explicit:
            raise ValueError('--unit-strategies requires the configured Mage policy, not a historical factory')
        try:
            overrides=json.loads(Path(args.unit_strategies).read_text())
        except (OSError,ValueError) as error:
            raise ValueError(f'Cannot read unit strategies: {error}') from error
    if args.without_on_a_diet and explicit:
        raise ValueError('--without-on-a-diet cannot be combined with challenge configuration options')
    if args.without_on_a_diet:
        rules=configured_rules('eight-without-on-diet')
    elif explicit or policy_factory is None:
        rules=configured_rules(args.challenge_preset or 'regular',args.challenge,args.disable_challenge)
    else:
        # An explicitly supplied historical factory is already an opt-in preset.
        if policy_factory is SurvivalPolicy:
            if args.seed:raise ValueError('--seed requires the configured Mage startup workflow')
            return policy_factory(goal=args.goal,engine=args.engine)
        return policy_factory(goal=args.goal,engine=args.engine,**({'seed':args.seed} if args.seed else {}))
    policy=MagePolicy(goal=args.goal,engine=args.engine,seed=args.seed,rules=rules,
                       unit_strategy_overrides=overrides,
                       stop_on_no_safe_action=getattr(args,'stop_on_no_safe_action',False),
                       stop_on_incomplete_loot=getattr(args,'stop_on_incomplete_loot',False))
    if args.goal=='survival' and (getattr(args,'stop_on_no_safe_action',False)
                                  or getattr(args,'stop_on_incomplete_loot',False)):
        raise ValueError('Survival runs continue until death; early-stop flags are only for checkpoint/evaluation goals')
    return policy


def main(policy_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--launch", action="store_true", help="Launch a graphical game in a separate profile")
    parser.add_argument("--game-dir", help="Separate game checkout for --launch (default: sibling shattered-pixel-dungeon)")
    parser.add_argument("--profile", help="Explicit save profile for --launch; default is a fresh temporary directory")
    parser.add_argument("--java-home", help="Gradle-compatible JDK directory (e.g. Java 21)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--watch", action="store_true", help="Pause 0.3 seconds between decisions")
    parser.add_argument("--hidden", action="store_true", help="Hide the launched window during evaluation (not headless)")
    parser.add_argument("--workspace", type=int, help="Verify this launched game window on a numbered Hyprland workspace before playing")
    parser.add_argument("--delay", type=float, help="Explicit seconds between decisions, including menu inputs")
    parser.add_argument("--keep-open", action="store_true", help="Leave a launched game open when the bot stops")
    parser.add_argument("--max-actions", type=int, default=3000,
                        help='Action budget for checkpoint/evaluation goals; ignored for survival')
    parser.add_argument("--engine", choices=("legacy", "planner"), default="legacy",
                        help="Use legacy tactics or experimental utility combat under the same priority tree")
    parser.add_argument("--goal", choices=("survival", "two-floors", "floor-four", "goo"), default="survival",
                        help="Stop at a checkpoint/Goo, or keep playing until death (survival); unsupported UI/API faults pause")
    parser.add_argument("--log", help="New observation/decision JSONL file (never overwrites an existing log)")
    parser.add_argument("--seed", help="Optional custom seed, e.g. ABC-DEF-GHI; entered/verified through ordinary UI")
    try:
        from .challenge_rules import CHALLENGE_OPTIONS,PRESETS
    except ImportError:
        from challenge_rules import CHALLENGE_OPTIONS,PRESETS
    parser.add_argument('--challenge-preset',choices=PRESETS,
                        help='Explicit preset; default is regular (all challenge rules off)')
    parser.add_argument('--challenge','--enable-challenge',action='append',default=[],choices=CHALLENGE_OPTIONS,
                        help='Enable one challenge and its rules; repeat to combine')
    parser.add_argument('--disable-challenge',action='append',default=[],choices=CHALLENGE_OPTIONS,
                        help='Disable a challenge from an explicit preset; repeat as needed')
    parser.add_argument('--without-on-a-diet',action='store_true',
                        help='Verified challenge policy: disable On a Diet while keeping the other eight enabled')
    parser.add_argument('--stop-on-no-safe-action',action='store_true',
                        help='Opt into early safety stops instead of logged best-effort continuation')
    parser.add_argument('--stop-on-incomplete-loot',action='store_true',
                        help='Opt into blocking descent with outstanding collectible loot')
    parser.add_argument('--unit-strategies',metavar='JSON',
                        help='JSON object mapping ordinary public enemy names to validated strategy groups')
    args = parser.parse_args()
    try:
        policy = configured_policy(args,policy_factory)
    except ValueError as error:
        parser.error(str(error))
    if args.max_actions < 1 or (args.delay is not None and (args.delay < 0 or not math.isfinite(args.delay))):
        parser.error("max-actions must be positive and delay nonnegative")
    if args.hidden and (not args.launch or args.watch):
        parser.error("--hidden requires --launch and cannot be combined with --watch")
    if args.workspace is not None and (args.workspace<1 or not args.launch or args.hidden):
        parser.error('--workspace requires a visible --launch and a positive workspace number')
    if args.launch:
        with socket.socket() as check:
            if check.connect_ex(("127.0.0.1", args.port)) == 0:
                parser.error("Port is already occupied; use --url to attach deliberately or choose --port")
    process = None
    result = None
    try:
        if args.launch:
            api, process, profile = launch_game(args)
        else:
            api = PlayerAPI(args.url)
        if args.log:
            log_path = Path(args.log)
        elif process:
            log_path = profile / f"decisions-{time.time_ns()}.jsonl"
        else:
            base = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else Path(tempfile.gettempdir())
            log_path = base / f"survival-run-{time.time_ns()}.jsonl"
        print(f"Decision log: {log_path}", flush=True)
        result = run(api, policy, args.max_actions,
                     args.delay if args.delay is not None else 0.3 if args.watch else 0, log_path)
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result["outcome"] == "success" else 2
    except KeyboardInterrupt:
        print("Bot interrupted; no input was retried.", file=sys.stderr)
        return 130
    except (RuntimeError, urllib.error.URLError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        terminal=result and result.get('outcome') in {'dead','success','deadlocked'}
        persistent=getattr(policy,'goal','survival')=='survival'
        if process and not args.keep_open and (not persistent or terminal):
            stop_game(process)
        elif process and persistent and not terminal:
            print('Until-death run paused: game left open; no unsupported UI or ambiguous input retried.',file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
