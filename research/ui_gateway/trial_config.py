"""Research-only matched OpenCode configuration for the fixed-page UI gateway."""
import copy
from pathlib import Path

TOOLS = ("browser_navigate", "browser_snapshot", "browser_click",
         "browser_press_key", "browser_take_screenshot", "browser_resize")


def with_ui_gateway(base, *, python, adapter, repo, port, token):
    """Apply the same browser catalog and permission policy before arm separation."""
    config = copy.deepcopy(base)
    for value in (python, adapter, repo):
        path = Path(value)
        if not path.is_absolute() or path != path.resolve():
            raise ValueError("UI gateway paths must be canonical")
    if not 1024 <= port <= 65535 or len(token) != 48:
        raise ValueError("UI broker identity is invalid")
    config["mcp"] = {"servers": {"browser": {"type": "local", "command": [str(python), "-B",
        str(adapter), "--repo", str(repo), "--port", str(port), "--token", token],
        "codemode": False}}}
    browser_rules = [{"action": "browser_*", "resource": "*", "effect": "deny"}]
    browser_rules += [{"action": "browser_" + name, "resource": "*", "effect": "allow"}
                      for name in TOOLS]
    config["permissions"] += [
        {"action": "webfetch", "resource": "*", "effect": "deny"},
        {"action": "search_*", "resource": "*", "effect": "deny"},
        *browser_rules,
    ]
    for name, agent in config.get("agents", {}).items():
        if not isinstance(agent, dict) or "permissions" not in agent:
            continue
        agent["permissions"] = [rule for rule in agent["permissions"]
                                if not rule.get("action", "").startswith(("browser_", "search_"))
                                and rule.get("action") != "webfetch"]
        agent["permissions"] += [
            {"action": "webfetch", "resource": "*", "effect": "deny"},
            {"action": "search_*", "resource": "*", "effect": "deny"},
            *([{"action": tool, "resource": "*", "effect": "deny"}
               for tool in ("glob", "grep", "skill")] if name == "browse" else []),
            *(copy.deepcopy(browser_rules) if name == "browse" else
              [{"action": "browser_*", "resource": "*", "effect": "deny"}]),
        ]
    return config
