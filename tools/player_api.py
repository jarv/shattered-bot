#!/usr/bin/env python3
"""Dependency-free client for the opt-in desktop player API."""

import argparse
import json
import os
import urllib.error
import urllib.request


class PlayerAPIError(RuntimeError):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(f"HTTP {status}: {message}")


class PlayerAPI:
    def __init__(self, url="http://127.0.0.1:8765", token=None):
        self.url = url.rstrip("/")
        self.token = token or os.environ["SPD_API_TOKEN"]
        self.observation = None

    def _request(self, path, body=None):
        request = urllib.request.Request(
            self.url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                self.observation = json.load(response)
        except urllib.error.HTTPError as error:
            raise PlayerAPIError(error.code, error.read().decode()) from error
        return self.observation

    def state(self):
        return self._request("/state")

    def step(self, action):
        if self.observation is None:
            self.state()
        return self._request(
            "/action", {**action, "observation_id": self.observation["observation_id"]}
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("action", nargs="?", help='JSON action, e.g. \'{"type":"wait"}\'')
    args = parser.parse_args()
    api = PlayerAPI(args.url)
    result = api.step(json.loads(args.action)) if args.action else api.state()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
