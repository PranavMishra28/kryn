"""Research-only Harbor adapter for KRYN's pinned OpenCode 2.0.10 loop.

Import with ``--agent research.harbor_kryn_agent:KrynOpenCode`` from a KRYN
checkout. Harbor owns the task container and verifier; this module supplies
only KRYN's exact CLI/config/plugin bytes to the agent phase.
"""

import json
from pathlib import Path
import shlex
from tempfile import TemporaryDirectory

from harbor.agents.installed.base import PackageSpec, with_prompt_template
from harbor.agents.installed.opencode import OpenCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from tools.native_client import product_plugin_files


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = "/tmp/kryn-plugin"
STATE_DIR = "/tmp/kryn-state"
LOCAL_PORT = 18765


def container_config():
    """Keep the shipped policy/roles, substituting only container-owned paths."""
    config = json.loads((ROOT / "setup/opencode.template.json").read_text()
                        .replace("__ROOT__", "/tmp/kryn"))
    base_url = f"http://127.0.0.1:{LOCAL_PORT}/v1"
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
    return config


class KrynOpenCode(OpenCode):
    """Use Harbor's official verifier with KRYN's actual 2.0.10 worker bytes."""

    MODEL_CONNECTION = None
    SYSTEM_PACKAGES = {**OpenCode.SYSTEM_PACKAGES, "socat": PackageSpec.standard("socat")}

    @staticmethod
    def name() -> str:
        return "kryn-opencode"

    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(
            environment, ("bash", "coreutils", "nodejs", "npm", "git", "ripgrep", "socat", "curl")
        )
        await self.exec_as_agent(
            environment,
            "npm i -g @opencode/cli@2.0.10 && test \"$(opencode --version)\" = 'opencode v2.0.10'",
        )
        with TemporaryDirectory(prefix="kryn-harbor-plugin-") as temporary:
            source = Path(temporary)
            for name, data in product_plugin_files(ROOT).items():
                (source / name).write_bytes(data)
            await environment.upload_dir(source, PLUGIN_DIR)
        await self.exec_as_agent(environment, f"mkdir -p {STATE_DIR} {self.environment_logs_dir} "
                                 "/tmp/kryn/xdg/config /tmp/kryn/xdg/data "
                                 "/tmp/kryn/xdg/cache /tmp/kryn/xdg/state")

    @with_prompt_template
    async def run(self, instruction: str, environment: BaseEnvironment,
                  context: AgentContext) -> None:
        self._instruction = instruction
        port = int(self.extra_env["KRYN_HARBOR_RELAY_PORT"])
        if not 1024 <= port <= 65535:
            raise ValueError("Invalid inference-only host relay port")
        await self.exec_as_agent(environment,
            f"socat TCP-LISTEN:{LOCAL_PORT},bind=127.0.0.1,reuseaddr,fork "
            f"TCP:host.docker.internal:{port} > {self.environment_logs_dir}/relay.log "
            "2>&1 </dev/null &")
        await self.exec_as_agent(environment,
            f"for i in 1 2 3 4 5 6 7 8 9 10; do curl -fsS --max-time 2 "
            f"http://127.0.0.1:{LOCAL_PORT}/v1/models >/dev/null && exit 0; "
            "sleep 0.2; done; exit 1")
        output = shlex.quote(str(self.environment_logs_dir / self._OUTPUT_FILENAME))
        command = ("opencode run --standalone --model local/qwen --agent agent "
                   "--format json --auto -- " + shlex.quote(instruction) +
                   f" 2>&1 </dev/null | tee {output}")
        await self.exec_as_agent(environment, command, env={
            "OPENCODE_CONFIG_CONTENT": json.dumps(container_config()),
            "OPENCODE_CLI_CONFIG_CONTENT": '{"session":{"permissions":"auto"}}',
            "NO_PROXY": "host.docker.internal,127.0.0.1,localhost",
            "XDG_CONFIG_HOME": "/tmp/kryn/xdg/config",
            "XDG_DATA_HOME": "/tmp/kryn/xdg/data",
            "XDG_CACHE_HOME": "/tmp/kryn/xdg/cache",
            "XDG_STATE_HOME": "/tmp/kryn/xdg/state",
        })
        if messages := self._error_messages():
            raise RuntimeError("OpenCode error event: " + "; ".join(messages[:3]))
