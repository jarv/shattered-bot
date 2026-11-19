#!/usr/bin/env python3
"""Exercise a running API game. Use ONLY with a disposable profile: this plays turns."""

import argparse
import json
import urllib.error
import urllib.request

from player_api import PlayerAPI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    api = PlayerAPI(args.url)
    state = api.state()
    assert state.get("status") == "ready", "Start a disposable run first"
    stale_id = state["observation_id"]

    state = api.step({"type": "wait"})
    assert state["status"] == "ready"
    state = api.step({"type": "search"})
    assert state["status"] == "ready"
    state = api.step({"type": "inspect", "cell": state["hero"]["cell"]})
    assert state["modal"]
    state = api.step({"type": "back"})
    assert not state["modal"]

    throwable = next(item for item in state["inventory"] if "THROW" in item["actions"])
    state = api.step({"type": "item", "id": throwable["id"], "action": "THROW"})
    assert state["status"] == "targeting"
    assert state["target_prompt"]
    state = api.step({"type": "back"})
    assert state["status"] == "ready"

    cell, width = state["hero"]["cell"], state["map"]["width"]
    adjacent = next(
        tile["cell"] for tile in state["map"]["cells"]
        if tile["visible"] and tile["terrain"] in (1, 2, 6, 9, 14, 20)
        and abs(tile["cell"] % width - cell % width) <= 1
        and abs(tile["cell"] // width - cell // width) <= 1
        and tile["cell"] != cell
    )
    state = api.step({"type": "cell", "cell": adjacent})
    assert state["hero"]["cell"] == adjacent

    for token, revision, expected in (
        (api.token, stale_id, 409),
        ("wrong-token", state["observation_id"], 401),
    ):
        request = urllib.request.Request(
            api.url + "/action",
            data=json.dumps({"type": "wait", "observation_id": revision}).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(request, timeout=35)
        except urllib.error.HTTPError as error:
            assert error.code == expected, error.code
        else:
            raise AssertionError(f"Expected HTTP {expected}")
    print("Passed: observe, wait, search, inspect/back, item targeting/cancel, move, stale IDs, auth")


if __name__ == "__main__":
    main()
