"""Negative controls for the benchmark inference boundary."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research.local_only import check_config, check_environment


URL = "http://127.0.0.1:18765/v1"


def config():
    return {
        "model": "local/qwen",
        "providers": {"local": {
            "package": "@opencode/ai/providers/openai-compatible",
            "settings": {"baseURL": URL},
            "models": {"qwen": {
                "modelID": "Qwen3.5-9B-6bit",
                "package": "@opencode/ai/providers/openai-compatible",
                "settings": {"baseURL": URL},
                "variants": [{"id": "fast", "settings": {"baseURL": URL}}],
            }},
        }},
        "agents": {"agent": {"model": "local/qwen"}},
        "commands": {},
    }


class LocalOnlyGateTests(unittest.TestCase):
    def test_routes_and_model_selection_fail_closed(self):
        good = config()
        self.assertEqual(len(check_config(good, URL)), 64)
        for mutate in (
            lambda c: c.update(model="opencode/free"),
            lambda c: c["providers"].update(remote={}),
            lambda c: c["providers"]["local"]["models"].update(other={}),
            lambda c: c["providers"]["local"]["models"]["qwen"].update(modelID="other"),
            lambda c: c["providers"]["local"]["models"]["qwen"]["variants"][0]["settings"].update(baseURL="https://example.com/v1"),
            lambda c: c["agents"]["agent"].update(model="remote/agent"),
        ):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(RuntimeError):
                check_config(bad, URL)
        with self.assertRaises(RuntimeError):
            check_config(good, "http://localhost:18765/v1")

    def test_isolation_and_credentials_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = {key: str(root / key.lower()) for key in (
                "HOME", "OPENCODE_TEST_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
                "XDG_STATE_HOME")}
            env.update(OPENCODE_CONFIG_CONTENT=json.dumps(config()),
                       OPENCODE_CONFIG_PROJECT_DISABLE="true")
            self.assertEqual(len(check_environment(env, root, URL)), 64)
            for extra in ({"OPENAI_API_KEY": "secret"},
                          {"OPENCODE_CONFIG_PROJECT_DISABLE": "false"},
                          {"HOME": str(root.parent)},
                          {"OPENCODE_CONFIG_DIR": str(root)}):
                bad = dict(env, **extra)
                with self.assertRaises(RuntimeError):
                    check_environment(bad, root, URL)


if __name__ == "__main__":
    unittest.main()
