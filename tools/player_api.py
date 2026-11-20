#!/usr/bin/env python3
"""Dependency-free client for the opt-in desktop player API."""

import argparse
import json
import os
import urllib.error
import urllib.request


class PlayerAPIError(RuntimeError):
    def __init__(self, status, message, *, code=None, action_may_have_executed=None):
        self.status, self.message = status, message
        self.code = code
        self.action_may_have_executed = action_may_have_executed
        super().__init__(f"HTTP {status}: {message}")


class PlayerAPI:
    API_VERSION = 1

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
                observation = json.load(response)
                if (not isinstance(observation, dict)
                        or type(observation.get("api_version")) is not int
                        or observation["api_version"] != self.API_VERSION):
                    raise PlayerAPIError(
                        response.status, "Unsupported player API version; update the game and client together",
                        code="API_VERSION_MISMATCH", action_may_have_executed=body is not None,
                    )
        except urllib.error.HTTPError as error:
            self.observation = None
            with error:
                raw = error.read().decode(errors="replace")
            try:
                detail = json.loads(raw)["error"]
                message = detail["message"]
                code = detail["code"]
                uncertain = detail["action_may_have_executed"]
            except (ValueError, KeyError, TypeError):
                message, code, uncertain = raw, None, body is not None
            raise PlayerAPIError(
                error.code, message, code=code, action_may_have_executed=uncertain,
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            self.observation = None
            raise PlayerAPIError(
                0, f"Request failed; read state before continuing: {error}",
                code="TRANSPORT_ERROR", action_may_have_executed=body is not None,
            ) from error
        except PlayerAPIError:
            self.observation = None
            raise
        self.observation = observation
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
