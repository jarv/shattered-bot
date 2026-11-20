import io
import json
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.player_api import PlayerAPI, PlayerAPIError
from tools.survival_bot import launch_game


class Response(io.BytesIO):
    status = 200

    def __init__(self, value):
        super().__init__(json.dumps(value).encode())


class PlayerAPITest(unittest.TestCase):
    def setUp(self):
        self.api = PlayerAPI(token="test-token")

    @patch("urllib.request.urlopen")
    def test_state_then_step_uses_latest_observation(self, request):
        request.side_effect = [
            Response({"api_version": 1, "observation_id": 3, "status": "menu"}),
            Response({"api_version": 1, "observation_id": 5, "status": "ready"}),
        ]
        state = self.api.step({"type": "wait"})
        self.assertEqual(5, state["observation_id"])
        calls = request.call_args_list
        self.assertIsNone(calls[0].args[0].data)
        self.assertEqual(
            {"type": "wait", "observation_id": 3},
            json.loads(calls[1].args[0].data),
        )
        self.assertEqual("Bearer test-token", calls[1].args[0].get_header("Authorization"))

    @patch("urllib.request.urlopen")
    def test_structured_error_invalidates_handles_without_retry(self, request):
        self.api.observation = {"api_version": 1, "observation_id": 3}
        request.side_effect = urllib.error.HTTPError(
            self.api.url + "/action", 504, "timeout", {},
            io.BytesIO(json.dumps({"api_version": 1, "error": {
                "code": "DECISION_TIMEOUT", "message": "Read state; do not retry",
                "action_may_have_executed": True,
            }}).encode()),
        )
        with self.assertRaises(PlayerAPIError) as caught:
            self.api.step({"type": "wait"})
        self.assertEqual("DECISION_TIMEOUT", caught.exception.code)
        self.assertTrue(caught.exception.action_may_have_executed)
        self.assertIsNone(self.api.observation)
        self.assertEqual(1, request.call_count)

    @patch("urllib.request.urlopen")
    def test_transport_failure_does_not_retry(self, request):
        self.api.observation = {"api_version": 1, "observation_id": 3}
        request.side_effect = TimeoutError("socket timeout")
        with self.assertRaises(PlayerAPIError) as caught:
            self.api.step({"type": "wait"})
        self.assertEqual("TRANSPORT_ERROR", caught.exception.code)
        self.assertTrue(caught.exception.action_may_have_executed)
        self.assertIsNone(self.api.observation)
        self.assertEqual(1, request.call_count)

    @patch("urllib.request.urlopen")
    def test_unknown_or_unversioned_api_is_rejected(self, request):
        for observation in ({"api_version": 2}, {"api_version": True}, {"observation_id": 1}, []):
            request.return_value = Response(observation)
            with self.assertRaises(PlayerAPIError) as caught:
                self.api.state()
            self.assertEqual("API_VERSION_MISMATCH", caught.exception.code)
            self.assertFalse(caught.exception.action_may_have_executed)
            self.assertIsNone(self.api.observation)

    @patch("urllib.request.urlopen")
    def test_non_json_error_body_is_reported_conservatively(self, request):
        self.api.observation = {"api_version": 1, "observation_id": 3}
        request.side_effect = urllib.error.HTTPError(
            self.api.url + "/action", 502, "bad gateway", {}, io.BytesIO(b"Bad gateway"),
        )
        with self.assertRaises(PlayerAPIError) as caught:
            self.api.step({"type": "wait"})
        self.assertEqual("Bad gateway", caught.exception.message)
        self.assertTrue(caught.exception.action_may_have_executed)
        self.assertIsNone(self.api.observation)

    @patch("tools.survival_bot.stop_game")
    @patch("tools.survival_bot.time.sleep")
    @patch("tools.survival_bot.PlayerAPI")
    @patch("tools.survival_bot.subprocess.Popen")
    def test_launcher_retries_only_observation_transport_errors(self, process, api, sleep, stop):
        import tempfile

        process.return_value.poll.return_value = None
        with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="spd-launch-test-") as temp:
            game_dir = Path(temp) / "game"
            game_dir.mkdir()
            (game_dir / "gradlew").touch()
            args = SimpleNamespace(game_dir=str(game_dir), profile=temp,
                                   port=38949, hidden=True, java_home=None)
            api.return_value.state.side_effect = [
                PlayerAPIError(0, "Connection refused", code="TRANSPORT_ERROR",
                               action_may_have_executed=False),
                {"api_version": 1},
            ]
            launch_game(args, log_path=Path(temp) / "retry.log")
            self.assertEqual(2, api.return_value.state.call_count)
            sleep.assert_called_once_with(0.25)
            stop.assert_not_called()

            api.return_value.state.side_effect = PlayerAPIError(
                200, "Wrong version", code="API_VERSION_MISMATCH",
                action_may_have_executed=False,
            )
            with self.assertRaises(PlayerAPIError):
                launch_game(args, log_path=Path(temp) / "version.log")
            stop.assert_called_once_with(process.return_value)


if __name__ == "__main__":
    unittest.main()
