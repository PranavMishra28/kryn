"""Fail-closed, research-only proof of the benchmark model route."""

import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import localai  # noqa: E402

MODEL = "Qwen3.5-9B-6bit"
REFERENCE = "local/qwen"
FORWARD_TARGET = "http://127.0.0.1:8000/v1"
PROVIDER_PACKAGE = "@opencode/ai/providers/openai-compatible"


def _require(condition, message):
    if not condition:
        raise RuntimeError("Local-only benchmark gate: " + message)


def _loopback_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                and parsed.port is not None and parsed.path == "/v1"
                and not parsed.username and not parsed.password and not parsed.query
                and not parsed.fragment)
    except ValueError:
        return False


def check_config(config, expected_url):
    """Reject every route that could select a nonlocal configured model."""
    _require(_loopback_url(expected_url), "expected inference route is not loopback")
    _require(isinstance(config, dict), "effective OpenCode config is missing")
    _require(config.get("model") in {REFERENCE, REFERENCE + "#fast"},
             "default model is not the pinned local model")
    providers = config.get("providers")
    _require(isinstance(providers, dict) and set(providers) == {"local"},
             "external or missing provider configuration")
    provider = providers["local"]
    _require(provider.get("package") == PROVIDER_PACKAGE and
             provider.get("settings", {}).get("baseURL") == expected_url,
             "provider does not use the expected loopback route")
    models = provider.get("models")
    _require(isinstance(models, dict) and set(models) == {"qwen"},
             "external or missing model configuration")
    model = models["qwen"]
    _require(model.get("modelID") == MODEL and model.get("package") == PROVIDER_PACKAGE
             and model.get("settings", {}).get("baseURL") == expected_url,
             "model ID, package, or route changed")
    variants = model.get("variants", [])
    _require(isinstance(variants, list) and {v.get("id") for v in variants
             if isinstance(v, dict)} == {"fast"} and len(variants) == 1
             and variants[0].get("settings", {}).get("baseURL") == expected_url,
             "variant route changed")
    for catalog in ("agents", "commands"):
        entries = config.get(catalog, {})
        _require(isinstance(entries, dict), "invalid " + catalog + " catalog")
        for name, item in entries.items():
            _require(isinstance(item, dict) and
                     item.get("model", REFERENCE) in {REFERENCE, REFERENCE + "#fast"},
                     "nonlocal model reference in " + catalog + "/" + str(name))
    return hashlib.sha256(json.dumps(config, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def check_environment(env, isolation_root, expected_url):
    """Prove the effective config is isolated and no provider secret is forwarded."""
    _require(isinstance(env, dict), "worker environment is missing")
    forbidden = ("OPENAI", "ANTHROPIC", "GOOGLE", "GEMINI", "OPENROUTER",
                 "AZURE_OPENAI", "AWS_BEDROCK", "VERTEX", "MISTRAL_API",
                 "TOGETHER_API", "FIREWORKS_API", "CEREBRAS_API")
    leaked = [key for key in env if key.upper().startswith(forbidden)
              or (key.upper().endswith(("_API_KEY", "_AUTH_TOKEN"))
                  and key != "OPENCODE_PASSWORD")]
    _require(not leaked, "external model credentials are forwarded")
    _require(env.get("OPENCODE_CONFIG_PROJECT_DISABLE") == "true",
             "project config discovery is enabled")
    _require("OPENCODE_CONFIG_DIR" not in env, "ambient config directory is forwarded")
    root = Path(isolation_root).resolve()
    _require(root.is_absolute(), "config isolation root is not absolute")
    for key in ("HOME", "OPENCODE_TEST_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
                "XDG_STATE_HOME"):
        value = env.get(key)
        _require(isinstance(value, str) and Path(value).is_absolute()
                 and Path(value).resolve().is_relative_to(root), key + " is not isolated")
    try:
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Local-only benchmark gate: effective config is unreadable") from error
    return check_config(config, expected_url)


def attest(env, isolation_root, expected_url):
    """Pin config and the owner's live local oMLX listener before generation."""
    config_sha = check_environment(env, isolation_root, expected_url)
    pid = localai.runtime_identity()
    runtime = localai.runtime_metadata()
    _require(runtime.get("healthy") is True and runtime.get("model") == MODEL
             and runtime.get("runtime") == "http://127.0.0.1:8000"
             and runtime.get("max_model_len") == 98304
             and runtime.get("model_memory_max") == 22 * 1024**3
             and runtime.get("active_requests") == 0
             and runtime.get("waiting_requests") == 0,
             "owned 96K/22-GiB local runtime is not idle and healthy")
    return {"schema": 1, "passed": True, "provider": "local", "reference": REFERENCE,
            "model_id": MODEL, "effective_config_sha256": config_sha,
            "configured_loopback_url": expected_url, "forward_target": FORWARD_TARGET,
            "owned_runtime_pid": pid, "runtime_version": runtime["version"],
            "context_tokens": runtime["max_model_len"],
            "memory_ceiling_bytes": runtime["model_memory_max"],
            "external_credentials_forwarded": False,
            "project_config_discovery": False,
            "relay_source_sha256": hashlib.sha256(
                (ROOT / "tools/learning.py").read_bytes()).hexdigest()}


def same_runtime(receipt):
    """Fail closed if the local listener changed while the arm was running."""
    return (localai.runtime_identity() == receipt["owned_runtime_pid"]
            and localai.runtime_metadata().get("model") == MODEL)
