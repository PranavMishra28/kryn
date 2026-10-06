"""Shared research-only OpenCode container configuration; no Harbor SDK required."""

import json
from pathlib import Path
import shlex

from research.local_only import check_environment

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = "/tmp/kryn-plugin"
STATE_DIR = "/tmp/kryn-state"
LOCAL_PORT = 18765
LOCAL_URL = f"http://127.0.0.1:{LOCAL_PORT}/v1"


def container_config(*, native=False):
    """Keep the shipped policy/roles, substituting only container-owned paths."""
    config = json.loads((ROOT / "setup/opencode.template.json").read_text()
                        .replace("__ROOT__", "/tmp/kryn"))
    base_url = LOCAL_URL
    config["providers"]["local"]["settings"]["baseURL"] = base_url
    model = config["providers"]["local"]["models"]["qwen"]
    model["settings"]["baseURL"] = base_url
    for variant in model["variants"]:
        variant["settings"]["baseURL"] = base_url
    # Terminal-Bench is a terminal task; its container does not contain the
    # owner's browser or search MCP. No benchmark oracle is mounted here.
    config["mcp"]["servers"] = {}
    product = next(item for item in config["plugins"] if isinstance(item, dict))
    product["package"] = PLUGIN_DIR
    product["options"].update(stateDir=STATE_DIR, nodeBinary="/usr/bin/node",
                              profileId="terminal-bench-calibration",
                              inferenceBaseURL=base_url)
    if native:
        config["plugins"] = [entry for entry in config["plugins"] if entry is not product]
        config["agents"] = {
            name: {key: value for key, value in agent.items()
                   if key in {"mode", "hidden", "model", "permissions", "description"}}
            for name, agent in config["agents"].items()}
    return config


def worker_environment(*, native=False):
    """The complete OpenCode environment; the launch uses ``env -i``."""
    env = {
        "HOME": "/tmp/kryn/home",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "OPENCODE_TEST_HOME": "/tmp/kryn/home",
        "OPENCODE_CONFIG_CONTENT": json.dumps(container_config(native=native)),
        "OPENCODE_CLI_CONFIG_CONTENT": '{"session":{"permissions":"auto"}}',
        "OPENCODE_CONFIG_PROJECT_DISABLE": "true",
        "NO_PROXY": "host.docker.internal,127.0.0.1,localhost",
        "XDG_CONFIG_HOME": "/tmp/kryn/xdg/config",
        "XDG_DATA_HOME": "/tmp/kryn/xdg/data",
        "XDG_CACHE_HOME": "/tmp/kryn/xdg/cache",
        "XDG_STATE_HOME": "/tmp/kryn/xdg/state",
    }
    check_environment(env, "/tmp/kryn", LOCAL_URL)
    return env


def scrubbed_command(*, native=False):
    env = worker_environment(native=native)
    return "/usr/bin/env -i " + " ".join(
        shlex.quote(key + "=" + value) for key, value in sorted(env.items()))
